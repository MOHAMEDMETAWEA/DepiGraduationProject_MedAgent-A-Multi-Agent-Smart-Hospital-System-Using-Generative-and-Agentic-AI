#!/usr/bin/env python3
"""
Build a curated medical knowledge base for MedAgent RAG.
Creates structured medical content covering common triage topics in Arabic and English,
then runs chunking, embedding, and storage into pgvector.

Usage:
    uv run python scripts/build_curated_kb.py
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add backend directory to path
_backend_root = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(_backend_root))

# ── Curated medical knowledge in AR + EN ──
# Each entry: {source, title, content, language, category}

MEDICAL_KNOWLEDGE = [
    # ── CARDIAC (EN + AR) ──
    {
        "source": "WHO Guidelines",
        "title": "Heart Attack Warning Signs",
        "content": """Heart attack warning signs: Chest pain or discomfort (pressure, squeezing, fullness). Pain spreading to shoulder, arm, back, neck or jaw. Shortness of breath with or without chest discomfort. Cold sweat, nausea, vomiting, or lightheadedness. Women may experience different symptoms: unusual fatigue, sleep disturbance, shortness of breath, indigestion, anxiety. Call emergency services (123 in Egypt, 911 in US) immediately if any of these signs appear. Do not drive yourself to the hospital. Chew aspirin (325mg) if not allergic and no contraindications. Every minute matters — early treatment saves heart muscle.""",
        "language": "en",
        "category": "cardiac",
    },
    {
        "source": "WHO Guidelines",
        "title": "علامات النوبة القلبية التحذيرية",
        "content": """علامات النوبة القلبية التحذيرية: ألم أو ضغط في الصدر (ضغط، عصر، امتلاء). ألم يمتد للكتف أو الذراع أو الظهر أو الرقبة أو الفك. ضيق تنفس مع أو بدون ألم الصدر. عرق بارد، غثيان، قيء، دوخة. النساء قد يعانين من أعراض مختلفة: إرهاق غير معتاد، اضطراب النوم، ضيق تنفس، عسر هضم، قلق. اتصل بالإسعاف فوراً (123 في مصر) إذا ظهرت أي من هذه العلامات. لا تقد بنفسك للمستشفى. امضغ أسبرين (325 مجم) إذا لم تكن تعاني من حساسية ولا توجد موانع. كل دقيقة مهمة — العلاج المبكر ينقذ عضلة القلب.""",
        "language": "ar",
        "category": "cardiac",
    },
    {
        "source": "WHO Guidelines",
        "title": "Stroke FAST Signs",
        "content": """Stroke FAST warning signs: Face drooping — one side of the face droops or is numb, ask person to smile to check. Arm weakness — one arm is weak or numb, ask person to raise both arms. Speech difficulty — speech is slurred or person cannot speak, ask to repeat a simple sentence. Time to call emergency — if any signs present, call ambulance immediately. Other stroke symptoms: sudden confusion, trouble seeing in one or both eyes, sudden severe headache, trouble walking, dizziness. Stroke is a medical emergency. Treatment within 3-4.5 hours greatly improves outcomes.""",
        "language": "en",
        "category": "neurological",
    },
    {
        "source": "WHO Guidelines",
        "title": "علامات الجلطة الدماغية السريعة (FAST)",
        "content": """علامات الجلطة الدماغية السريعة (FAST): الوجه — تدلي أو تنميل في جانب واحد من الوجه، اطلب من الشخص أن يبتسم. الذراع — ضعف أو تنميل في ذراع واحدة، اطلب رفع الذراعين. الكلام — كلام غير واضح أو صعوبة في الكلام، اطلب تكرار جملة بسيطة. الوقت — اتصل بالإسعاف فوراً إذا ظهرت أي علامة. أعراض أخرى للجلطة: ارتباك مفاجئ، صعوبة في الرؤية في عين أو اثنتين، صداع شديد مفاجئ، صعوبة في المشي، دوخة. الجلطة حالة طبية طارئة. العلاج خلال 3-4.5 ساعات يحسن النتائج بشكل كبير.""",
        "language": "ar",
        "category": "neurological",
    },
    # ── RESPIRATORY (EN + AR) ──
    {
        "source": "WHO Guidelines",
        "title": "Respiratory Distress",
        "content": """Respiratory distress emergency signs: Severe shortness of breath, inability to speak in full sentences, gasping for air. Blue or gray lips, face, or fingernails (cyanosis). Rapid breathing (tachypnea) — more than 30 breaths per minute in adults. Chest retractions (skin pulling between ribs). Stridor — a high-pitched wheezing sound when breathing. Confusion or decreased alertness due to low oxygen. These are life-threatening signs requiring immediate emergency care. While waiting for ambulance: sit the person upright, loosen tight clothing, ensure fresh air. Do NOT lay the person flat if they're struggling to breathe.""",
        "language": "en",
        "category": "respiratory",
    },
    {
        "source": "WHO Guidelines",
        "title": "ضيق التنفس الحاد",
        "content": """علامات الطوارئ التنفسية: ضيق شديد في التنفس، عدم القدرة على التكلم بجمل كاملة، صعوبة في التقاط النفس. ازرقاق الشفاه أو الوجه أو الأظافر. تنفس سريع — أكثر من 30 نفس في الدقيقة للبالغين. انكماش الصدر بين الضلوع. صرير — صوت صفير حاد عند التنفس. ارتباك أو نقص الانتباه بسبب نقص الأكسجين. هذه علامات مهددة للحياة تتطلب رعاية طارئة فورية. أثناء انتظار الإسعاف: أجلس الشخص بشكل مستقيم، خفف الملابس الضيقة، تأكد من وجود هواء نقي. لا تضع الشخص مستلقياً إذا كان يعاني من صعوبة في التنفس.""",
        "language": "ar",
        "category": "respiratory",
    },
    # ── ANAPHYLAXIS (EN + AR) ──
    {
        "source": "WHO Guidelines",
        "title": "Anaphylaxis Emergency",
        "content": """Anaphylaxis is a severe life-threatening allergic reaction. Signs: swelling of face, lips, tongue, or throat. Difficulty breathing or wheezing. Hives or widespread rash. Rapid heartbeat. Dizziness or fainting. Nausea, vomiting, or diarrhea. Feeling of impending doom. Common triggers: foods (peanuts, tree nuts, shellfish), medications (antibiotics, NSAIDs), insect stings (bees, wasps), latex. Emergency treatment: Epinephrine (adrenaline) injection into outer thigh — this is the FIRST and ONLY life-saving treatment. Call emergency services immediately. If person has auto-injector (EpiPen), use it. Antihistamines are NOT a substitute for epinephrine. Person should go to hospital even if symptoms improve after epinephrine.""",
        "language": "en",
        "category": "allergy",
    },
    {
        "source": "WHO Guidelines",
        "title": "الحساسية المفرطة (صدمة الحساسية)",
        "content": """الحساسية المفرطة هي ردة فعل تحسسية شديدة مهددة للحياة. العلامات: تورم الوجه، الشفاه، اللسان، أو الحلق. صعوبة في التنفس أو صفير. شرى أو طفح جلدي واسع الانتشار. تسارع ضربات القلب. دوخة أو إغماء. غثيان، قيء، أو إسهال. إحساس بدنو الموت. المسببات الشائعة: الأطعمة (الفول السوداني، المكسرات، المحار)، الأدوية (مضادات حيوية، مسكنات)، لسعات الحشرات (نحل، دبابير)، اللاتكس. العلاج الطارئ: حقن الإبينفرين (الأدرينالين) في الفخذ الخارجي — هذا هو العلاج الأول والوحيد المنقذ للحياة. اتصل بالإسعاف فوراً. مضادات الهيستامين ليست بديلاً عن الإبينفرين. يجب نقل الشخص للمستشفى حتى لو تحسنت الأعراض بعد الإبينفرين.""",
        "language": "ar",
        "category": "allergy",
    },
    # ── BLEEDING (EN + AR) ──
    {
        "source": "WHO Guidelines",
        "title": "Severe Bleeding Control",
        "content": """Severe bleeding is a life-threatening emergency. Signs of severe bleeding: Blood spurting from wound, blood pooling on ground, blood soaking through clothing rapidly, signs of shock (pale skin, rapid breathing, confusion). First aid for severe bleeding: Apply direct firm pressure to wound with clean cloth. Do NOT remove embedded objects — apply pressure around the object. Use tourniquet only if direct pressure fails and bleeding is life-threatening from a limb. Keep person warm and calm. Lay person flat and elevate legs if possible (unless spinal injury suspected). Call emergency services immediately. Do not wash severe wounds. Do not apply a tourniquet over a joint.""",
        "language": "en",
        "category": "trauma",
    },
    {
        "source": "WHO Guidelines",
        "title": "السيطرة على النزيف الحاد",
        "content": """النزيف الحاد هو حالة طارئة مهددة للحياة. علامات النزيف الحاد: دم يتدفق من الجرح، تجمع دم على الأرض، تشبع الملابس بالدم بسرعة، علامات الصدمة (جلد شاحب، تنفس سريع، ارتباك). الإسعافات الأولية للنزيف الحاد: اضغط مباشرة وبقوة على الجرح بقطعة قماش نظيفة. لا تزل الأشياء المضمنة في الجرح — اضغط حولها. استخدم الرباط الضاغط فقط إذا فشل الضغط المباشر وكان النزيف مهدداً للحياة في أحد الأطراف. حافظ على دفء وهدوء الشخص. أرقد الشخص بشكل مسطح وارفع الساقين إذا أمكن (ما لم تشتبه في إصابة العمود الفقري). اتصل بالإسعاف فوراً. لا تغسل الجروح الشديدة. لا تضع رباطاً ضاغطاً فوق مفصل.""",
        "language": "ar",
        "category": "trauma",
    },
    # ── FEVER (EN + AR) ──
    {
        "source": "MedlinePlus",
        "title": "Fever in Adults",
        "content": """Fever is body temperature above 38°C (100.4°F). Fever is the body's natural defense against infection and is usually not harmful. When to seek urgent care: temperature above 39.5°C (103°F) that does not respond to medication. Fever lasting more than 3 days. Severe headache with fever (possible meningitis). Stiff neck with fever. Confusion with fever. Seizure. Severe abdominal pain. Difficulty breathing. Dehydration signs: dry mouth, decreased urination, dizziness when standing. Treatment: rest, plenty of fluids, paracetamol (acetaminophen) for temperature reduction. Do NOT give aspirin to children or teenagers (Reye's syndrome risk).""",
        "language": "en",
        "category": "infectious",
    },
    {
        "source": "MedlinePlus",
        "title": "الحمى عند البالغين",
        "content": """الحمى هي ارتفاع درجة حرارة الجسم فوق 38 درجة مئوية. الحمى هي دفاع الجسم الطبيعي ضد العدوى وعادة لا تكون ضارة. متى تطلب رعاية عاجلة: درجة حرارة فوق 39.5 درجة مئوية لا تستجيب للأدوية. حمى مستمرة لأكثر من 3 أيام. صداع شديد مع الحمى (احتمال التهاب السحايا). تيبس الرقبة مع الحمى. ارتباك مع الحمى. تشنجات. ألم شديد في البطن. صعوبة في التنفس. علامات الجفاف: جفاف الفم، قلة التبول، دوخة عند الوقوف. العلاج: راحة، شرب سوائل بكثرة، باراسيتامول لتخفيض الحرارة. لا تعط الأسبرين للأطفال أو المراهقين (خطر متلازمة راي).""",
        "language": "ar",
        "category": "infectious",
    },
    # ── HEADACHE (EN + AR) ──
    {
        "source": "MedlinePlus",
        "title": "Headache Red Flags",
        "content": """Most headaches are not serious and resolve on their own. Red-flag headaches requiring urgent evaluation: Sudden severe headache (thunderclap headache — worst headache of your life, reaching maximum intensity within seconds). Headache with fever and stiff neck. Headache after head injury. Headache with confusion, seizure, or loss of consciousness. New headache in person over 50. Headache that worsens with coughing or straining. Headache with vision changes or eye pain. Headache with weakness or numbness on one side of body. Common headache types: tension headache (band-like pressure, mild-moderate), migraine (throbbing, one-sided, moderate-severe with nausea/light sensitivity). Treatment: rest, hydration, over-the-counter pain relievers. Avoid known triggers for migraines.""",
        "language": "en",
        "category": "neurology",
    },
    {
        "source": "MedlinePlus",
        "title": "الصداع — علامات الخطر",
        "content": """معظم حالات الصداع ليست خطيرة وتزول من تلقاء نفسها. الصداع الذي يحتاج تقييماً عاجلاً: صداع شديد مفاجئ (صداع الرعد — أسوأ صداع في حياتك، يصل لأقصى شدة في ثوان). صداع مع حمى وتيبس الرقبة. صداع بعد إصابة في الرأس. صداع مع ارتباك أو تشنج أو فقدان وعي. صداع جديد في شخص فوق 50 سنة. صداع يزداد مع السعال أو الشد. صداع مع تغيرات في الرؤية أو ألم في العين. صداع مع ضعف أو تنميل في جانب واحد من الجسم. أنواع الصداع الشائعة: صداع التوتر (ضغط مثل الحزام، خفيف لمتوسط)، الشقيقة (نابض، في جانب واحد، متوسط لشديد مع غثيان/حساسية للضوء). العلاج: راحة، ترطيب، مسكنات بدون وصفة. تجنب مثيرات الشقيقة المعروفة.""",
        "language": "ar",
        "category": "neurology",
    },
    # ── ABDOMINAL PAIN (EN + AR) ──
    {
        "source": "WHO Guidelines",
        "title": "Abdominal Pain — Emergency Signs",
        "content": """Abdominal pain emergency signs: Sudden severe abdominal pain. Pain with rigid, board-like abdomen. Vomiting blood or passing blood in stool. Inability to pass stool or gas with abdominal swelling. Severe pain with fever. Pain in right lower abdomen (possible appendicitis). Abdominal pain after trauma. Abdominal pain during pregnancy with bleeding. Common causes of abdominal pain: gastroenteritis (stomach flu — usually viral, self-limiting), constipation, indigestion, gastritis, food poisoning. Seek medical attention for: pain lasting more than 24 hours, pain that wakes you from sleep, unexplained weight loss, persistent nausea/vomiting. Do not apply heat to undiagnosed severe abdominal pain.""",
        "language": "en",
        "category": "abdominal",
    },
    {
        "source": "WHO Guidelines",
        "title": "ألم البطن — علامات الطوارئ",
        "content": """علامات الطوارئ لألم البطن: ألم حاد مفاجئ في البطن. ألم مع تصلب البطن مثل اللوح الخشبي. تقيؤ دم أو خروج دم مع البراز. عدم القدرة على إخراج براز أو غازات مع انتفاخ البطن. ألم شديد مع حمى. ألم في الجزء السفلي الأيمن من البطن (احتمال التهاب الزائدة الدودية). ألم بطن بعد إصابة. ألم بطن أثناء الحمل مع نزيف. الأسباب الشائعة لألم البطن: التهاب المعدة والأمعاء (عادة فيروسي، يزول تلقائياً)، إمساك، عسر هضم، التهاب المعدة، تسمم غذائي. اطلب الرعاية الطبية: ألم يستمر أكثر من 24 ساعة، ألم يوقظك من النوم، فقدان وزن غير مفسر، غثيان/قيء مستمر. لا تضع حرارة على ألم بطن حاد غير مشخص.""",
        "language": "ar",
        "category": "abdominal",
    },
    # ── MENTAL HEALTH (EN + AR) ──
    {
        "source": "WHO Guidelines",
        "title": "Mental Health Crisis Signs",
        "content": """Mental health emergencies require immediate intervention. Emergency signs: Suicidal thoughts or plans — take these seriously and seek immediate help. Self-harm behavior. Severe panic attack with chest pain or difficulty breathing. Psychotic symptoms: hallucinations, delusions, disorganized speech. Severe depression with inability to care for self. Risk factors for suicide: previous attempts, mental illness, substance abuse, chronic pain, recent loss, isolation. If someone expresses suicidal thoughts: Listen without judgment, take them seriously, do not leave them alone, remove means of self-harm, seek professional help immediately. Depression symptoms: persistent sadness, loss of interest, sleep changes, appetite changes, fatigue, difficulty concentrating, feelings of worthlessness. Anxiety symptoms: excessive worry, restlessness, muscle tension, sleep disturbance, panic attacks. Both depression and anxiety are treatable conditions.""",
        "language": "en",
        "category": "mental_health",
    },
    {
        "source": "WHO Guidelines",
        "title": "علامات الأزمة النفسية الطارئة",
        "content": """الأزمات النفسية تتطلب تدخلاً فورياً. علامات الطوارئ: أفكار أو خطط انتحارية — خذها بجدية واطلب المساعدة فوراً. سلوك إيذاء النفس. نوبة هلع شديدة مع ألم في الصدر أو صعوبة في التنفس. أعراض ذهانية: هلاوس، أوهام، كلام غير منظم. اكتئاب شديد مع عدم القدرة على رعاية النفس. عوامل خطر الانتحار: محاولات سابقة، مرض نفسي، إدمان، ألم مزمن، فقدان حديث، عزلة. إذا عبر شخص عن أفكار انتحارية: استمع بدون إصدار أحكام، خذ كلامه بجدية، لا تتركه وحده، أبعد وسائل إيذاء النفس، اطلب مساعدة متخصصة فوراً. أعراض الاكتئاب: حزن مستمر، فقدان الاهتمام، تغيرات النوم، تغيرات الشهية، إرهاق، صعوبة التركيز، مشاعر انعدام القيمة. أعراض القلق: قلق مفرط، توتر، شد عضلي، اضطراب النوم، نوبات هلع. الاكتئاب والقلق حالتان قابلتان للعلاج.""",
        "language": "ar",
        "category": "mental_health",
    },
    # ── PEDIATRIC (EN + AR) ──
    {
        "source": "WHO Guidelines",
        "title": "Pediatric Emergency Signs",
        "content": """Children require special attention as they can deteriorate rapidly. Emergency signs in children: Fever above 40°C (104°F) especially in infants under 3 months. Febrile seizures (convulsions with fever) — first-time seizure requires emergency evaluation. Difficulty breathing: rapid breathing, nasal flaring, chest retractions, grunting. Dehydration signs: no tears when crying, dry mouth, sunken eyes, decreased urination (no wet diaper for 6+ hours in infants), sunken fontanelle in infants. Lethargy or unresponsiveness. Persistent vomiting (unable to keep any fluids down). Bulging fontanelle (in infants). High-pitched cry or unusual irritability. Purple or red rash that does not fade when pressed (glass test). Cold hands and feet with fever. For infants under 3 months, any fever requires immediate medical evaluation.""",
        "language": "en",
        "category": "pediatric",
    },
    {
        "source": "WHO Guidelines",
        "title": "علامات الطوارئ عند الأطفال",
        "content": """الأطفال يحتاجون اهتماماً خاصاً لأن حالتهم قد تتدهور بسرعة. علامات الطوارئ عند الأطفال: حرارة فوق 40 درجة مئوية خاصة عند الرضع أقل من 3 أشهر. تشنجات حرارية — التشنج الأول يتطلب تقييم طارئ. صعوبة في التنفس: تنفس سريع، فتحات أنف متسعة، انكماش الصدر، شخير. علامات الجفاف: عدم وجود دموع عند البكاء، جفاف الفم، عيون غائرة، قلة التبول (لا حفاض مبلل لأكثر من 6 ساعات عند الرضع)، نافوخ غائر عند الرضع. خمول أو عدم استجابة. قيء مستمر (عدم القدرة على الاحتفاظ بأي سوائل). نافوخ منتفخ عند الرضع. بكاء حاد أو انزعاج غير معتاد. طفح جلدي أرجواني أو أحمر لا يختفي عند الضغط عليه. برودة الأيدي والأقدام مع حمى. للرضع أقل من 3 أشهر، أي حمى تتطلب تقييم طبي فوري.""",
        "language": "ar",
        "category": "pediatric",
    },
    # ── PREGNANCY (EN + AR) ──
    {
        "source": "WHO Guidelines",
        "title": "Pregnancy Warning Signs",
        "content": """Pregnancy warning signs requiring urgent medical attention: Vaginal bleeding (any amount). Severe abdominal pain or cramping. Severe headache that does not go away. Vision changes: blurred vision, seeing spots, flashing lights. Sudden swelling of face, hands, or feet. Decreased fetal movement (baby moving less than usual). Regular contractions before 37 weeks (preterm labor). Gush of fluid from vagina (possible rupture of membranes). Fever during pregnancy. Severe nausea and vomiting with inability to keep fluids down. Pain or burning during urination. These symptoms may indicate complications such as miscarriage, ectopic pregnancy, preeclampsia, placental abruption, or preterm labor. All require immediate evaluation by a healthcare provider.""",
        "language": "en",
        "category": "pregnancy",
    },
    {
        "source": "WHO Guidelines",
        "title": "علامات الخطر أثناء الحمل",
        "content": """علامات الخطر أثناء الحمل التي تتطلب رعاية طبية عاجلة: نزيف مهبلي (أي كمية). ألم شديد في البطن أو تقلصات. صداع شديد لا يختفي. تغيرات في الرؤية: عدم وضوح الرؤية، رؤية بقع، أضواء وامضة. تورم مفاجئ في الوجه أو اليدين أو القدمين. قلة حركة الجنين (حركة أقل من المعتاد). انقباضات منتظمة قبل الأسبوع 37 (ولادة مبكرة). تدفق سائل من المهبل (تمزق الأغشية). حمى أثناء الحمل. غثيان وقيء شديد مع عدم القدرة على الاحتفاظ بالسوائل. ألم أو حرقان أثناء التبول. هذه الأعراض قد تشير إلى مضاعفات مثل الإجهاض، الحمل خارج الرحم، تسمم الحمل، انفصال المشيمة، أو الولادة المبكرة. جميعها تتطلب تقييماً فورياً من مقدم رعاية صحية.""",
        "language": "ar",
        "category": "pregnancy",
    },
    # ── MEDICATION (EN + AR) ──
    {
        "source": "WHO Guidelines",
        "title": "Medication Safety",
        "content": """Medication safety principles: Always inform your doctor about all medications you take including prescription, over-the-counter, supplements, and herbal remedies. Dangerous drug interactions: Warfarin and NSAIDs (ibuprofen, naproxen, aspirin) — significantly increases bleeding risk. Warfarin and certain antibiotics — can increase anticoagulant effect. ACE inhibitors (blood pressure medications) and potassium supplements — can cause dangerous potassium levels. Multiple sedating medications — can cause respiratory depression. Grapefruit juice with statins and other medications — can increase drug levels to dangerous amounts. Signs of adverse drug reaction: rash, difficulty breathing, swelling, severe nausea, jaundice, unusual bleeding. Always check with a pharmacist before combining medications. Do not stop prescribed medications without consulting your doctor.""",
        "language": "en",
        "category": "medication",
    },
    {
        "source": "WHO Guidelines",
        "title": "سلامة الأدوية والتداخلات الدوائية",
        "content": """مبادئ سلامة الأدوية: أخبر طبيبك دائماً عن كل الأدوية التي تتناولها بما فيها الوصفات الطبية والأدوية بدون وصفة والمكملات والأعشاب. تداخلات دوائية خطيرة: الوارفارين ومضادات الالتهاب غير الستيرويدية (إيبوبروفين، نابروكسين، أسبرين) — تزيد خطر النزيف بشكل كبير. الوارفارين ومضادات حيوية معينة — قد تزيد التأثير المضاد للتخثر. مثبطات الإنزيم المحول للأنجيوتنسين (أدوية ضغط) ومكملات البوتاسيوم — قد تسبب مستويات بوتاسيوم خطيرة. أدوية مهدئة متعددة معاً — قد تسبب تثبيط تنفسي. عصير الجريب فروت مع الستاتينات وأدوية أخرى — قد يزيد مستويات الدواء لكميات خطيرة. علامات التفاعل الدوائي الضار: طفح جلدي، صعوبة تنفس، تورم، غثيان شديد، يرقان، نزيف غير معتاد. استشر الصيدلي دائماً قبل دمج الأدوية. لا توقف الأدوية الموصوفة بدون استشارة طبيبك.""",
        "language": "ar",
        "category": "medication",
    },
    # ── TRIAGE (EN + AR) ──
    {
        "source": "Manchester Triage Group",
        "title": "Manchester Triage Scale Overview",
        "content": """The Manchester Triage Scale (MTS) is a clinical risk management tool used to prioritize patient care based on clinical urgency. Triage categories: Emergency (Red) — Immediate: life-threatening conditions requiring immediate intervention. Examples: cardiac arrest, severe respiratory distress, active severe bleeding, anaphylaxis, status epilepticus. Very Urgent (Orange) — within 10 minutes: conditions that could become life-threatening. Examples: chest pain of possible cardiac origin, severe difficulty breathing, altered consciousness. Urgent (Yellow) — within 60 minutes: conditions requiring urgent attention but not immediately life-threatening. Examples: moderate shortness of breath, acute severe pain, fever with signs of infection. Standard (Green) — within 120 minutes: stable conditions. Examples: minor injuries, mild symptoms. Non-urgent (Blue) — within 240 minutes: conditions that can safely wait. Examples: minor complaints, follow-up visits. The triage score (0-100) reflects urgency: 90-100 emergency, 70-89 very urgent, 40-69 urgent, 20-39 standard, below 20 non-urgent.""",
        "language": "en",
        "category": "triage",
    },
    {
        "source": "Manchester Triage Group",
        "title": "مقياس مانشستر للفرز الطبي",
        "content": """مقياس مانشستر للفرز الطبي هو أداة إدارة مخاطر سريرية تستخدم لتحديد أولويات رعاية المرضى بناءً على الضرورة السريرية. فئات الفرز: طارئ (أحمر) — فوري: حالات مهددة للحياة تتطلب تدخلاً فورياً. أمثلة: توقف القلب، ضائقة تنفسية شديدة، نزيف حاد نشط، حساسية مفرطة، حالة صرعية. عاجل جداً (برتقالي) — خلال 10 دقائق: حالات قد تصبح مهددة للحياة. أمثلة: ألم صدر ذو منشأ قلبي محتمل، صعوبة تنفس شديدة، تغير في الوعي. عاجل (أصفر) — خلال 60 دقيقة: حالات تتطلب اهتماماً عاجلاً لكنها ليست مهددة للحياة فوراً. أمثلة: ضيق تنفس متوسط، ألم حاد مفاجئ، حمى مع علامات عدوى. قياسي (أخضر) — خلال 120 دقيقة: حالات مستقرة. أمثلة: إصابات طفيفة، أعراض خفيفة. غير عاجل (أزرق) — خلال 240 دقيقة: حالات يمكنها الانتظار بأمان. درجة الفرز (0-100) تعكس الاستعجال: 90-100 طوارئ، 70-89 عاجل جداً، 40-69 عاجل، 20-39 قياسي، أقل من 20 غير عاجل.""",
        "language": "ar",
        "category": "triage",
    },
]


async def build():
    # Load .env
    dotenv_path = _backend_root / ".env"
    if dotenv_path.exists():
        with open(dotenv_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    v = v.strip().strip('"').strip("'")
                    if k not in os.environ:
                        os.environ[k] = v

    os.environ.setdefault("DISABLE_RATE_LIMIT", "true")

    from app.ai.retrieval.chunker import MedicalChunker
    from app.ai.retrieval.embeddings import Embedder
    from app.ai.retrieval.vectorstore import VectorStore
    from app.core.database import get_session

    chunker = MedicalChunker(chunk_size=256, chunk_overlap=64)
    embedder = Embedder()

    total_chunks = 0

    print(f"Processing {len(MEDICAL_KNOWLEDGE)} medical knowledge entries...\n")

    async with get_session() as session:
        store = VectorStore(session)

        for i, entry in enumerate(MEDICAL_KNOWLEDGE, 1):
            chunks = chunker.chunk(entry["content"])
            if not chunks:
                continue

            embeddings = embedder.embed(chunks)
            chunk_indices = list(range(len(chunks)))
            extra_meta = {
                "title": entry["title"],
                "category": entry["category"],
            }

            ids = await store.upsert_chunks(
                contents=chunks,
                embeddings=embeddings,
                source=entry["source"],
                source_url="",
                section_title=entry["title"],
                language=entry["language"],
                extra_meta=extra_meta,
                chunk_indices=chunk_indices,
            )
            added = len(ids)
            total_chunks += added
            print(
                f"  [{i}/{len(MEDICAL_KNOWLEDGE)}] {entry['title'][:50]} ({entry['language']}) → {len(chunks)} chunks, {added} new"
            )

    print(f"\n✅ Done: {total_chunks} chunks stored across {len(MEDICAL_KNOWLEDGE)} documents")
    print(f"   Languages: AR + EN")
    print(
        f"   Categories: cardiac, neurological, respiratory, allergy, trauma, infectious, neurology, abdominal, mental_health, pediatric, pregnancy, medication, triage"
    )


if __name__ == "__main__":
    asyncio.run(build())
