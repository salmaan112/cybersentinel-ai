import json
import joblib
import pandas as pd
import mlflow
import mlflow.xgboost
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
from xgboost import XGBClassifier
from features import engineer_features

mlflow.set_experiment("cybersentinel-auth-anomaly")


def main():
    raw = pd.read_csv("data/login_logs.csv")
    df, feature_cols = engineer_features(raw)

    df["is_attack"] = (df["label"] != "normal").astype(int)

    X = df[feature_cols]
    y = df["is_attack"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    with open("model_features.json", "w") as f:
        json.dump(feature_cols, f)

    params = dict(
        n_estimators=200, max_depth=5, learning_rate=0.1,
        eval_metric="logloss", random_state=42,
        scale_pos_weight=(y_train == 0).sum() / max((y_train == 1).sum(), 1),
    )

    with mlflow.start_run(run_name="xgboost-auth-anomaly"):
        mlflow.log_params(params)

        model = XGBClassifier(**params)
        model.fit(X_train, y_train)

        preds = model.predict(X_test)
        probs = model.predict_proba(X_test)[:, 1]

        report = classification_report(y_test, preds, output_dict=True, zero_division=0)
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


if __name__ == "__main__":
    main()
