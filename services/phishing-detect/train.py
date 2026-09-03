"""
Phase 1 — Phishing URL Detection.
Trains an XGBoost classifier on the feature-engineered phishing dataset
and logs the run to MLflow so you have a real experiment-tracking habit
from the very first model in this project.
"""
import pandas as pd
import json
import mlflow
import mlflow.xgboost
import joblib
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
from xgboost import XGBClassifier

DATA_PATH = "data/phishing_augmented.csv"
MODEL_OUT = "model.joblib"

# These require a live network/DNS/WHOIS lookup at request time — excluding them
# from v1 keeps the service fast (no external calls) and, critically, keeps
# training and serving features consistent. This is a deliberate scope cut,
# not an oversight — document it as a "v2: add async enrichment" item.
NETWORK_DEPENDENT_FEATURES = [
    "time_response", "domain_spf", "asn_ip", "time_domain_activation",
    "time_domain_expiration", "qty_ip_resolved", "qty_nameservers",
    "qty_mx_servers", "ttl_hostname", "tls_ssl_certificate",
    "qty_redirects", "url_google_index", "domain_google_index",
]

mlflow.set_experiment("cybersentinel-phishing-detect")


def main():
    df = pd.read_csv(DATA_PATH)
    df = df.drop(columns=NETWORK_DEPENDENT_FEATURES)
    X = df.drop(columns=["phishing"])
    y = df["phishing"]

    # Save the exact column order/list the model was trained on, so the
    # serving-side feature extractor never drifts out of sync with training.
    with open("model_features.json", "w") as f:
        json.dump(list(X.columns), f)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    params = dict(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.1,
        eval_metric="logloss",
        random_state=42,
    )

    with mlflow.start_run(run_name="xgboost-baseline"):
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
        joblib.dump(model, MODEL_OUT)

        print(f"Accuracy:  {report['accuracy']:.4f}")
        print(f"Precision: {report['1']['precision']:.4f}")
        print(f"Recall:    {report['1']['recall']:.4f}")
        print(f"F1:        {report['1']['f1-score']:.4f}")
        print(f"ROC AUC:   {auc:.4f}")
        print(f"\nModel saved to {MODEL_OUT}")


if __name__ == "__main__":
    main()
