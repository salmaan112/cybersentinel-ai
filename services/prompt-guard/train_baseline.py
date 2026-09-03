"""
Phase 4 — Prompt Injection Detection, v1 baseline.

IMPORTANT CONTEXT FOR YOUR WRITE-UP:
The original plan was to fine-tune DistilBERT with QLoRA. That step needs a
pretrained transformer downloaded from Hugging Face, which requires internet
access this sandbox doesn't have. So this v1 baseline uses classical ML
(TF-IDF + XGBoost) instead — a legitimate, well-established approach for text
classification that runs anywhere. The QLoRA fine-tuning script is provided
separately (qlora_finetune.py) for you to run on Colab or your own machine
with GPU + internet access, where it belongs anyway for real training speed.
Comparing this baseline against the QLoRA model's results is actually a
*better* story for your report than either alone: "I benchmarked classical
ML against a fine-tuned transformer and here's the tradeoff" is a genuine
technical finding, not just a checkbox.
"""
import json
import joblib
import pandas as pd
import mlflow
import mlflow.xgboost
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import classification_report, roc_auc_score
from xgboost import XGBClassifier

mlflow.set_experiment("cybersentinel-prompt-guard")


def main():
    df = pd.read_csv("data/prompts.csv")
    X_text = df["text"].astype(str)
    y = df["is_malicious"]

    X_train_text, X_test_text, y_train, y_test = train_test_split(
        X_text, y, test_size=0.2, random_state=42, stratify=y
    )

    vectorizer = TfidfVectorizer(
        max_features=5000, ngram_range=(1, 2), sublinear_tf=True, min_df=2
    )
    X_train = vectorizer.fit_transform(X_train_text)
    X_test = vectorizer.transform(X_test_text)

    params = dict(
        n_estimators=300, max_depth=6, learning_rate=0.1,
        eval_metric="logloss", random_state=42,
        scale_pos_weight=(y_train == 0).sum() / max((y_train == 1).sum(), 1),
    )

    with mlflow.start_run(run_name="tfidf-xgboost-baseline"):
        mlflow.log_params(params)
        mlflow.log_param("vectorizer", "tfidf-5000-bigram")

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
        joblib.dump(vectorizer, "vectorizer.joblib")

        print(f"Accuracy:  {report['accuracy']:.4f}")
        print(f"Precision: {report['1']['precision']:.4f}")
        print(f"Recall:    {report['1']['recall']:.4f}")
        print(f"F1:        {report['1']['f1-score']:.4f}")
        print(f"ROC AUC:   {auc:.4f}")


if __name__ == "__main__":
    main()
