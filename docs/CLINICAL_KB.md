# Clinical Knowledge Base

> The substance that turns MedAgent from "another generic chatbot" into a clinically-grounded triage assistant.

---

## Why this exists

Generic LLMs (Llama, GPT, Gemini, …) **hallucinate drug doses** and **default to "see a doctor"** because that's their safety-trained behavior. For a medical-grade product we need:

1. A **single source of truth** for what the agent says about each complaint
2. A **schema-validated** format so non-engineers (clinicians) can extend it
3. **Source citations** so every claim is auditable
4. A **needs-clinical-review** flag so we know what hasn't been signed off yet

This is implemented as **YAML files** under `backend/app/clinical/`, loaded once at startup, validated against pydantic schemas, and exposed to the AI agent through the `clinical_lookup` tool.

---

## Directory layout

```
backend/app/clinical/
├── __init__.py
├── schemas.py                       # pydantic models — the contract
├── kb.py                            # loader (singleton, lru_cached)
├── chief_complaints/                # 10 YAML files, one per complaint
│   ├── chest_pain.yaml
│   ├── fever.yaml
│   ├── cough.yaml
│   ├── headache.yaml
│   ├── abdominal_pain.yaml
│   ├── back_pain.yaml
│   ├── diarrhea.yaml
│   ├── sore_throat.yaml
│   ├── skin_rash.yaml
│   └── fatigue.yaml
├── formulary/
│   └── drugs.yaml                   # Egyptian drug formulary (10+ drugs)
└── specialties/                     # Pre-visit intake templates (B2B)
    ├── general_practice.yaml
    ├── pediatrics.yaml
    └── ent.yaml
```

---

## The three buckets

### 1. Chief complaints

Each YAML file describes one chief complaint, with everything the agent needs to triage it correctly.

```yaml
id: chest_pain
name: { ar: ألم الصدر, en: Chest pain }
category: cardiovascular
age_range: adult

synonyms:
  - chest pain
  - ألم صدر
  - حجر على صدري
  - ضغط على الصدر

red_flags:
  - question:
      ar: هل الألم بدأ خلال آخر ساعة، أو ينتشر للذراع الأيسر أو الفك أو الكتف؟
      en: Did the pain start within the last hour, or does it radiate to the left arm, jaw, or shoulder?
    severity: emergency
    rationale: Classic ACS presentation — central pressure radiating to arm/jaw within 12h needs ECG + troponin now.

differentials:
  - name: { ar: متلازمة الشريان التاجي الحادة (ACS), en: Acute coronary syndrome }
    likelihood: emergency
    key_features:
      - { ar: ضغط أو ثقل وسط الصدر يستمر >15 دقيقة, en: Central pressure/heaviness lasting >15 min }
      - { ar: انتشار للذراع الأيسر أو الفك, en: Radiation to left arm or jaw }
    icd10: I21

followup_questions:
  - field_id: pain_onset
    question: { ar: امتى بدأ الألم بالظبط؟, en: When exactly did it start? }
    relevance: always

self_care:
  - drug_id: paracetamol
    instruction:
      ar: لو الألم عضلي مؤكد وغير قلبي، باراسيتامول ٥٠٠-١٠٠٠ مج.
      en: If pain is clearly musculoskeletal (non-cardiac), paracetamol 500-1000 mg PO.
    duration: as needed up to 48h
    contraindications:
      - { ar: لا تستخدم لو في شك ولو بسيط في سبب قلبي, en: Do not use if any cardiac concern remains }

workup:
  - name: { ar: تخطيط القلب الكهربي (ECG), en: 12-lead ECG }
    indication: { ar: لاستبعاد متلازمة الشريان التاجي الحادة, en: Rule out ACS }
    priority: emergent

when_to_escalate:
  - { ar: الألم ساعدش بالراحة بعد ١٥ دقيقة, en: Pain not relieved by 15 min of rest }
  - { ar: ضيق نفس متزايد أو إغماء, en: Worsening shortness of breath or syncope }

sources:
  - https://cks.nice.org.uk/topics/chest-pain/
  - https://www.who.int/publications/i/item/9789241549929    # WHO PEN
  - https://www.acc.org/guidelines/                            # AHA/ACC 2021

needs_clinical_review: true
```

**Field-by-field semantics** are defined in [`schemas.py`](../backend/app/clinical/schemas.py). The loader rejects any YAML that fails validation — so a typo in `severity` (`emergncy` instead of `emergency`) crashes startup, not production.

### 2. Drug formulary

Single file: `formulary/drugs.yaml`. Each entry is one drug, with **Egyptian brand names**, **weight-based pediatric doses**, **pregnancy category**, and **contraindications**.

```yaml
- id: ibuprofen
  generic_name: { ar: إيبوبروفين, en: Ibuprofen }
  brand_names_eg: [Brufen, Ibufen, Profinal, Megafen]
  drug_class: nsaid
  otc: true
  pregnancy_category: C        # avoid 3rd trimester (D)
  pediatric_min_age_years: 0.5 # ≥6 months

  dosing:
    - min_age_years: 12
      dose: "400 mg PO every 6-8 h with food"
      max_daily: "1200 mg/day OTC; 2400 mg/day Rx"
    - min_age_years: 0.5
      max_age_years: 12
      weight_based: true
      dose: "5-10 mg/kg PO every 6-8 h with food"
      max_daily: "30 mg/kg/day (max 1200 mg)"

  contraindications:
    - { ar: قرحة معدية نشطة, en: Active peptic ulcer }
    - { ar: نزف معدي مشتبه, en: Suspected GI bleed }
    - { ar: فشل كلوي (eGFR <30), en: Renal failure (eGFR <30) }
    - { ar: حمل (ثلث ثالث), en: Pregnancy (3rd trimester) }
    - { ar: ربو حساس للأسبرين, en: Aspirin-sensitive asthma }
    - { ar: شك في acute abdomen (يخفي علامات الزائدة), en: Suspected acute abdomen (masks signs) }

  common_interactions:
    - { ar: يقلل تأثير أدوية الضغط (ACE-i, ARB, diuretics), en: Blunts antihypertensives }
    - { ar: يزيد خطر نزف مع warfarin/aspirin/SSRI, en: Increased bleeding risk with anticoagulants/SSRI }

  sources: [BNF, NICE CKS NSAIDs]
```

**Why weight-based for pediatrics?** Because telling a parent "5 ml" without the child's weight is a dosing error vector. The schema forces the LLM to ask for weight before recommending.

### 3. Specialty intake templates

For the B2B "pre-visit intake" mode (a clinic uses MedAgent to collect a structured H&P before the patient walks into the appointment).

```yaml
id: general_practice
name: { ar: طب الأسرة / الباطنة العامة, en: General practice / family medicine }

fields:
  - { id: age, label: {…}, section: demographics, required: true }
  - { id: chief_complaint, label: {…}, section: chief_complaint, required: true }
  - { id: pmh_chronic, label: {…}, section: pmh, required: true }
  - { id: current_meds, label: {…}, section: meds, required: true }
  - { id: allergies, label: {…}, section: allergies, required: true }
  # … more fields organised by H&P section

required_red_flag_complaints:
  - chest_pain
  - headache
  - abdominal_pain
```

The agent walks through `fields` until all `required: true` slots are filled, then runs red-flag screening for every complaint in `required_red_flag_complaints`.

---

## How the agent uses the KB

```
patient message
       │
       ▼
┌────────────────────┐
│ detect_red_flags   │   (always)
└────────────────────┘
       │
       ▼
┌────────────────────┐
│ score_triage       │   (always)
└────────────────────┘
       │
       ▼
┌────────────────────┐
│ clinical_lookup    │   ◀── reads the YAML KB
│                    │      returns: differentials, red_flag_questions,
│                    │               self_care (with brand_names_eg),
│                    │               when_to_escalate, sources
└────────────────────┘
       │
       ▼
┌────────────────────┐
│ inject as synth.   │   the LLM sees this as a "tool I already called"
│ tool_call message  │
└────────────────────┘
       │
       ▼
┌────────────────────┐
│ LLM generates reply│   following the system prompt (3-phase workflow,
│                    │   hard rules, self-check)
└────────────────────┘
       │
       ▼
patient sees: empathy + 🟢🟡🔴 differential + intake questions
```

If `clinical_lookup` returns `matched: false`, the prompt forbids the LLM from inventing a differential or drug — it must ask clarifying questions instead.

---

## Sources & evidence base

Every chief complaint cites at least one of:

| Source | Coverage |
|---|---|
| **NICE Clinical Knowledge Summaries** (NICE CKS) | UK-equivalent primary-care guidance for ~330 conditions; openly licensed |
| **WHO IMCI / PEN** | Integrated Management of Childhood Illness + Package of Essential Noncommunicable Disease Interventions |
| **NICE Guidelines** (e.g. NG143 for fever in under-5s, NG59 for back pain, CG150 for headaches) | Full clinical guidelines |
| **AHA/ACC** | Cardiology-specific (chest pain) |
| **BNF** (British National Formulary) | Drug dosing reference for the formulary |

URLs are captured in each YAML's `sources:` field. When the LLM cites a recommendation, it can — and should — surface the source to the user.

---

## How to add a new chief complaint

> Goal: make this so boring a clinician can do it without engineering help.

### Step 1: Create the YAML

```bash
cp backend/app/clinical/chief_complaints/headache.yaml \
   backend/app/clinical/chief_complaints/<new_id>.yaml
```

Replace `id`, `name`, `synonyms`, `red_flags`, `differentials`, `followup_questions`, `self_care`, `workup`, `when_to_escalate`, `sources`.

### Step 2: Make sure synonyms cover patient phrasing

The agent uses synonym matching to route an unstructured patient message to the right YAML. Include:
- Both **Arabic** (MSA + Egyptian dialect) and **English**
- Patient-typed colloquialisms ("حجر على صدري" not just "ألم صدر")
- Common typos / variants

### Step 3: Validate

```bash
docker compose exec backend /app/.venv/bin/python -c \
  "from app.clinical.kb import get_kb; kb = get_kb(); print(kb.complaints['<new_id>'])"
```

If the file is malformed pydantic will reject it with a precise field path — fix and retry.

### Step 4: Get clinical sign-off

Until a licensed physician has reviewed the file, leave `needs_clinical_review: true`. The CI gate can list every still-unreviewed complaint:

```bash
grep -l "needs_clinical_review: true" backend/app/clinical/chief_complaints/
```

### Step 5: Smoke-test

Open the chat, type a synonym, verify the differential + self-care reflect your edits. See [`MANUAL_VERIFY.md`](MANUAL_VERIFY.md) for the full checklist.

---

## How to add a new drug

Append to `backend/app/clinical/formulary/drugs.yaml` following the existing pattern. Pediatric dosing **must** be `weight_based: true` with a `mg/kg` formula — never recommend a flat pediatric dose without weight.

---

## Anti-patterns (things we deliberately don't do)

| Anti-pattern | Why we don't do it |
|---|---|
| Hardcoding drug names in the LLM prompt | Locks clinical content to a prompt edit; no audit trail; no validation. |
| Numeric confidence percentages (`67%`) | LLMs invent these. Qualitative labels (`very_common` / `common` / `rare` / `emergency`) are honest. |
| One YAML for everything | Each file should be small enough that a clinician can read it in one sitting. |
| Bulk import from a single textbook | Different sources fit different contexts (NICE for primary care, WHO for global / pediatric, AHA for cardio). Curation > scraping. |
| Auto-generating YAML with an LLM | Defeats the purpose. The KB exists so a human is in the loop on every clinical claim. |

---

## Roadmap for the KB

| Priority | Item |
|---|---|
| 🔴 Critical | Get all 10 existing complaints reviewed + signed off by a licensed physician (`needs_clinical_review: false`). |
| 🔴 Critical | Add: hyperglycemia warning, hypoglycemia, dyspepsia, UTI, dizziness — common complaints currently triggering `matched: false`. |
| 🟠 High | Pediatric variants of fever / cough / diarrhea (different red-flag thresholds, weight-based dosing). |
| 🟠 High | Pregnancy-aware variants of headache / abdo pain / chest pain. |
| 🟡 Medium | Mental-health protocols (depression, anxiety, panic attack — wired to PHQ-9 / GAD-7 screening). |
| 🟡 Medium | More specialty templates (OBGYN, dermatology, ortho). |
| 🟢 Nice-to-have | A clinician-facing web editor that writes valid YAML (so they never touch a file directly). |

---

## See also

- [`schemas.py`](../backend/app/clinical/schemas.py) — the source of truth for what each field means
- [`kb.py`](../backend/app/clinical/kb.py) — loader implementation (singleton, `lru_cached`, Arabic-normalised synonym index)
- [`clinical_lookup.py`](../backend/app/ai/tools/clinical_lookup.py) — the tool that surfaces KB content to the agent
- [`safety.md`](safety.md) — how the KB integrates with the safety stack
- [`ai-pipeline.md`](ai-pipeline.md) — broader agent design

---

_Last updated: 2026-05-24_
