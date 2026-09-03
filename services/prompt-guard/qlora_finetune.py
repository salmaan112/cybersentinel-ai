"""
QLoRA fine-tuning for prompt injection detection — run this on Google Colab
(free GPU) or your own machine with internet access, NOT in a restricted
sandbox, since it downloads distilbert-base-uncased from Hugging Face.

Colab setup:
  1. Upload dataset.csv (from services/prompt-guard/data/prompts.csv) to Colab
  2. Runtime -> Change runtime type -> GPU (T4 is fine)
  3. !pip install transformers peft bitsandbytes accelerate datasets -q
  4. Paste this script into a cell (or upload as .py and %run it) and execute

This produces a LoRA adapter you can load on top of DistilBERT. Copy the
resulting ./prompt-guard-qlora/ folder back into services/prompt-guard/ when
done, and see serve_qlora.py for how to load it in the FastAPI service.
"""
import pandas as pd
import torch
import numpy as np
from datasets import Dataset
from transformers import (
    AutoTokenizer, AutoModelForSequenceClassification,
    TrainingArguments, Trainer, DataCollatorWithPadding,
)
from peft import LoraConfig, get_peft_model, TaskType
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, roc_auc_score

MODEL_NAME = "distilbert-base-uncased"
OUTPUT_DIR = "./prompt-guard-qlora"


def load_data():
    df = pd.read_csv("dataset.csv")  # adjust path if needed on Colab
    train_df, test_df = train_test_split(
        df, test_size=0.2, random_state=42, stratify=df["is_malicious"]
    )
    return (
        Dataset.from_pandas(train_df[["text", "is_malicious"]].rename(columns={"is_malicious": "label"})),
        Dataset.from_pandas(test_df[["text", "is_malicious"]].rename(columns={"is_malicious": "label"})),
    )


def compute_metrics(eval_pred):
    logits, labels = eval_pred
    probs = torch.softmax(torch.tensor(logits), dim=1)[:, 1].numpy()
    preds = np.argmax(logits, axis=1)
    precision, recall, f1, _ = precision_recall_fscore_support(labels, preds, average="binary", zero_division=0)
    return {
        "accuracy": accuracy_score(labels, preds),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "roc_auc": roc_auc_score(labels, probs),
    }


def main():
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    base_model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME, num_labels=2)

    # QLoRA config: only train small adapter matrices, not the full 66M params.
    # This is what makes fine-tuning fast/cheap even on a free Colab GPU.
    lora_config = LoraConfig(
        task_type=TaskType.SEQ_CLS,
        r=8,                     # rank of the adapter matrices
        lora_alpha=16,
        lora_dropout=0.1,
        target_modules=["q_lin", "v_lin"],  # DistilBERT's attention projections
    )
    model = get_peft_model(base_model, lora_config)
    model.print_trainable_parameters()  # sanity check: should be <1% of full model

    train_ds, test_ds = load_data()

    def tokenize(batch):
        return tokenizer(batch["text"], truncation=True, padding=False, max_length=256)

    train_ds = train_ds.map(tokenize, batched=True)
    test_ds = test_ds.map(tokenize, batched=True)

    collator = DataCollatorWithPadding(tokenizer=tokenizer)

    args = TrainingArguments(
        output_dir="./qlora-checkpoints",
        per_device_train_batch_size=16,
        per_device_eval_batch_size=32,
        num_train_epochs=5,
        learning_rate=2e-4,          # LoRA typically wants a higher LR than full fine-tuning
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        logging_steps=10,
        report_to="none",
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_ds,
        eval_dataset=test_ds,
        data_collator=collator,
        compute_metrics=compute_metrics,
    )

    trainer.train()
    metrics = trainer.evaluate()
    print("\nFinal QLoRA metrics:", metrics)

    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    print(f"\nAdapter saved to {OUTPUT_DIR} — download this folder from Colab and "
          f"copy it into services/prompt-guard/ to use it in the FastAPI service.")


if __name__ == "__main__":
    main()
