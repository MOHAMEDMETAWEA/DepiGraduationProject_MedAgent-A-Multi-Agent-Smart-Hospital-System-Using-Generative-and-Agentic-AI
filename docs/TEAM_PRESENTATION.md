# MedAgent — توزيع الأدوار وملف المناقشة

> **للفريق:** اقرأ ده قبل المناقشة بشوية. كل واحد فيه يعرف قسمه بالظبط، يحفظ النقاط الرئيسية، ويبقى جاهز للأسئلة المحتملة.

---

## 👥 الفريق

| الاسم | الدور | المسؤوليات الأساسية |
|---|---|---|
| 👨‍💼 **حسام** | Lead Architect + Clinical Product | Architecture، Clinical KB، Prompts، Vision Compare، Deployment |
| 👨‍💻 **أحمد** | Frontend Foundations | Landing Page، Design System، Reusable Components |
| 🧪 **محمود** | QA + Tools Integration | Vision testing، Manual UI testing، View/Download features، Screenshots، Bug fixes |
| 📘 **محمد** | Research + Initial Vision | Plan المبدئي، فكرة المشروع، Research، Documentation الأولية |

---

# 1. 👨‍💼 حسام — Lead Architect

## النقاط اللي تقولها (الـ Pitch بتاعك)

> *"أنا مسؤول عن البنية المعمارية الشاملة (Architecture)، وبنيت ٤ ميزات رئيسية على المشروع:*
> *1. محرك المعرفة السريرية (Clinical KB) — نظام يخلي الـ AI يقتبس من بروتوكولات NICE/WHO بدل ما يهلوس.*
> *2. هندسة الـ prompts (v2/v3) — workflow ثلاثي المراحل، Hard Rules، Emergency Playbook بـ ٥ أرقام طوارئ.*
> *3. Vision multi-compare — مقارنة ٤ مزودي رؤية على نفس الصورة (Gemini, GPT-4o, Llama-4, Qwen-VL).*
> *4. الـ DevOps — Cloudflare Tunnel للـ team testing، production Dockerfiles، CI gate."*

## مساهماتك بالتفصيل

### 1.1 Architecture & Plan
- صمّمت الـ system layers (Backend + Frontend + AI + DB + Safety)
- وضعت [plan.md](../plan.md) و [docs/architecture.md](architecture.md)
- اخترت الـ tech stack (FastAPI + Next.js 16 + PostgreSQL + Docker)

### 1.2 Clinical Knowledge Base
- بنيت `backend/app/clinical/` كاملًا
- كتبت `schemas.py` — pydantic models للـ KB validation
- ألّفت ١٠ chief complaints بـ YAML (مع citations من NICE CKS/WHO)
- بنيت Egyptian Drug Formulary (paracetamol، ibuprofen، omeprazole، …) بـ brand names + weight-based dosing
- بنيت ٣ specialty intake templates (GP، Pediatrics، ENT)
- بنيت `clinical_lookup` — الأداة رقم ١٤ في الـ tool registry

### 1.3 Prompt Engineering v2/v3
- أعدت كتابة `system_ar.txt` و `system_en.txt` بالكامل
- **Workflow ثلاثي المراحل:** Intake → Differential → Plan
- **Hard Rules:** ممنوع أدوية في الرد الأول، اقرأ رسالة المريض، ممنوع راو tool output
- **Self-check** — ١٠ أسئلة قبل الإرسال
- **Emergency Playbook** — ٥ عناصر مع أرقام (١٢٣، ١٦٣٢٨، ٩٨٨، ١٥٩)

### 1.4 Vision Multi-Compare
- ضفت `vision_provider` و `vision_model` في `ChatRequest`
- بنيت `VisionModelSelector` (multi-select) في الـ frontend
- وصّلت الـ frontend بالـ backend بحيث الـ request الواحد يفنّش لـ N parallel requests
- النتائج بتظهر كـ `VisionResultCard` منفصلة مع label لكل موديل

### 1.5 DevOps
- Cloudflare Tunnel support (`proxy.ts` + `allowedDevOrigins`)
- Production Dockerfiles (backend + frontend)
- `docker-compose.prod.yml`
- Sentry integration (مع PHI scrubber)
- Grafana dashboard JSON

## الأسئلة المحتملة + أجوبتك

**Q: ايه الفرق بين الـ workflow بتاعك والـ AI chatbot العادي؟**
> *"الـ chatbot العادي بيرد من حفظ الموديل — اللي بيهلوس جرعات. عندنا الـ workflow بيمر بـ ٣ مراحل إجبارية: الـ AI يجمع info → يعرض differential → يدّي خطة بعد فحص الـ contraindications. كمان عندنا KB من NICE/WHO الـ LLM ملزم يقتبس منها بدل ما يخترع."*

**Q: ليه عملت الـ Hard Rules ضد ذكر الأدوية في الرد الأول؟**
> *"عشان الـ patient safety. لو وصفت paracetamol لمريض بياخد warfarin ممكن يحصل نزف. لو وصفت ibuprofen لحامل في الشهر التاني ممكن يضر الجنين. الـ AI لازم يعرف الـ context الكامل قبل أي توصية دوائية."*

**Q: ليه عملت Vision Multi-Compare؟**
> *"عشان نقدر نقيس أحسن مزود رؤية للحالة. مش كل موديل بيشتغل كويس على كل صورة — Gemini أحسن في الـ medical imaging، Llama-4 أسرع، GPT-4o أعلى دقة. الـ UI بيخلي الطبيب يقارن ويختار."*

---

# 2. 👨‍💻 أحمد — Frontend Foundations

## النقاط اللي تقولها

> *"أنا بنيت أساس الـ frontend اللي البقية بنوا عليه. عملت Landing Page كامل، صممت الـ design system (الألوان، الـ glassmorphic effects، الـ RTL support)، وعملت الـ reusable components اللي بنستخدمها في كل الصفحات (Buttons, Cards, Inputs, Modals)."*

## مساهماتك بالتفصيل

### 2.1 Landing Page
- `frontend/app/[locale]/page.tsx`
- مكوّنات الـ landing: `LandingNav`, `Hero`, `SocialProof`, `HowItWorks`, `TriageLevels`, `FeatureGrid`, `SafetySection`, `FinalCta`, `LandingFooter`
- موجودين في `frontend/components/landing/`

### 2.2 Design System
- ألوان الـ project (primary، emergency، urgent، routine)
- Tailwind v4 configuration
- Glassmorphic + Liquid Glass styling
- RTL support للعربي
- Dark mode toggle

### 2.3 Reusable Components
- `frontend/components/ui/` — Button, Card, Input, Modal, Toast, Dialog
- شغل على shadcn/ui pattern
- بيستخدمها كل الصفحات (Chat, Admin, Doctor inbox)

### 2.4 Navigation + Layout
- Sidebar layout
- Locale switcher
- Theme provider

## الأسئلة المحتملة + أجوبتك

**Q: ليه اخترت Next.js 16 App Router؟**
> *"عشان نحتاج SSR للـ SEO على الـ landing page، RSC للـ performance، وlocale routing لدعم العربي والإنجليزي. الـ App Router بيدّيلنا كل ده مع server components للـ data fetching."*

**Q: ليه استخدمت Tailwind v4 + shadcn/ui؟**
> *"Tailwind بيدّينا control كامل على الـ styling بدون CSS files. shadcn/ui مش library بل copy-paste components فنقدر نعدّل في أي حاجة. وده اللي خلانا نعمل glassmorphic style مخصص للمشروع الطبي."*

**Q: إزاي عملت دعم العربي + RTL؟**
> *"استخدمت next-intl للترجمة، و الـ HTML بيتغير `dir="rtl"` تلقائي بناءً على اللغة. كل الـ Tailwind utilities زي `me-`, `ms-`, `start-`, `end-` بدل `mr-`, `ml-`, `left-`, `right-` عشان تشتغل في الاتجاهين."*

---

# 3. 🧪 محمود — QA + Tools Integration

## النقاط اللي تقولها

> *"دوري كان أتأكد إن كل الأدوات شغّالة فعلًا، مش بس في الكود. عملت اختبار يدوي كامل لكل الـ scenarios الطبية، اكتشفت bugs وتم إصلاحها، اشتغلت على ميزة الـ Vision (تحليل الصور) من أول الـ upload لحد ظهور النتائج، وضفت ميزات view + download للـ doctor handoffs بحيث الدكتور يقدر يشوف الملف ويحمّله PDF."*

## مساهماتك بالتفصيل

### 3.1 Manual UI Testing + Bug Reporting
- اختبرت كل الـ critical flows: login → chat → triage → handoff → doctor inbox
- وثقت [`docs/MANUAL_VERIFY.md`](MANUAL_VERIFY.md) — checklist يدوي شامل
- اكتشفت bugs وتم إصلاحها (red flag false positives، schema errors، UI rendering issues)

### 3.2 Vision Tools Integration
- اختبرت `analyze_vision` على أنواع صور مختلفة (X-ray، skin، wound)
- ساعدت في إعداد الـ multi-provider setup (Gemini، Groq، OpenAI، OpenRouter)
- تأكدت إن الـ image upload + preview + analysis كلها شغّالة E2E
- اختبرت الـ retry logic لما provider يفشل

### 3.3 Doctor Handoff Features (View + Download)
- ميزة `view` — الدكتور يقدر يفتح الـ handoff ويشوف الـ SOAP note
- ميزة `download PDF` — تحميل الـ handoff بصيغة PDF احترافية
- تكامل مع `html2pdf.js` للتحويل
- ضمنت إن الـ Arabic content يـ render صح في الـ PDF (RTL support)

### 3.4 Tools Sanitization (Branch: mahmoud-ai-triage)
- شغّلت على branch منفصلة (`mahmoud-ai-triage`)
- ضمنت إن كل tool input بيتـ sanitize قبل ما يوصل للـ LLM
- شيلت strict patterns اللي كانت بتسبب Groq validation errors
- ضفت LLM stream error handling
- صلّحت ReAct infinite loop

## الأسئلة المحتملة + أجوبتك

**Q: إزاي تتأكد إن الـ AI tools شغّالة؟**
> *"عملت testing على مستويين: (1) Manual UI walkthrough لكل سيناريو — صداع، ألم صدر، حمى، طوارئ نفسية. (2) Vision-specific testing — رفعت صور حقيقية (أشعة، طفح جلدي) وتأكدت إن النتائج منطقية. لو في bug، بسجّله مع screenshot."*

**Q: ايه أصعب bug اكتشفته؟**
> *"الـ Vision LLM unavailable bug — كان الـ API بيرد بنجاح بس النتيجة بتبان كأنها فشل. الفيكس كان في الـ vision provider abstraction — الـ defaults الافتراضية كانت غلط لكل provider."*

**Q: ليه استخدمت html2pdf.js للـ download؟**
> *"عشان نحتاج نولّد PDF من الـ React component مباشرة بدون server roundtrip. html2pdf.js بياخد الـ DOM ويحوّله PDF بـ font support للعربي."*

---

# 4. 📘 محمد — Research + Initial Vision

## النقاط اللي تقولها

> *"أنا اللي حطّيت الفكرة الأساسية للمشروع. بدأت من تحديد المشكلة: المرضى في المنطقة العربية ما عندهمش وصول سهل لـ triage طبي بلغتهم. عملت research للحلول الموجودة (Babylon, Ada, K Health) وحطّيت الـ plan الأولي للمشروع. كمان اشتغلت على الـ documentation التأسيسية."*

## مساهماتك بالتفصيل

### 4.1 Initial Project Vision
- تحديد الـ problem statement: ما في AI triage عربي قوي
- تحديد الـ target users: مرضى ناطقين بالعربي + أطباء يحتاجوا أداة فرز
- اختيار الـ scope: triage + handoff (مش full diagnosis)

### 4.2 Research
- دراسة الـ competitors (Babylon Health، Ada، K Health، Buoy)
- اختيار الـ guidelines المرجعية (NICE CKS، WHO IMCI)
- تحديد الـ regulatory considerations (PHI، HIPAA-equivalent)

### 4.3 Initial Plan & Documentation
- وضع الـ roadmap الأولي
- كتابة الـ vision document
- توثيق الـ user stories والـ use cases
- المساهمة في الـ initial architecture decisions

## الأسئلة المحتملة + أجوبتك

**Q: ليه فكرة المشروع دي بالظبط؟ مش بدل نـ deploy موديل جاهز؟**
> *"الموديلات الجاهزة (ChatGPT, Claude) متدربة كـ general assistants، مش طبيين متخصصين. كمان مش بتلتزم بـ guidelines محددة، ولغتها العربية ضعيفة في الـ medical context. احنا بنينا workflow متخصص يلتزم بـ NICE/WHO ويتكلم لهجة مصرية."*

**Q: ايه الـ differentiator بتاعنا عن Ada / K Health؟**
> *"Ada و K Health مش بيدعموا العربي أصلًا، ومش بيوصفوا أدوية بـ Egyptian brand names. احنا متخصصين في السوق العربي مع formulary محلي."*

**Q: ايه الـ research methodology اللي اتبعتها؟**
> *"دراسة literature في medical AI، analysis لـ existing products، interviews غير رسمية مع أطباء، ومراجعة guidelines الـ NICE الـ open source."*

---

# 📋 نقاط مشتركة (كلنا نعرفها)

## الأرقام الرئيسية (احفظوها!)

| المقياس | القيمة |
|---|---|
| Backend modules | 115 Python files |
| Frontend pages | 19 (App Router) |
| AI tools | 14 |
| Chief complaints (KB) | 10 |
| Drug formulary entries | 10+ |
| Specialty templates | 3 |
| Backend tests | 305 |
| Frontend E2E tests | 12+ |
| Test coverage | ≥75% |
| Database tables | 15 |
| Supported languages | 2 (Arabic + English) |

## الـ Tech Stack

> Backend: **FastAPI + PostgreSQL + Redis + Alembic**
> Frontend: **Next.js 16 + React 19 + Tailwind v4**
> AI: **ReAct Agent + 14 tools + RAG (multilingual-e5 + bge-reranker)**
> Vision: **Multi-provider** (Gemini, GPT-4o, Llama-4, Qwen-VL)
> Safety: **Red flags + Hallucination gate + PHI encryption (Fernet AES-256)**
> Infra: **Docker + GitHub Actions CI + Prometheus + Sentry**

## أسئلة عامة محتمل تتسأل لأي حد فينا

**Q: المشروع شغّال فعلًا ولا demo؟**
> *"شغّال بالكامل — Docker stack كاملة، DB، 305 backend tests passing، 12 frontend E2E specs، CI gate. اللينك الحي على [اللينك بتاع الـ Cloudflare Tunnel]"*

**Q: ايه الـ limitations الحالية؟**
> *"الـ KB لسه فيه ١٠ complaints بس — محتاج clinician يوقّع عليها قبل الـ production launch. كمان مفيش عندنا clinical validation study (مقارنة الـ AI ضد physician baseline) — ده الـ next step."*

**Q: لو الـ AI غلط في تشخيص، مين المسؤول قانونيًا؟**
> *"الـ AI مش بيشخّص — هو فرز (triage) فقط. كل رد فيه disclaimer واضح إنه preliminary وليس بديل للطبيب. كمان حالات الـ emergency بتصعّد فورًا للـ ER بدون تشخيص."*

**Q: إزاي بتمنعوا الـ AI من إعطاء معلومات خطر؟**
> *"٣ طبقات: (1) Red flag detector ييـ block أي محادثة طارئة. (2) Clinical KB بـ contraindications علشان مفيش دواء يتوصف بدون فحص. (3) Self-check rules في الـ system prompt — الـ LLM بيشيك على نفسه قبل ما يبعت."*

---

# 🎯 نصايح أخيرة للمناقشة

## للجميع

1. **مفيش حد بيـ overlap في كلامه** — كل واحد يقول قسمه فقط، مفيش "أنا كمان عملت ده"
2. **استخدموا "احنا"** لما تتكلموا عن decisions جماعية ("احنا اخترنا Next.js لأن...")
3. **استخدموا "أنا"** لما تتكلموا عن عملكم الفردي ("أنا بنيت الـ Clinical KB")
4. **اعرفوا الـ flow الكامل** حتى لو مش بتعملوه — لو سؤال عن جزء مش بتاعك، احوّله للزميل ("ده تخصص محمود، بسيب ليه يجاوب")

## ترتيب اللي يتكلم (مقترح)

1. **محمد** يبدأ — الـ vision والـ problem statement (٢ دقيقة)
2. **حسام** — الـ architecture والـ technical decisions (٣ دقيقة)
3. **أحمد** — الـ frontend والـ design (٢ دقيقة)
4. **محمود** — الـ testing والـ tools integration (٢ دقيقة)
5. **حسام** — closing + live demo (٣ دقيقة)

**المجموع:** ١٢ دقيقة + ٥-١٠ دقايق للأسئلة

## قبل المناقشة بساعة

- [ ] افتح الـ tunnel + Docker + تأكد الـ chat شغّال
- [ ] جرب سيناريوهين فعليين (صداع، ألم صدر) عشان تكون مرتاح في الـ demo
- [ ] افتح الـ GitHub repo + الـ Swagger UI على tabs منفصلة
- [ ] احفظ الـ credentials في clipboard (`patient@medagent.com / Patient123`)

## أهم Demo Moments

| الـ Demo | الـ Wow Factor |
|---|---|
| Chat: "عندي صداع" | يظهر الـ intake questions + 🟢🟡🔴 differential من KB |
| Chat: "أنا حامل بآخد warfarin، عندي صداع" | يمنع NSAIDs + يختار باراسيتامول + يشرح السبب |
| Chat: "حاسس مش عاوز أعيش" | يظهر رقم ١٦٣٢٨ + كلام إنساني |
| Vision Compare | ٤ موديلات يحللوا نفس X-ray بالتوازي |
| Doctor Inbox | SOAP note منظّم + buttons (Acknowledge → Review → Close) |

---

**كل التوفيق يا فريق 🚀**

_Last updated: 2026-05-24_
