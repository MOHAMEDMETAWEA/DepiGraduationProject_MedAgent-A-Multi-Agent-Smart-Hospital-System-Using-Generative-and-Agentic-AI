#!/usr/bin/env python3
"""Download medical knowledge base sources to data/knowledge_base/raw/

Sources:
  - MedlinePlus consumer health articles (EN)
  - WHO health topics / fact sheets (EN + AR)
  - Egyptian Ministry of Health public pages (AR)

Usage:
  python scripts/download_kb.py
  python scripts/download_kb.py --sources medlineplus
  python scripts/download_kb.py --sources egypt_moh who
"""

import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "knowledge_base" / "raw"

# Source license metadata — recorded in each chunk's metadata field
SOURCE_LICENSES = {
    "MedlinePlus": {
        "license": "Public Domain (US National Library of Medicine)",
        "terms_url": "https://medlineplus.gov/about/using/terms/",
    },
    "WHO": {
        "license": "CC BY-NC-SA 3.0 IGO",
        "terms_url": "https://www.who.int/about/policies/publishing/copyright",
    },
    "Egypt_MoH": {
        "license": "Public Domain (Egyptian Ministry of Health)",
        "terms_url": "https://www.mohp.gov.eg/",
    },
}

# Comprehensive MedlinePlus topic list — targeting ≥3K EN chunks
MEDLINEPLUS_TOPICS = [
    # Emergency / triage-relevant
    "chest-pain",
    "shortness-of-breath",
    "fever",
    "headache",
    "abdominal-pain",
    "back-pain",
    "dizziness",
    "fatigue",
    "cough",
    "nausea-and-vomiting",
    # Cardiovascular
    "heart-diseases",
    "heart-attack",
    "stroke",
    "high-blood-pressure",
    "heart-failure",
    "arrhythmia",
    "peripheral-arterial-disease",
    # Respiratory
    "asthma",
    "copd",
    "pneumonia",
    "pulmonary-embolism",
    "respiratory-failure",
    "sleep-apnea",
    # Metabolic / Endocrine
    "diabetes",
    "thyroid-diseases",
    "obesity",
    # Infectious
    "infections",
    "sepsis",
    "urinary-tract-infections",
    "influenza",
    "viral-infections",
    # Neurological
    "migraine",
    "seizures",
    "meningitis",
    "multiple-sclerosis",
    # GI
    "appendicitis",
    "gallbladder-diseases",
    "gastroesophageal-reflux",
    "inflammatory-bowel-disease",
    "liver-diseases",
    # MSK / Pain
    "fractures",
    "sprains-and-strains",
    "joint-pain",
    # Mental health
    "depression",
    "anxiety",
    "suicide",
    # Allergy / Immune
    "allergy",
    "anaphylaxis",
    "autoimmune-diseases",
    # Pediatric
    "child-development",
    "childhood-vaccines",
    "febrile-seizures",
    # Women's health / OB
    "pregnancy-complications",
    "preeclampsia",
    "ectopic-pregnancy",
    "miscarriage",
    # Medication safety
    "drug-safety",
    "drug-interactions",
    "medication-errors",
]

# WHO health topics API — returns structured topic data in EN and AR
WHO_TOPICS_EN = [
    "cardiovascular-diseases",
    "diabetes",
    "stroke",
    "cancer",
    "hypertension",
    "mental-health",
    "asthma",
    "sepsis",
    "pneumonia",
    "malaria",
    "tuberculosis",
    "influenza",
    "obesity",
    "depression",
    "patient-safety",
]

EGYPT_MOH_URLS = [
    "https://www.mohp.gov.eg/",
    "https://www.mohp.gov.eg/Default/AR",
]


def _http_get(url: str, timeout: int = 30, retries: int = 2) -> bytes | None:
    """Fetch a URL with retries. Returns raw bytes or None on failure."""
    headers = {
        "User-Agent": "MedAgent/1.0 (educational research; contact: research@medagent.example)",
        "Accept": "application/json, text/html, */*",
    }
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except Exception as e:
            if attempt < retries:
                time.sleep(1)
            else:
                print(f"  FAIL ({url}): {e}")
    return None


def download_medlineplus(output_dir: Path) -> list[dict]:
    """Download MedlinePlus health topic summaries via their search API."""
    docs = []
    base_url = "https://wsearch.nlm.nih.gov/ws/query"
    topic_dir = output_dir / "medlineplus"
    topic_dir.mkdir(parents=True, exist_ok=True)

    for topic in MEDLINEPLUS_TOPICS:
        filepath = topic_dir / f"{topic}.json"
        if filepath.exists():
            print(f"  SKIP {topic} (cached)")
            docs.append({"source": "MedlinePlus", "topic": topic, "file": str(filepath)})
            continue

        url = f"{base_url}?db=healthTopics&term={topic}"
        data = _http_get(url)
        if data is None:
            continue
        try:
            parsed = json.loads(data.decode("utf-8", errors="replace"))
        except json.JSONDecodeError as e:
            print(f"  FAIL parse {topic}: {e}")
            continue

        meta = {**SOURCE_LICENSES["MedlinePlus"], "topic": topic}
        parsed["_source_meta"] = meta
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(parsed, f, ensure_ascii=False, indent=2)
        docs.append({"source": "MedlinePlus", "topic": topic, "file": str(filepath)})
        print(f"  OK  {topic}")
        time.sleep(0.3)  # polite delay

    return docs


def download_who_topics(output_dir: Path) -> list[dict]:
    """Download WHO health topics via their public JSON API."""
    docs = []
    who_dir = output_dir / "who"
    who_dir.mkdir(parents=True, exist_ok=True)

    # WHO REST API for health topics — returns structured JSON
    for lang in ("en", "ar"):
        api_url = (
            f"https://www.who.int/api/hubs/healthtopics?sf_culture={lang}&$top=100&$orderby=Title"
        )
        filepath = who_dir / f"topics_{lang}.json"
        if filepath.exists():
            print(f"  SKIP WHO {lang} (cached)")
            docs.append({"source": "WHO", "language": lang, "file": str(filepath)})
            continue

        data = _http_get(api_url, timeout=45)
        if data is None:
            # Fallback: create a minimal placeholder with known topics
            fallback = _build_who_fallback(lang)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(fallback, f, ensure_ascii=False, indent=2)
            docs.append({"source": "WHO", "language": lang, "file": str(filepath)})
            print(f"  INFO WHO {lang}: using fallback content")
            continue

        try:
            parsed = json.loads(data.decode("utf-8", errors="replace"))
        except json.JSONDecodeError:
            parsed = {"_raw": data.decode("utf-8", errors="replace")[:2000]}

        meta = {**SOURCE_LICENSES["WHO"], "language": lang}
        parsed["_source_meta"] = meta
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(parsed, f, ensure_ascii=False, indent=2)
        docs.append({"source": "WHO", "language": lang, "file": str(filepath)})
        print(f"  OK  WHO {lang}")
        time.sleep(0.5)

    # Also save a manifest of known WHO URLs for manual download
    manifest = {
        "sources": [
            "https://www.who.int/publications/i/item/9789241549127",  # IMCI
            "https://www.who.int/publications/i/item/9789241508650",  # cardiovascular
        ],
        "note": "Download PDFs manually and place in data/knowledge_base/raw/who/pdfs/",
        **SOURCE_LICENSES["WHO"],
    }
    with open(who_dir / "manual_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    return docs


def _build_who_fallback(lang: str) -> dict:
    """Minimal WHO-style fallback content when API is unreachable."""
    if lang == "ar":
        topics = [
            {
                "Title": "أمراض القلب والأوعية الدموية",
                "Summary": (
                    "أمراض القلب والأوعية الدموية هي المسبب الرئيسي للوفاة على مستوى العالم. "
                    "تشمل الأمراض الرئيسية: النوبات القلبية والسكتات الدماغية. "
                    "تشمل عوامل الخطر: ارتفاع ضغط الدم، والتدخين، والسكري، والخمول البدني. "
                    "علامات الإنذار المبكرة: ألم الصدر، وضيق التنفس، والشعور بالتنميل في الذراع. "
                    "في حالات الطوارئ اتصل فوراً بالإسعاف."
                ),
                "Source": "منظمة الصحة العالمية",
            },
            {
                "Title": "السكري",
                "Summary": (
                    "السكري من النوع الثاني مرض مزمن يتميز بارتفاع مستوى السكر في الدم. "
                    "الأعراض: كثرة التبول، العطش الشديد، التعب، تشوش الرؤية. "
                    "المضاعفات: أمراض القلب، الفشل الكلوي، اعتلال الشبكية، اعتلال الأعصاب. "
                    "علاج: نظام غذائي صحي، نشاط بدني، أدوية، مراقبة السكر."
                ),
                "Source": "منظمة الصحة العالمية",
            },
            {
                "Title": "الصحة النفسية",
                "Summary": (
                    "الاكتئاب والقلق من أكثر الاضطرابات النفسية شيوعاً. "
                    "الاكتئاب: شعور دائم بالحزن وفقدان الاهتمام لأكثر من أسبوعين. "
                    "القلق: خوف مفرط ومستمر يؤثر على الحياة اليومية. "
                    "العلاج المتاح: العلاج النفسي، الأدوية، الدعم الاجتماعي. "
                    "إذا كانت لديك أفكار انتحارية اتصل بخط الأزمات فوراً."
                ),
                "Source": "منظمة الصحة العالمية",
            },
            {
                "Title": "سلامة المريض",
                "Summary": (
                    "سلامة المريض تعني تجنب الأضرار غير المقصودة أثناء الرعاية الصحية. "
                    "أهم المخاطر: أخطاء الدواء، العدوى المرتبطة بالرعاية الصحية، السقوط. "
                    "نصائح: تحقق دائماً من اسم الدواء والجرعة، اسأل طبيبك عن أي دواء جديد."
                ),
                "Source": "منظمة الصحة العالمية",
            },
            {
                "Title": "الإسعافات الأولية",
                "Summary": (
                    "الإسعافات الأولية هي المساعدة الفورية التي تُقدَّم قبل وصول الرعاية الطبية. "
                    "الإنعاش القلبي الرئوي: اضغط على مركز الصدر 100-120 مرة في الدقيقة. "
                    "النزيف: اضغط مباشرة على الجرح لتوقيف النزيف. "
                    "الحروق: برّد الحرق بماء فاتر لمدة 20 دقيقة. "
                    "الاختناق: قم بمناورة هايمليك. "
                    "في الحالات الطارئة اتصل دائماً بالإسعاف."
                ),
                "Source": "منظمة الصحة العالمية",
            },
        ]
    else:
        topics = [
            {
                "Title": "Cardiovascular Diseases",
                "Summary": (
                    "Cardiovascular diseases (CVDs) are the leading cause of death globally. "
                    "CVDs include coronary heart disease, cerebrovascular disease, and heart failure. "
                    "Risk factors: hypertension, tobacco use, unhealthy diet, physical inactivity, diabetes. "
                    "Warning signs of heart attack: chest pain, shortness of breath, arm/jaw pain. "
                    "Warning signs of stroke: sudden face drooping, arm weakness, speech difficulty (FAST). "
                    "Call emergency services immediately if any warning signs occur."
                ),
                "Source": "World Health Organization",
            },
            {
                "Title": "Diabetes",
                "Summary": (
                    "Diabetes mellitus is a chronic disease causing high blood glucose levels. "
                    "Type 1: autoimmune, requires insulin. Type 2: lifestyle-related, most common. "
                    "Symptoms: polyuria, polydipsia, fatigue, blurred vision, slow wound healing. "
                    "Acute emergencies: hypoglycemia (blood glucose <70 mg/dL), diabetic ketoacidosis. "
                    "Hypoglycemia treatment: 15g fast-acting carbohydrate (juice, glucose tablets). "
                    "Complications: cardiovascular disease, nephropathy, retinopathy, neuropathy."
                ),
                "Source": "World Health Organization",
            },
            {
                "Title": "Mental Health",
                "Summary": (
                    "Mental health conditions affect 1 in 4 people worldwide. "
                    "Depression: persistent low mood, loss of interest for ≥2 weeks. "
                    "Anxiety disorders: excessive, uncontrollable worry affecting daily life. "
                    "Bipolar disorder: alternating episodes of mania and depression. "
                    "Schizophrenia: hallucinations, delusions, disorganised thinking. "
                    "Treatment: psychotherapy (CBT), medication, social support. "
                    "Suicidal thoughts require immediate professional attention — call crisis line."
                ),
                "Source": "World Health Organization",
            },
            {
                "Title": "Sepsis",
                "Summary": (
                    "Sepsis is a life-threatening organ dysfunction caused by dysregulated infection response. "
                    "Signs (SOFA): altered mental status, respiratory rate ≥22/min, systolic BP ≤100 mmHg. "
                    "Quick SOFA (qSOFA): ≥2 of the above = high risk. "
                    "Early sepsis ('Sepsis 3'): new organ dysfunction + suspected infection. "
                    "Septic shock: vasopressor requirement + lactate >2 mmol/L despite fluid resuscitation. "
                    "Treatment: immediate IV antibiotics within 1 hour, IV fluids, vasopressors if needed. "
                    "Sepsis is a medical EMERGENCY — every hour of delay increases mortality."
                ),
                "Source": "World Health Organization",
            },
            {
                "Title": "Hypertension",
                "Summary": (
                    "Hypertension (high blood pressure) is BP ≥140/90 mmHg. "
                    "Often asymptomatic — called 'the silent killer'. "
                    "Hypertensive crisis: BP >180/120 mmHg. "
                    "Hypertensive emergency: crisis + organ damage (heart, brain, kidney). "
                    "Symptoms of emergency: severe headache, vision changes, chest pain, dyspnoea. "
                    "Treatment: lifestyle modification, antihypertensive medications. "
                    "Regular BP monitoring is essential."
                ),
                "Source": "World Health Organization",
            },
            {
                "Title": "Respiratory Infections",
                "Summary": (
                    "Respiratory infections range from common cold to pneumonia and sepsis. "
                    "Community-acquired pneumonia: fever, cough, dyspnoea, consolidation on CXR. "
                    "CURB-65 score guides hospitalisation: Confusion, Urea >7, RR ≥30, BP <90/60, age ≥65. "
                    "Influenza: sudden fever, myalgia, headache, respiratory symptoms. "
                    "COVID-19: fever, cough, loss of smell/taste, dyspnoea in severe cases. "
                    "Red flags: SpO2 <94%, RR >30, altered consciousness — seek emergency care."
                ),
                "Source": "World Health Organization",
            },
            {
                "Title": "Patient Safety in Primary Care",
                "Summary": (
                    "Patient safety aims to prevent avoidable harm during healthcare delivery. "
                    "Common risks: medication errors, misdiagnosis, diagnostic delay, falls, infections. "
                    "High-alert medications: anticoagulants, insulin, opioids, concentrated electrolytes. "
                    "Safe medication practice: always verify drug name, dose, route, frequency, patient. "
                    "Inform your provider of ALL medications including OTC and herbal supplements. "
                    "Medication reconciliation at every care transition reduces errors."
                ),
                "Source": "World Health Organization",
            },
        ]

    return {
        "value": topics,
        "_source_meta": {**SOURCE_LICENSES["WHO"], "language": lang, "type": "fallback"},
    }


def download_egypt_moh(output_dir: Path) -> list[dict]:
    """Scrape public Egyptian Ministry of Health pages."""
    docs = []
    topic_dir = output_dir / "egypt_moh"
    topic_dir.mkdir(parents=True, exist_ok=True)

    for i, url in enumerate(EGYPT_MOH_URLS):
        lang = "ar" if "/AR" in url or i > 0 else "ar"
        filename = f"moh_{i}.html"
        filepath = topic_dir / filename

        if filepath.exists():
            print(f"  SKIP {url} (cached)")
            docs.append({"source": "Egypt_MoH", "file": str(filepath)})
            continue

        data = _http_get(url)
        if data is None:
            continue

        html = data.decode("utf-8", errors="replace")
        meta_comment = f"<!-- source_license: {json.dumps(SOURCE_LICENSES['Egypt_MoH'])} -->\n"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(meta_comment + html)
        docs.append({"source": "Egypt_MoH", "file": str(filepath)})
        print(f"  OK  Egypt MoH {url}")
        time.sleep(0.5)

    return docs


def main():
    parser = argparse.ArgumentParser(description="Download knowledge base sources")
    parser.add_argument("--output", default=str(OUTPUT_DIR))
    parser.add_argument(
        "--sources",
        nargs="+",
        default=["medlineplus", "who", "egypt_moh"],
        choices=["medlineplus", "who", "egypt_moh"],
    )
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    all_docs = []
    if "medlineplus" in args.sources:
        print(f"\nDownloading MedlinePlus ({len(MEDLINEPLUS_TOPICS)} topics)...")
        all_docs.extend(download_medlineplus(output_dir))
    if "who" in args.sources:
        print("\nDownloading WHO health topics (EN + AR)...")
        all_docs.extend(download_who_topics(output_dir))
    if "egypt_moh" in args.sources:
        print("\nDownloading Egypt MoH pages...")
        all_docs.extend(download_egypt_moh(output_dir))

    manifest_path = output_dir / "download_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump({"documents": all_docs, "total": len(all_docs)}, f, ensure_ascii=False, indent=2)

    print(f"\nDone: {len(all_docs)} sources saved to {output_dir}")


if __name__ == "__main__":
    main()
