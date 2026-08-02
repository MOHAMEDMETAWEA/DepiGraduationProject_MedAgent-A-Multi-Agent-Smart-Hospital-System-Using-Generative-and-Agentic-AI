# MedAgent — تقرير مشروع DEPI النهائي

## برنامج الابتكار الرقمي المصري (DEPI)
**مسار:** الذكاء الاصطناعي وعلوم البيانات — الجولة الثانية

**الطالب:** حسام حسن
**المشروع:** MedAgent — مساعد فرز طبي ذكي ثنائي اللغة (عربي + إنجليزي)
**تاريخ التقديم:** 6 مايو 2026

---

## 1. ملخص تنفيذي

MedAgent هو مساعد طبي ذكي ثنائي اللغة يعمل بالذكاء الاصطناعي، مبني على بنية وكيل ReAct-style. يستطيع المرضى وصف أعراضهم بالعربية أو الإنجليزية (أو خليط من اللغتين)، ويقوم MedAgent بما يلي:

1. **فرز الحالة (Triage):** تحديد ما إذا كانت الحالة طارئة أو عاجلة أو روتينية
2. **التشخيص التفريقي (Differential Diagnosis):** قائمة بالتشخيصات المحتملة مع درجات ثقة وأدلة داعمة
3. **توصية بالإجراء المناسب:** الذهاب للطوارئ، أو حجز موعد مع طبيب، أو رعاية منزلية
4. **ملخص تسليم للطبيب (Handoff):** مستند PDF منظم يمكن للمريض مشاركته مع الطبيب

النظام مبني على معايير الإنتاج (production-grade) مع:
- خط أنابيب أمان متعدد المراحل (5 مراحل)
- تشفير البيانات الطبية الحساسة (PHI) بتقنية AES-256
- سجل تدقيق مشفر بسلسلة تجزئة (hash-chained audit log)
- دعم كامل للغة العربية (RTL + تدقيق إملائي + لهجة مصرية)
- استرجاع المعرفة الطبية (RAG) من مصادر موثوقة (WHO، MedlinePlus)
- 14 أداة سريرية متخصصة (أدوية، صحة نفسية، أطفال، حمل، تحليل صور)

---

## 2. المشكلة والحل

### 2.1 المشكلة

- **فجوة اللغة العربية في الذكاء الاصطناعي الطبي:** معظم أدوات الفرز الطبي الذكية تخدم المتحدثين بالإنجليزية فقط، مما يترك 400+ مليون متحدث بالعربية بدون خدمة مماثلة
- **ازدحام غرف الطوارئ:** كثير من زيارات الطوارئ يمكن تجنبها لو توفرت أداة فرز أولية موثوقة
- **غياب التوعية الطبية:** المرضى لا يعرفون متى يجب عليهم التوجه للطوارئ ومتى يمكنهم الانتظار
- **الخلط بين اللغات (Code-switching):** شائع جداً في مصر (Franco-Arabic)، ومعظم الأنظمة لا تتعامل معه

### 2.2 الحل

MedAgent يسد هذه الفجوة عبر:
- دعم كامل للغة العربية (بما في ذلك Franco-Arabic)
- خط أنابيب أمان يضمن عدم تقديم تشخيصات خاطئة
- قاعدة معرفة طبية مسترجعة (RAG) تضمن استناد كل معلومة إلى مصدر موثوق
- واجهة مستخدم زجاجية عصرية (Glassmorphic UI) تدعم الوضع الداكن و RTL

---

## 3. التقنيات المستخدمة

### 3.1 الخلفية (Backend)

| التقنية | الإصدار | الغرض |
|---------|---------|-------|
| Python | 3.11+ | لغة البرمجة |
| FastAPI | 0.136+ | إطار API غير متزامن |
| SQLAlchemy 2.0 | async | ORM غير متزامن |
| PostgreSQL + pgvector | 17 | قاعدة بيانات + متجهات |
| Redis | 7 | تخزين مؤقت + تحديد المعدل |
| Alembic | 1.13+ | ترحيل قاعدة البيانات |
| Pydantic | 2.x | التحقق من صحة البيانات |
| python-jose + bcrypt | — | JWT + تشفير كلمات المرور |
| cryptography (Fernet) | 42+ | تشفير AES-256 للبيانات الطبية |
| structlog | 25+ | تسجيل JSON منظم |
| slowapi | 0.1+ | تحديد معدل الطلبات (Redis) |
| aiosmtplib + jinja2 | — | إرسال البريد الإلكتروني |
| weasyprint | 62+ | توليد PDF للتسليم الطبي |
| httpx | 0.27+ | عميل HTTP غير متزامن |

### 3.2 الواجهة الأمامية (Frontend)

| التقنية | الإصدار | الغرض |
|---------|---------|-------|
| Next.js | 16 (App Router) | إطار الواجهة |
| React | 19 | مكتبة واجهة المستخدم |
| TypeScript | 5.x (strict) | لغة البرمجة |
| Tailwind CSS | 4 | إطار التنسيق |
| shadcn/ui | 4.6 | مكتبة المكونات |
| next-intl | 4.11 | التدويل (عربي/إنجليزي) |
| zustand | 5 | إدارة الحالة |
| react-hook-form + zod | — | إدارة النماذج |
| framer-motion | 12 | الرسوم المتحركة |

### 3.3 الذكاء الاصطناعي والتعلم الآلي

| التقنية | الغرض |
|---------|-------|
| Qwen2.5-7B-Instruct | النموذج اللغوي الأساسي (يدعم العربية بقوة) |
| multilingual-e5-large | نموذج التضمين (1024 بعد) |
| bge-reranker-v2-m3 | إعادة ترتيب النتائج |
| pgvector (IVF-Flat) | مخزن المتجهات |
| LoRA / QLoRA | ضبط دقيق (fine-tuning) |
| MLflow | تتبع التجارب |
| Sentence-Transformers | تضمين النصوص |

---

## 4. معمارية النظام

### 4.1 هيكل المشروع

```
MedAgent/
├── backend/                     # تطبيق FastAPI
│   ├── app/
│   │   ├── main.py              # نقطة الدخول + تسجيل المسارات
│   │   ├── core/                # البنية التحتية (config, security, db, crypto)
│   │   ├── modules/             # وحدات النطاق (auth, chat, admin, handoff, ...)
│   │   ├── ai/                  # وكيل الذكاء الاصطناعي
│   │   │   ├── agent/           # ReAct loop + tool registry + system prompts
│   │   │   ├── llm/             # مزودي النماذج اللغوية
│   │   │   ├── retrieval/       # RAG (تضمين + مخزن متجهات + إعادة ترتيب)
│   │   │   ├── tools/           # 14 أداة سريرية متخصصة
│   │   │   ├── safety/          # خط أنابيب الأمان متعدد المراحل
│   │   │   └── nlp/             # اكتشاف اللغة + تدقيق عربي + إخفاء PII
│   │   ├── models/              # نماذج SQLAlchemy (15 جدول)
│   │   └── common/              # أدوات مشتركة (PDF, pagination, audit)
│   ├── tests/                   # اختبارات pytest (شفرة + تكامل)
│   └── alembic/                 # ترحيل قاعدة البيانات
├── frontend/                    # تطبيق Next.js
│   ├── app/[locale]/            # صفحات متعددة اللغات
│   ├── components/              # مكونات React (auth, chat, admin, ...)
│   ├── lib/api/                 # طبقة API client
│   ├── store/                   # Zustand stores
│   └── messages/                # ملفات الترجمة (ar.json, en.json)
├── docs/                        # التوثيق
├── docker-compose.yml           # حاويات التطوير
└── plan.md                      # خطة المشروع الرئيسية
```

### 4.2 طبقات النظام

| الطبقة | المسؤولية |
|--------|----------|
| **HTTP (routers)** | استقبال الطلبات، التحقق من الصحة، تنسيق الردود |
| **Service** | منطق الأعمال، تنسيق repositories + agent |
| **Agent** | تنظيم LLM، استدعاء الأدوات، RAG، حواجز الأمان |
| **Data** | استعلامات قاعدة البيانات، المعاملات |
| **Frontend** | واجهة المستخدم، التحديثات المتفائلة، التحقق |

### 4.3 معمارية الوكيل (Agent Architecture)

```
إدخال المستخدم
    ↓
[Stage 1] تدقيق Pre-LLM:
    - اكتشاف اللغة
    - تدقيق عربي
    - إخفاء المعلومات الشخصية (PII)
    - كشف الطوارئ (Red Flags) ← مسار سريع
    ↓ (إذا لم تكن حالة طارئة)
[Stage 2] حلقة ReAct (أقصى 5 تكرارات):
    - LLM يقرر: إجابة نهائية أم استدعاء أداة؟
    - تنفيذ الأداة ← إضافة النتيجة للسياق
    ↓
[Stage 3] بوابة أمان Post-LLM:
    - كشف الهلاوس (مقارنة بالمصادر)
    - إعادة صياغة العبارات المحظورة
    - معايرة عدم اليقين
    - التحقق من اتساق التصنيف
    ↓
[Stage 4] سجل تدقيق مشفر:
    - تسجيل كل عملية بسلسلة تجزئة
```

### 4.4 الأدوات السريرية (14 أداة)

| الأداة | الغرض |
|--------|-------|
| `retrieve_medical_knowledge` | استرجاع المعرفة الطبية من قاعدة المعرفة |
| `score_triage` | تصنيف الحالة (مقياس مانشستر) |
| `detect_red_flags` | كشف أعراض الطوارئ |
| `summarize_for_doctor` | ملخص منظم للطبيب |
| `format_soap` | تنسيق SOAP note |
| `tot_differential_diagnosis` | تشخيص تفريقي (Tree-of-Thought) |
| `analyze_vision` | تحليل أولي للصور الطبية |
| `verify_no_hallucination` | كشف الادعاءات غير المدعومة |
| `calibrate_uncertainty` | معايرة مستوى الثقة |
| `check_medication_interactions` | فحص تفاعلات الأدوية |
| `screen_mental_health` | فحص الصحة النفسية (PHQ-9/GAD-7) |
| `assess_pediatric_safety` | بوابة أمان للأطفال (< 18 سنة) |
| `assess_pregnancy_safety` | بوابة أمان للحوامل |

### 4.5 خط أنابيب الأمان (5 مراحل)

1. **Pre-LLM Red-Flag Fast Path:** كلمات الطوارئ بالعربية والإنجليزية تتجاوز النموذج بالكامل
2. **System Prompt Enforcement:** لا تشخيص نهائي، لا وصفات طبية، دائماً استشهد بالمصادر
3. **Post-LLM Hallucination Detector:** كل ادعاء طبي يقارن بالمصادر المسترجعة
4. **Uncertainty Calibration:** الادعاءات منخفضة الثقة تُعلم للمستخدم
5. **Hash-Chained Audit Log:** كل عملية مرقمة تسلسلياً ومرتبطة بتجزئة — التلاعب قابل للكشف

### 4.6 قاعدة البيانات (15 جدول)

- `users` — المستخدمين (مريض، طبيب، مسؤول)
- `patient_profiles` — ملفات المرضى الموسعة
- `doctor_profiles` — ترخيص، تخصص، حالة الموافقة
- `auth_tokens` — رموز التحقق وإعادة التعيين
- `refresh_tokens` — رموز التحديث (استخدام واحد)
- `conversations` — جلسات المحادثة + حالة التصنيف
- `messages` — الرسائل (مع تشفير اختياري)
- `handoff_summaries` — ملخصات التسليم للطبيب
- `handoff_exports` — صادرات FHIR R4 / HL7 v2 / PDF
- `safety_assessments` — تقييمات الأمان لكل رسالة
- `vision_analyses` — تحليلات الصور الطبية
- `medication_records` — سجلات الأدوية
- `kb_chunks` — أجزاء قاعدة المعرفة (مع متجهات pgvector)
- `audit_logs` — سجل التدقيق المشفر
- `support_tickets` — تذاكر الدعم
- `notification_log` — سجل الإشعارات

---

## 5. واجهة المستخدم

### 5.1 الصفحات والمسارات

| المسار | الصفحة | الوصف |
|--------|--------|-------|
| `/` | الرئيسية | صفحة هبوط تسويقية |
| `/login` | تسجيل الدخول | نموذج دخول |
| `/register` | إنشاء حساب | تسجيل كمريض أو طبيب |
| `/forgot-password` | نسيت كلمة المرور | استعادة كلمة المرور |
| `/chat` | محادثة جديدة | بدء فرز طبي |
| `/chat/[id]` | محادثة قائمة | استكمال محادثة |
| `/history` | السجل | قائمة المحادثات السابقة |
| `/profile` | الملف الشخصي | تحديث البيانات |
| `/admin/dashboard` | لوحة التحكم | إحصائيات المنصة |
| `/admin/users` | إدارة المستخدمين | قائمة + تفعيل/تعطيل |
| `/admin/doctors` | إدارة الأطباء | موافقة/رفض |
| `/admin/audit` | سجل التدقيق | سجل العمليات |
| `/admin/safety` | إحصائيات الأمان | معدلات الهلاوس |
| `/doctor/inbox` | صندوق الطبيب | التسليمات المستلمة |
| `/doctor/handoff` | ملخص التسليم | عرض ملخص المريض |
| `/support/faq` | الأسئلة الشائعة | FAQ |
| `/support/contact` | اتصل بنا | نموذج اتصال |

### 5.2 التصميم (Glassmorphic + Liquid Glass)

- **النمط:** زجاجي (Glassmorphism) مع حركات سائلة خفيفة
- **الألوان:** أزرق طبي موثوق + ألوان دلالية (أحمر للطوارئ، برتقالي للعاجل، أخضر للروتيني)
- **الوضع الداكن:** مدعوم كلياً عبر next-themes
- **الخطوط:** Manrope للعناوين، Inter (إنجليزي) / Cairo (عربي) للنصوص
- **RTL:** دعم كامل للغة العربية مع اتجاه من اليمين لليسار
- **الحركة:** Framer Motion مع احترام `prefers-reduced-motion`

---

## 6. ميزات متقدمة

### 6.1 دعم Franco-Arabic

يستطيع النظام فهم Franco-Arabic (العربية مكتوبة بحروف لاتينية وأرقام):
- `7` ← ح (7abiby = حبيبي)
- `3` ← ع (3yoon = عيون)
- `2` ← ء (so2al = سؤال)

### 6.2 الفروع المتخصصة

- **فرع الأطفال (Pediatric):** يتفعل تلقائياً عند عمر < 18 سنة، مع فحوصات جرعات مناسبة للعمر
- **فرع الحمل (Pregnancy):** يتفعل تلقائياً عند وجود حمل، مع فحوصات OB وتحذيرات فئة الحمل

### 6.3 Tree-of-Thought (ToT)

للتشخيص التفريقي المعقد، يتحول الوكيل إلى وضع Tree-of-Thought:
1. توليد 3 فرضيات تشخيصية
2. استرجاع الأدلة لكل فرضية
3. تقييم وترتيب الفرضيات
4. عرض التشخيص التفريقي مع درجات الثقة

### 6.4 توافقية طبية (Interoperability)

- **FHIR R4 Bundle JSON:** تصدير بصيغة FHIR القياسية
- **HL7 v2.5:** تصدير بصيغة HL7 التقليدية
- **PDF:** مستند PDF منسق يمكن طباعته أو مشاركته

### 6.5 تشفير البيانات الطبية (PHI Encryption)

- خوارزمية AES-256-CBC + HMAC-SHA256 (Fernet)
- تشفير على مستوى التطبيق قبل التخزين في قاعدة البيانات
- الحقول المشفرة: محتوى الرسائل، تحليلات الصور، ملفات المرضى، ملخصات التسليم
- في الإنتاج: فشل فوري إذا كان المفتاح غير موجود

### 6.6 سجل تدقيق مشفر (Hash-Chained Audit)

- كل عملية ترقيم تسلسلياً (BIGSERIAL)
- كل سجل مرتبط بالسجل السابق عبر SHA-256
- أي تلاعب بالسجلات قابل للكشف فوراً
- إمكانية التحقق عبر `/admin/audit-verify`

---

## 7. الاختبارات

### 7.1 اختبارات الخلفية (Backend)

- إطار: pytest + pytest-asyncio + pytest-cov
- 11 ملف اختبار رئيسي + مجلدات اختبار متخصصة
- تغطية تشمل: core, models, security, deps, users, audit, rate_limit, tools, RAG, chunker, vision, branches
- اختبارات مصادقة شاملة: register, login, token, password
- بيانات تقييم (eval data): vision, hallucination, specialized tools

### 7.2 اختبارات الواجهة (Frontend)

- Playwright لاختبارات E2E (4 تدفقات رئيسية)
- Vitest لاختبارات الوحدة
- MSW لمحاكاة API
- Testing Library لاختبارات المكونات

---

## 8. النشر والتشغيل

### 8.1 بيئة التطوير

```bash
# تشغيل جميع الخدمات
make up

# أو بشكل منفصل
docker compose up postgres redis mailpit -d  # بنية تحتية
cd backend && uv run uvicorn app.main:app --reload  # خلفية
cd frontend && pnpm dev  # واجهة أمامية
```

### 8.2 النشر الإنتاجي

| المكون | المنصة |
|--------|--------|
| الواجهة الأمامية | Vercel |
| الخلفية | Railway / Render |
| قاعدة البيانات | Neon / Supabase |
| النموذج اللغوي | OpenRouter API |
| المراقبة | Sentry + Prometheus |

---

## 9. التحديات والحلول

| التحدي | الحل |
|--------|------|
| دعم Franco-Arabic | كاشف لغة مخصص مع قاموس Franco→Arabic |
| منع الهلاوس الطبية | خط أنابيب أمان من 5 مراحل + نموذج مدقق منفصل |
| أمان بيانات المرضى | تشفير AES-256 على مستوى التطبيق |
| قابلية التدقيق | سجل تدقيق مشفر بسلسلة تجزئة |
| تعدد اللغات + RTL | next-intl مع دعم كامل للغة العربية |
| أداء استرجاع المعرفة | pgvector + bge-reranker لإعادة الترتيب |
| استجابة الطوارئ الفورية | مسار سريع يتجاوز LLM بالكامل |

---

## 10. الدروس المستفادة

1. **الأمان أولاً في المجال الطبي:** خط أنابيب الأمان متعدد المراحل ليس "ميزة إضافية" بل ضرورة مطلقة
2. **اللغة العربية تحدٍ حقيقي:** Franco-Arabic واللهجات المختلفة تتطلب معالجة لغوية متخصصة
3. **بنية الوكيل (Agent) أقوى من الشات بوت التقليدي:** ReAct loop مع الأدوات يعطي نتائج أكثر دقة وموثوقية
4. **التدقيق (Audit) أساسي للثقة:** chain of custody عبر hash chain يجعل النظام قابلاً للتدقيق الكامل
5. **الفصل بين الطبقات يسهل التطوير:** الفصل الصارم بين HTTP/Service/Agent/Data جعل المشروع قابلاً للتوسع

---

## 11. العمل المستقبلي

- [ ] تطبيق جوال (React Native)
- [ ] دعم DICOM كامل لعرض الصور الإشعاعية
- [ ] تكامل مع أنظمة السجلات الطبية الإلكترونية (EHR)
- [ ] نموذج Arabic-first مدرب من الصفر (بدلاً من الاعتماد على نماذج متعددة اللغات)
- [ ] اعتماد HIPAA / GDPR
- [ ] نظام حجز مواعيد متكامل
- [ ] دعم لغات إضافية (فرنسي، أوردو)
- [ ] تحسين النموذج عبر RLHF من تفاعلات حقيقية (بموافقة المستخدمين)
- [ ] واجهة صوتية (Speech-to-Text + Text-to-Speech)

---

## 12. المراجع

- **OpenAI Compatible API pattern** — استخدمت لتوحيد التواصل مع مزودي LLM المختلفين
- **ReAct: Synergizing Reasoning and Acting in Language Models** (Yao et al., 2023)
- **Tree of Thoughts: Deliberate Problem Solving with Large Language Models** (Yao et al., 2023)
- **Manchester Triage System** — أساس أداة `score_triage`
- **PHQ-9 / GAD-7** — مقاييس موحدة للصحة النفسية
- **WHO Clinical Guidelines** — مصدر رئيسي لقاعدة المعرفة
- **HL7 FHIR R4** — معيار التوافقية الطبية
- **OWASP Top 10 for LLM Applications** — مرجع لنموذج التهديدات الأمنية

---

## 13. تحديثات النسخة النهائية (Phase 6 — Clinical KB Engine)

> آخر تحديث: 2026-05-24
>
> هذا القسم يوثّق الإضافات الجوهرية اللي اتعملت بعد التسليم الأولي للتقرير، واللي حوّلت النظام من "AI triage assistant" إلى **Clinically-grounded RAG product** جاهز للـ pilot في عيادات حقيقية.

### 13.1 محرك المعرفة السريرية (Clinical KB)

#### الفكرة
الـ LLMs العامة (Llama, GPT, Gemini) ميصلحوش لوصف أدوية مباشرةً للمريض — لأنها بتهلوس جرعات وبتستهلك القاعدة الأساسية بـ "روح للدكتور". الحل: **هيكل بيانات منفصل عن الـ LLM** يحتوي على المحتوى السريري المنسّق، والـ LLM بيقتبس منه فقط.

#### البنية (`backend/app/clinical/`)

```
clinical/
├── schemas.py                    # Pydantic models (the contract)
├── kb.py                         # Singleton loader مع lru_cache
├── chief_complaints/             # ١٠ ملفات YAML
│   ├── chest_pain.yaml           # NICE CKS + AHA/ACC 2021
│   ├── fever.yaml                # NICE + WHO IMCI
│   ├── headache.yaml             # NICE NG150
│   ├── cough.yaml                # NICE CKS
│   ├── abdominal_pain.yaml       # NICE CKS
│   ├── back_pain.yaml            # NICE NG59
│   ├── diarrhea.yaml             # WHO + NICE
│   ├── sore_throat.yaml          # NICE NG84
│   ├── skin_rash.yaml            # NICE Urticaria
│   └── fatigue.yaml              # NICE CKS
├── formulary/
│   └── drugs.yaml                # ١٠ أدوية بأسماء تجارية مصرية + dosing
└── specialties/                  # ٣ قوالب intake
    ├── general_practice.yaml
    ├── pediatrics.yaml
    └── ent.yaml
```

#### كل chief complaint يحتوي على

| الحقل | المعنى |
|---|---|
| `synonyms` | كلمات مفتاحية بالعربي والإنجليزي + لهجة مصرية (مثلًا "حجر على صدري" لـ chest pain) |
| `red_flags[]` | أسئلة كشف العلامات الخطرة مع `severity` و `rationale` |
| `differentials[]` | احتمالات تشخيصية مع `likelihood` (very_common/common/uncommon/rare/emergency) |
| `followup_questions[]` | أسئلة استكشافية إضافية حسب الحاجة |
| `self_care[]` | علاج OTC مع `drug_id` يربط بالـ formulary |
| `workup[]` | الفحوصات الموصى بها مع `priority` (routine/urgent/emergent) |
| `when_to_escalate[]` | علامات تستدعي تصعيد فوري |
| `sources[]` | روابط NICE / WHO / BMJ |
| `needs_clinical_review` | flag يظهر في الـ CI لتذكير الفريق إن المحتوى يحتاج توقيع طبيب |

#### مثال: drug formulary entry

```yaml
- id: ibuprofen
  generic_name: { ar: إيبوبروفين, en: Ibuprofen }
  brand_names_eg: [Brufen, Ibufen, Profinal, Megafen]
  pregnancy_category: C
  pediatric_min_age_years: 0.5

  dosing:
    - min_age_years: 12
      dose: "400 mg PO every 6-8 h with food"
      max_daily: "1200 mg/day OTC"
    - min_age_years: 0.5
      max_age_years: 12
      weight_based: true       # ← يجبر الـ LLM يسأل عن الوزن
      dose: "5-10 mg/kg PO every 6-8 h"
      max_daily: "30 mg/kg/day (max 1200 mg)"

  contraindications:
    - { ar: قرحة معدية نشطة, en: Active peptic ulcer }
    - { ar: نزف معدي مشتبه, en: Suspected GI bleed }
    - { ar: فشل كلوي (eGFR <30), en: Renal failure (eGFR <30) }
    - { ar: حمل (ثلث ثالث), en: Pregnancy (3rd trimester) }
    - { ar: شك في acute abdomen (يخفي علامات الزائدة), en: Suspected acute abdomen }
```

#### أداة `clinical_lookup` الجديدة

اتضافت كأداة رقم ١٤ في الـ tool registry. الـ agent بيستدعيها قبل كل رد للمريض، والنتيجة بتتحقن في الـ messages history كأنها استدعاء أداة طبيعي. هذا يجعل الـ LLM **مضطرًا** ينسخ منها بدل ما يهلوس.

تفاصيل كاملة في [`docs/CLINICAL_KB.md`](CLINICAL_KB.md).

### 13.2 الـ Workflow ثلاثي المراحل (Intake → Differential → Plan)

#### المشكلة قبل التعديل
الـ LLM كان بيتسرع: يجاوب على "عندي صداع" بـ paracetamol 1000 مج في أول رد، **بدون معرفة** الأدوية الحالية أو الحساسية أو الأمراض المزمنة. ده خطر سريري حقيقي (warfarin + NSAIDs = نزيف، حمل + بروفين = خطر).

#### الحل
نظّمت الـ system prompt إجباريًا في **٣ مراحل** بقواعد صلبة (Hard Rules):

**المرحلة A — التشخيص الأولي + الاستقصاء** (الرد الأول)
1. سطر تعاطف يعكس كلام المريض
2. عرض ٢-٣ احتمالات تشخيصية أوّلية (🟢🟡🔴)
3. أسئلة intake إجبارية: الأدوية الحالية + الحساسية + الأمراض المزمنة + الحمل + ١-٢ سؤال سريري محدد

🚫 **ممنوع نهائيًا** في المرحلة A:
- اسم أي دواء
- جرعة (500 مج / mg)
- تشخيص قطعي
- خطة علاج كاملة

**المرحلة B — التشخيص التفريقي المُحدّث** (بعد ما يجاوب)
- تأكيد/تنقيح الـ differential بناءً على إجاباته

**المرحلة C — الخطة + Safety check**
- اقتراح دواء من `self_care[]` فقط (مش من ذاكرة الـ LLM)
- التحقق من `contraindications` ضد أدويته + أمراضه + حساسيته + الحمل
- لو فيه تعارض → اختيار بديل آمن

#### التحقق الذاتي (Self-check) قبل الإرسال

٠١ سؤال إجباري يتحقق منهم الـ LLM قبل ما يبعت الرد، مقسّمين على:
- **Drug-safety** (٣ أسئلة)
- **Patient-respect** (٣ أسئلة — اقرأ رسالة المريض، ما تسألش عن حاجة قالها)
- **Clinical-accuracy** (٤ أسئلة)

**القاعدة الذهبية:** "لو في شك، اسأل بدل ما تكتب وصفة."

### 13.3 Emergency Playbook (دعم الأزمات النفسية)

كان فيه bug خطير: الـ agent كان يـ short-circuit في حالات الطوارئ ويرد بـ badge أحمر فقط بدون أي محتوى نصي. مريض بأفكار انتحارية كان بيخرج بـ 0 tokens of help.

#### الحل: Emergency Fast-Path
لما `detect_red_flags` يرجع `severity: emergency`:
1. يـ emit الـ badge events للـ UI
2. يبدّل system prompt كاملًا لـ "Emergency Mode" مختصر وموجّه
3. يستدعي LLM **بدون tools** عشان يولّد رد مباشر متعاطف

#### بنية الرد الإجبارية (٥ عناصر)

```
١. سطر تعاطف قصير ("أنا فاهم، خليني معاك دلوقتي")
٢. رقم الخط الساخن المناسب:
   - 🚑 ١٢٣ إسعاف مصر / ٩١١ دوليًا
   - 🧠 ١٦٣٢٨ خط نجدة نفسية مصر / ٩٨٨ أمريكا / ١١٦ ١٢٣ أوروبا
   - ☎️ ١٥٩ تسمم مصر
٣. خطوة إسعاف أولي محددة (مضغ aspirin / EpiPen / استلقاء على الجنب)
٤. ايه يقول للمسعف
٥. متى يطلب إسعاف بدل ما يروح بنفسه
```

### 13.4 Vision Multi-Compare

نظام جديد يتيح للمستخدم تحليل نفس الصورة بـ **٤ مزودي رؤية** متوازي والمقارنة:

| المزوّد | الموديل | الميزة |
|---|---|---|
| **Groq** | Llama-4 Scout (multimodal) | مجاني، سريع جدًا |
| **OpenAI** | GPT-4o | أعلى دقة في الطب |
| **Google** | Gemini 2.5 Flash | مجاني، عربي ممتاز |
| **OpenRouter** | Llama 3.2 Vision Free | بديل مجاني |

UI: Dropdown متعدد الاختيار في الـ chat composer. الـ frontend بيـ fan-out N parallel requests كل واحد بـ `vision_provider` و `vision_model` مختلف. كل النتائج تظهر كـ `VisionResultCard` منفصل مع label لاسم الموديل.

### 13.5 محسّنات DevOps + النشر

#### Cloudflare Tunnel للـ team testing
- `proxy.ts` (renamed من `middleware.ts` لـ Next.js 16) مع forwarded-host post-processor يصلّح bug "redirect إلى :3000" خلف الـ proxy
- `next.config.ts` فيه `allowedDevOrigins: ["*.trycloudflare.com", "*.ngrok.io", ...]` عشان dev-mode HMR ميتـ block بسبب CORS
- شرح كامل للـ team-sharing flow في README

#### تحسينات Schema validation
- `clinical_lookup.age_years` بقت تقبل `int | str | None` (مش `int | None` فقط) عشان Groq's strict validator ميرفضش الـ call لو الـ LLM بعت `"null"` كـ string
- `field_validator(mode="before")` يحوّل أي شكل (`"42"`, `"unknown"`, `7.3`) لـ `int | None` نظيف
- نفس المعالجة طُبّقت على الـ synthesized `analyze_vision` tool call لتمرير `image_url` placeholder

#### Markdown rendering في الـ chat
- assistant messages دلوقتي تمر على `<Markdown>` component (ReactMarkdown + remark-gfm)
- patient messages تفضل plain text
- النتيجة: `### العناوين`، **bold**، lists، و emojis تظهر بشكل احترافي بدل raw `###`

### 13.6 إحصائيات النسخة الحالية

| المقياس | القيمة |
|---|---|
| ملفات Python | 115 |
| صفحات Next.js | 19 |
| AI tools registered | 14 |
| Chief complaints (KB) | 10 |
| Drugs (formulary) | 10+ |
| Specialty intake templates | 3 |
| Backend tests | 305 (≥75% coverage) |
| Frontend E2E specs | 12+ |
| جداول قاعدة البيانات | 15 |
| لغات مدعومة | Arabic (MSA + Egyptian) + English |

### 13.7 الخطوات التالية (Roadmap قصير المدى)

| الأولوية | البند |
|---|---|
| 🔴 | توقيع طبيب معتمد على الـ ١٠ chief complaints (إزالة flag `needs_clinical_review`) |
| 🔴 | إضافة complaints جديدة: hyperglycemia, hypoglycemia, dyspepsia, UTI, dizziness |
| 🟠 | Pre-visit intake mode UI (B2B للعيادات) — backend موجود، UI لم يكتمل |
| 🟠 | Pilot في عيادة واحدة + جمع feedback من ٢٠ مريض حقيقي |
| 🟡 | Clinical validation study — مقارنة triage الـ AI ضد junior physician على ٥٠ حالة |
| 🟡 | Mental-health protocols (depression, anxiety, panic attack) مع PHQ-9 / GAD-7 |

---

## 14. الخاتمة

MedAgent هو مشروع متكامل **production-grade** يدمج بين:

- **هندسة برمجيات حديثة:** FastAPI + Next.js 16 + PostgreSQL + Docker — مع 305 backend tests + 12 Playwright e2e
- **ذكاء اصطناعي متقدم:** ReAct Agent + RAG + 14 أداة سريرية + Multi-vision compare + clinical_lookup الجديدة
- **محتوى سريري منسّق:** 10 chief complaints + Egyptian drug formulary + 3 specialty templates، مبنيين على NICE CKS و WHO IMCI
- **Workflow احترافي:** 3-phase intake → differential → plan مع Hard Rules ضد التسرّع
- **أمان متعدد الطبقات:** تشفير PHI + تدقيق مشفر + كشف هلاوس + 5 أرقام طوارئ
- **دعم كامل للعربية:** RTL + Franco-Arabic + لهجة مصرية + brand names محلية

**المشروع جاهز:**
- ✅ للنشر التجريبي على عيادة pilot (Path 1: triage hotline replacement)
- ✅ للتطوير المستقبلي من خلال نقاط التوسع المحددة (Tool Registry, LLM Provider, KB YAML extension)
- 🟡 لـ enterprise sale بعد الحصول على clinical sign-off + validation study

---

**المشروع مفتوح المصدر:** [github.com/hossam7asan/MedAgent](https://github.com/hossam7asan/MedAgent)
**الرخصة:** MIT © 2026 حسام حسن

**روابط مهمة:**
- 📘 [docs/INDEX.md](INDEX.md) — guided navigation لكل الـ documentation
- 📖 [docs/CLINICAL_KB.md](CLINICAL_KB.md) — تفاصيل الـ KB schema + إزاي تضيف complaint
- 🏛 [docs/architecture.md](architecture.md) — تصميم النظام التفصيلي
- 🤖 [docs/ai-pipeline.md](ai-pipeline.md) — تفاصيل الـ ReAct loop والأدوات
- 🛡 [docs/safety.md](safety.md) — نموذج الأمان السريري الكامل
