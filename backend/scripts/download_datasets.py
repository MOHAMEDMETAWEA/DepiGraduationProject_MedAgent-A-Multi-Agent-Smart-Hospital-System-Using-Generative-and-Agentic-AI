"""
T3.01 — Medical Dataset Downloader

Downloads and prepares medical dialogue datasets for fine-tuning:
- MedDialog (EN): doctor-patient conversations
- HealthCareMagic: medical Q&A pairs
- MedQA: multiple-choice clinical questions

Translates subset to Arabic using NLLB-200.
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def download_meddialog():
    """
    MedDialog (English split)
    Source: https://huggingface.co/datasets/bigbio/meddialog
    Size: ~50K doctor-patient conversation turns
    License: MIT
    """
    from datasets import load_dataset

    print("Downloading MedDialog (EN)...")
    ds = load_dataset("bigbio/meddialog", split="train")
    print(f"Loaded {len(ds)} turns")

    # Save as JSONL
    output = RAW_DIR / "meddialog_en.jsonl"
    with open(output, "w", encoding="utf-8") as f:
        for i, row in enumerate(ds):
            if i >= 50000:
                break
            obj = {
                "id": row.get("id", str(i)),
                "doctor": row.get("doctor", ""),
                "patient": row.get("patient", ""),
                "description": row.get("description", ""),
                "dialogue": row.get("dialogue", ""),
            }
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    print(f"Saved {i + 1} turns to {output}")
    return output


def download_healthcare_magic():
    """
    HealthCareMagic-100k
    Source: https://huggingface.co/datasets/RafaelMPereira/HealthCareMagic-100k
    Size: ~100K Q&A pairs (we sample 30K)
    License: Apache 2.0
    """
    from datasets import load_dataset

    print("Downloading HealthCareMagic...")
    ds = load_dataset("RafaelMPereira/HealthCareMagic-100k", split="train")
    print(f"Loaded {len(ds)} pairs")

    output = RAW_DIR / "healthcare_magic_en.jsonl"
    with open(output, "w", encoding="utf-8") as f:
        for i, row in enumerate(ds):
            if i >= 30000:
                break
            obj = {
                "id": str(i),
                "question": row.get("question", ""),
                "answer": row.get("answer", ""),
            }
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    print(f"Saved {i + 1} pairs to {output}")
    return output


def download_medqa():
    """
    MedQA — USMLE-style questions
    Source: https://huggingface.co/datasets/bigbio/med_qa
    License: MIT
    """
    from datasets import load_dataset

    print("Downloading MedQA...")
    ds = load_dataset("bigbio/med_qa", split="train")
    print(f"Loaded {len(ds)} questions")

    output = RAW_DIR / "medqa_en.jsonl"
    with open(output, "w", encoding="utf-8") as f:
        for i, row in enumerate(ds):
            if i >= 10000:
                break
            obj = {
                "id": row.get("id", str(i)),
                "question": row.get("question", ""),
                "answer": row.get("answer", ""),
                "options": row.get("options", {}),
            }
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    print(f"Saved {i + 1} questions to {output}")
    return output


def translate_to_arabic(input_file: Path, output_file: Path, max_rows: int = 10000):
    """
    Translate English medical dialogues to Arabic using NLLB-200.

    NLLB-200 (No Language Left Behind) — Meta's multilingual model.
    Uses HuggingFace pipeline for translation.

    Falls back to a simple passthrough if the model isn't available.
    """

    print(f"Translating {input_file.name} to Arabic...")

    try:
        from transformers import pipeline

        translator = pipeline(
            "translation",
            model="facebook/nllb-200-distilled-600M",
            src_lang="eng_Latn",
            tgt_lang="arb_Arab",
            max_length=512,
        )

        with (
            open(input_file, encoding="utf-8") as fin,
            open(output_file, "w", encoding="utf-8") as fout,
        ):
            count = 0
            for line in fin:
                if count >= max_rows:
                    break
                row = json.loads(line)
                # Translate patient text
                patient_text = row.get("patient", row.get("question", ""))
                if patient_text and len(patient_text) > 5:
                    try:
                        translated = translator(patient_text[:400])[0]["translation_text"]
                        row["patient_ar"] = translated
                    except Exception:
                        row["patient_ar"] = patient_text
                count += 1
                fout.write(json.dumps(row, ensure_ascii=False) + "\n")

        print(f"Translated {count} rows to {output_file}")
    except ImportError:
        print("transformers not installed — copying without translation")
        import shutil

        shutil.copy(input_file, output_file)


if __name__ == "__main__":
    print("=" * 50)
    print("MedAgent — T3.01 Dataset Downloader")
    print("=" * 50)

    # Download English datasets
    download_meddialog()
    download_healthcare_magic()
    download_medqa()

    # Translate MedDialog subset to Arabic
    meddialog_en = RAW_DIR / "meddialog_en.jsonl"
    if meddialog_en.exists():
        translate_to_arabic(meddialog_en, PROCESSED_DIR / "meddialog_ar.jsonl", max_rows=10000)

    print("\nDone! Data saved to:")
    print(f"  Raw: {RAW_DIR}")
    print(f"  Processed: {PROCESSED_DIR}")
