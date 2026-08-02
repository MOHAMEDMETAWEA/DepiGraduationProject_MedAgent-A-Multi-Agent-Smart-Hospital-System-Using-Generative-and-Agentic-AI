"""
T3.04 — LoRA Fine-tuning Script (for Google Colab T4)

Fine-tunes Qwen2.5-7B-Instruct on medical dialogue data using QLoRA.
Runs on Colab free T4 GPU (~10-14 hours).

Usage:
    1. Upload this script to Google Colab
    2. Or copy-paste sections into notebook cells
    3. Run cells in order

Hardware requirement: T4 GPU (16GB VRAM) — free on Colab
"""

# ============================================================
# CELL 0: Mount Google Drive (first cell — run this FIRST)
# ============================================================
# from google.colab import drive
# drive.mount("/content/drive")
#
# # All outputs saved to Drive — won't disappear when session ends
# OUTPUT_DIR = "/content/drive/MyDrive/medagent-lora"

# ============================================================
# CELL 1: Install dependencies
# ============================================================
# !pip install -q transformers accelerate peft trl datasets bitsandbytes sentencepiece

# ============================================================
# CELL 2: Imports
# ============================================================
import torch
from datasets import Dataset, load_dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
    pipeline,
)
from trl import SFTTrainer

# ============================================================
# CELL 3: Configuration
# ============================================================
MODEL_NAME = "Qwen/Qwen2.5-7B-Instruct"
OUTPUT_DIR = "/content/drive/MyDrive/medagent-lora"  # Saved to Google Drive
HF_REPO = "Hossam7asan/medagent-lora"

# LoRA hyperparams
LORA_R = 16
LORA_ALPHA = 32
LORA_DROPOUT = 0.05
LORA_TARGET_MODULES = ["q_proj", "k_proj", "v_proj", "o_proj"]

# Training hyperparams
BATCH_SIZE = 4
GRADIENT_ACCUMULATION = 8  # Effective batch = 4 * 8 = 32
LEARNING_RATE = 2e-4
NUM_EPOCHS = 3
MAX_SEQ_LENGTH = 512
WARMUP_RATIO = 0.03

# Quantization (4-bit NF4)
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
)

# ============================================================
# CELL 4: Load tokenizer and model
# ============================================================
print("Loading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = "right"

print("Loading model (4-bit)...")
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True,
)
model = prepare_model_for_kbit_training(model)
print("Model loaded on:", model.device)

# ============================================================
# CELL 5: Apply LoRA
# ============================================================
lora_config = LoraConfig(
    r=LORA_R,
    lora_alpha=LORA_ALPHA,
    lora_dropout=LORA_DROPOUT,
    target_modules=LORA_TARGET_MODULES,
    bias="none",
    task_type="CAUSAL_LM",
)

model = get_peft_model(model, lora_config)
model.print_trainable_parameters()
# Expected: ~0.1% of total params are trainable (~5-10M out of 7B)


# ============================================================
# CELL 6: Load and prepare training data
# ============================================================
def format_medical_chat(example):
    """
    Format medical dialogue for instruction tuning.
    Template: <system> + patient message + doctor response
    """
    patient = example.get("patient", example.get("question", ""))
    doctor = example.get("doctor", example.get("answer", ""))

    if not patient or not doctor:
        return {"text": ""}

    system = (
        "<|im_start|>system\n"
        "You are MedAgent, a bilingual medical triage AI. "
        "Assess symptoms, ask follow-up questions, determine triage level "
        "(emergency/urgent/routine), and recommend next steps. "
        "Always include a 'consult a physician' disclaimer. "
        "Never provide definitive diagnoses or prescribe medications."
        "<|im_end|>\n"
    )
    user = f"<|im_start|>user\n{patient}<|im_end|>\n"
    assistant = f"<|im_start|>assistant\n{doctor}<|im_end|>\n"

    return {"text": system + user + assistant}


def load_training_data():
    """
    Load medical datasets and format for instruction tuning.

    Uses MedQuAD (curated medical Q&A) which is actively maintained.
    """
    data = []

    # MedQuAD — Medical Question Answering Dataset (actively maintained)
    try:
        ds = load_dataset("lavita/MedQuAD", split="train", streaming=True)
        for count, row in enumerate(ds, 1):
            # MedQuAD format: question, answer
            formatted = format_medical_chat(
                {
                    "patient": row.get("question", ""),
                    "doctor": row.get("answer", ""),
                }
            )
            if formatted["text"]:
                data.append(formatted)
            if count >= 30000:
                break
        print(f"MedQuAD: {len(data)} examples")
    except Exception as e:
        print(f"MedQuAD failed: {e}")

    # PubMedQA — Clinical questions with expert answers
    try:
        start_count = len(data)
        ds = load_dataset("pubmed_qa", "pqa_labeled", split="train", streaming=True)
        for count, row in enumerate(ds, 1):
            question = row.get("question", "")
            # Use long_answer or concatenate context as answer
            answer = row.get("long_answer", "") or " ".join(
                row.get("context", {}).get("contexts", [])
            )
            formatted = format_medical_chat(
                {
                    "patient": question,
                    "doctor": answer,
                }
            )
            if formatted["text"]:
                data.append(formatted)
            if count >= 10000:
                break
        print(f"PubMedQA: {len(data) - start_count} examples")
    except Exception as e:
        print(f"PubMedQA failed: {e}")

    # Medical Meadow Flashcards — Clinical knowledge
    try:
        start_count = len(data)
        ds = load_dataset(
            "medalpaca/medical_meadow_medical_flashcards", split="train", streaming=True
        )
        for count, row in enumerate(ds, 1):
            formatted = format_medical_chat(
                {
                    "patient": row.get("input", ""),
                    "doctor": row.get("output", ""),
                }
            )
            if formatted["text"]:
                data.append(formatted)
            if count >= 10000:
                break
        print(f"MedAlpaca: {len(data) - start_count} examples")
    except Exception as e:
        print(f"MedAlpaca failed: {e}")

    if not data:
        print("\n⚠️  All online sources failed. Using built-in examples for demo.")
        data = _get_fallback_data()

    import random

    random.seed(42)
    random.shuffle(data)

    n = len(data)
    train = data[: int(n * 0.8)]
    val = data[int(n * 0.8) : int(n * 0.9)]
    test = data[int(n * 0.9) :]

    print(f"Total: {n} | Train: {len(train)} | Val: {len(val)} | Test: {len(test)}")
    return train, val, test


def _get_fallback_data():
    """Built-in medical examples if no online datasets available."""
    return [
        {
            "text": "<|im_start|>system\nYou are MedAgent, a bilingual medical triage AI.\n<|im_end|>\n<|im_start|>user\nI have chest pain radiating to my left arm.<|im_end|>\n<|im_start|>assistant\nThis could indicate a cardiac event. You need emergency care — call 123 or go to ER immediately. Do NOT drive yourself.<|im_end|>"
        },
        {
            "text": "<|im_start|>system\nYou are MedAgent, a bilingual medical triage AI.\n<|im_end|>\n<|im_start|>user\nعندي صداع خفيف منذ يومين<|im_end|>\n<|im_start|>assistant\nالصداع الخفيف عادة لا يستدعي القلق. يمكنك أخذ قسط من الراحة وشرب الماء. إذا استمر أو ازداد سوءاً، يرجى استشارة الطبيب.<|im_end|>"
        },
        {
            "text": "<|im_start|>system\nYou are MedAgent, a bilingual medical triage AI.\n<|im_end|>\n<|im_start|>user\nI have high fever 39.5 for 3 days with chills<|im_end|>\n<|im_start|>assistant\nA persistent high fever could indicate infection requiring medical attention. Please see a doctor today. In the meantime, stay hydrated and monitor your temperature.<|im_end|>"
        },
        {
            "text": "<|im_start|>system\nYou are MedAgent, a bilingual medical triage AI.\n<|im_end|>\n<|im_start|>user\nعندي ألم في المعدة مع قيء مستمر<|im_end|>\n<|im_start|>assistant\nالقيء المستمر مع ألم المعدة قد يشير إلى التهاب أو انسداد. يجب مراجعة الطبيب اليوم. لا تتناول أي دواء بدون استشارة.<|im_end|>"
        },
        {
            "text": "<|im_start|>system\nYou are MedAgent, a bilingual medical triage AI.\n<|im_end|>\n<|im_start|>user\nDry cough for 5 days, no other symptoms<|im_end|>\n<|im_start|>assistant\nThis sounds like a mild viral illness. Rest, drink warm fluids, and monitor. If you develop fever or breathing difficulty, see a doctor.<|im_end|>"
        },
        {
            "text": "<|im_start|>system\nYou are MedAgent, a bilingual medical triage AI.\n<|im_end|>\n<|im_start|>user\nBaby 3 months old with fever 38.5, irritable<|im_end|>\n<|im_start|>assistant\nFever in infants under 3 months is a medical emergency — go to ER immediately. Do not give any medication without doctor's advice.<|im_end|>"
        },
        {
            "text": "<|im_start|>system\nYou are MedAgent, a bilingual medical triage AI.\n<|im_end|>\n<|im_start|>user\nI have blood in my urine and burning sensation<|im_end|>\n<|im_start|>assistant\nBlood in urine with burning could indicate a urinary tract infection or kidney stones. See a doctor within 24 hours for evaluation and treatment.<|im_end|>"
        },
        {
            "text": "<|im_start|>system\nYou are MedAgent, a bilingual medical triage AI.\n<|im_end|>\n<|im_start|>user\nعندي حساسية موسمية، عطس ورشح<|im_end|>\n<|im_start|>assistant\nأعراض الحساسية الموسمية يمكن التعامل معها في المنزل. استخدم مضادات الهيستامين المتاحة بدون وصفة. إذا تفاقمت الأعراض، استشر الطبيب.<|im_end|>"
        },
        {
            "text": "<|im_start|>system\nYou are MedAgent, a bilingual medical triage AI.\n<|im_end|>\n<|im_start|>user\nCannot breathe, wheezing, lips turning blue<|im_end|>\n<|im_start|>assistant\nThis is a medical EMERGENCY! Call 123 immediately. Blue lips indicate oxygen deprivation — every second counts.<|im_end|>"
        },
        {
            "text": "<|im_start|>system\nYou are MedAgent, a bilingual medical triage AI.\n<|im_end|>\n<|im_start|>user\nMild joint pain in knees, worse in morning<|im_end|>\n<|im_start|>assistant\nMorning joint stiffness could indicate arthritis. This is not urgent — schedule a routine appointment. Gentle exercise and warm compresses may help.<|im_end|>"
        },
    ]


print("Loading training data...")
train_data, val_data, test_data = load_training_data()

# Convert to Dataset
train_ds = Dataset.from_list(train_data)
val_ds = Dataset.from_list(val_data)
print(f"Train dataset: {len(train_ds)} examples")

# ============================================================
# CELL 7: Training
# ============================================================
training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    num_train_epochs=NUM_EPOCHS,
    per_device_train_batch_size=BATCH_SIZE,
    gradient_accumulation_steps=GRADIENT_ACCUMULATION,
    warmup_ratio=WARMUP_RATIO,
    learning_rate=LEARNING_RATE,
    lr_scheduler_type="cosine",
    logging_steps=10,
    save_steps=200,
    save_total_limit=2,
    fp16=True,
    optim="paged_adamw_8bit",
    report_to="none",
    remove_unused_columns=False,
)

trainer = SFTTrainer(
    model=model,
    args=training_args,
    train_dataset=train_ds,
    tokenizer=tokenizer,
    max_seq_length=MAX_SEQ_LENGTH,
    dataset_text_field="text",
)

print("Starting training...")
print("Expected time: 10-14 hours on T4")
trainer.train()

# ============================================================
# CELL 8: Save adapter
# ============================================================
print("Saving LoRA adapter...")
model.save_pretrained(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)

print(f"Adapter saved to: {OUTPUT_DIR}")
print("File size: ~50MB (adapter only)")

# ============================================================
# CELL 9: Push to HuggingFace Hub (optional)
# ============================================================
# from huggingface_hub import notebook_login
# notebook_login()  # Login first
# model.push_to_hub(HF_REPO)
# tokenizer.push_to_hub(HF_REPO)
# print(f"Pushed to https://huggingface.co/{HF_REPO}")


# ============================================================
# CELL 10: Quick test
# ============================================================
def test_model():
    """Quick test of the fine-tuned model."""
    pipe = pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
        max_new_tokens=128,
        temperature=0.3,
    )

    test_prompts = [
        "Patient: I have a severe headache and blurred vision, started suddenly.",
        "المريض: عندي ألم في الصدر وصعوبة في التنفس",
        "Patient: Mild cough for 3 days, no fever.",
    ]

    for prompt in test_prompts:
        result = pipe(prompt)[0]["generated_text"]
        print(f"\n{'=' * 40}")
        print(f"Input: {prompt}")
        print(f"Output: {result[len(prompt) :]}")


test_model()
print("\nDone! Fine-tuning complete.")
