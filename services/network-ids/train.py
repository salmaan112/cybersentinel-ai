"""
Phase 2 — Network Intrusion Detection.
Trains on the NSL-KDD benchmark dataset (standard column schema, no header row).
Binary classification: normal traffic vs. any attack (DoS/Probe/R2L/U2R collapsed
into one 'attack' class for v1 — see README for why, and the multi-class stretch
goal).
"""
import json
import joblib
import pandas as pd
import mlflow
import mlflow.xgboost
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, roc_auc_score
from xgboost import XGBClassifier

COLUMNS = [
    "duration", "protocol_type", "service", "flag", "src_bytes", "dst_bytes",
    "land", "wrong_fragment", "urgent", "hot", "num_failed_logins", "logged_in",
    "num_compromised", "root_shell", "su_attempted", "num_root",
    "num_file_creations", "num_shells", "num_access_files", "num_outbound_cmds",
    "is_host_login", "is_guest_login", "count", "srv_count", "serror_rate",
    "srv_serror_rate", "rerror_rate", "srv_rerror_rate", "same_srv_rate",
    "diff_srv_rate", "srv_diff_host_rate", "dst_host_count", "dst_host_srv_count",
    "dst_host_same_srv_rate", "dst_host_diff_srv_rate",
    "dst_host_same_src_port_rate", "dst_host_srv_diff_host_rate",
    "dst_host_serror_rate", "dst_host_srv_serror_rate", "dst_host_rerror_rate",
    "dst_host_srv_rerror_rate", "label",
]

CATEGORICAL_COLS = ["protocol_type", "service", "flag"]

mlflow.set_experiment("cybersentinel-network-ids")


def load(path):
    df = pd.read_csv(path, names=COLUMNS)
    df["is_attack"] = (df["label"] != "normal").astype(int)
    return df.drop(columns=["label"])


def encode_categoricals(train_df, test_df):
    """Fit LabelEncoders on train, apply to both — unseen test categories map
    to a safe fallback instead of crashing (NSL-KDD's test set intentionally
    contains a few service values not seen in training)."""
    encoders = {}
    for col in CATEGORICAL_COLS:
        le = LabelEncoder()
        le.fit(train_df[col])
        train_df[col] = le.transform(train_df[col])

        known = set(le.classes_)
        test_df[col] = test_df[col].apply(lambda v: v if v in known else le.classes_[0])
        test_df[col] = le.transform(test_df[col])

        encoders[col] = le
    return train_df, test_df, encoders


def main():
    train_df = load("data/nsl_kdd_train.csv")
    test_df = load("data/nsl_kdd_test.csv")

    train_df, test_df, encoders = encode_categoricals(train_df, test_df)

    X_train = train_df.drop(columns=["is_attack"])
    y_train = train_df["is_attack"]
    X_test = test_df.drop(columns=["is_attack"])
    y_test = test_df["is_attack"]

    # Persist encoders + feature order so the serving side matches exactly
    joblib.dump(encoders, "label_encoders.joblib")
    with open("model_features.json", "w") as f:
        json.dump(list(X_train.columns), f)

    params = dict(
        n_estimators=300, max_depth=8, learning_rate=0.1,
        eval_metric="logloss", random_state=42,
    )

    with mlflow.start_run(run_name="xgboost-nsl-kdd-binary"):
        mlflow.log_params(params)

        model = XGBClassifier(**params)
        model.fit(X_train, y_train)

        preds = model.predict(X_test)
        probs = model.predict_proba(X_test)[:, 1]

        report = classification_report(y_test, preds, output_dict=True)
        auc = roc_auc_score(y_test, probs)

        mlflow.log_metric("accuracy", report["accuracy"])
        mlflow.log_metric("precision", report["1"]["precision"])
        mlflow.log_metric("recall", report["1"]["recall"])
        mlflow.log_metric("f1", report["1"]["f1-score"])
        mlflow.log_metric("roc_auc", auc)
        mlflow.xgboost.log_model(model, "model")

        joblib.dump(model, "model.joblib")

        print(f"Accuracy:  {report['accuracy']:.4f}")
        print(f"Precision: {report['1']['precision']:.4f}")
        print(f"Recall:    {report['1']['recall']:.4f}")
        print(f"F1:        {report['1']['f1-score']:.4f}")
        print(f"ROC AUC:   {auc:.4f}")
        print("\nNote: evaluated on NSL-KDD's official test set, which — unlike "
              "the train set — includes genuinely unseen attack subtypes. A "
              "lower score here than on phishing-detect is expected and is a "
              "known, documented property of this benchmark, not a bug.")


if __name__ == "__main__":
    main()
