# MedAgent — Live Demo Script / سكريبت العرض المباشر

> **الجمهور:** لجنة DEPI · فريق المراجعة · أي حد بيحضر المناقشة.
> **المدة المستهدفة:** 15-20 دقيقة (5 مقدمة + 10 demo + 5 Q&A).
> **اللغة:** عربي أساسي، الإنجليزي بين قوسين للمصطلحات التقنية.
>
> **استخدم الـ doc ده كالـ teleprompter** — كل سيناريو فيه: الـ input اللي
> تكتبه، النتيجة المتوقعة، الـ talking point اللي توقف عنده، والـ backup
> plan لو حصلت مشكلة.

---

## 📋 جدول المحتويات / Table of contents

1. [قبل ما تبدأ — Pre-flight checklist](#0-pre-flight-checklist--قبل-ما-تبدأ)
2. [المقدمة (5 دقايق) — Opening pitch](#1-المقدمة--opening-pitch-5-min)
3. [Demo 1: المريض (5-7 دقايق)](#2-demo-1--المريض--patient-flow-57-min)
4. [Demo 2: الدكتور (3-4 دقايق)](#3-demo-2--الدكتور--doctor-flow-34-min)
5. [Demo 3: الأدمن (2-3 دقايق)](#4-demo-3--الأدمن--admin-flow-23-min)
6. [Q&A المتوقع — Anticipated questions](#5-qa-المتوقع--anticipated-questions)
7. [الخاتمة — Closing remarks](#6-الخاتمة--closing-remarks)
8. [Backup / لو حاجة وقعت](#7-backup--خطط-بديلة)

---

## 0. Pre-flight checklist / قبل ما تبدأ

شغّل دول **قبل بداية المناقشة بـ 10 دقايق**:

```bash
# 1. تأكد إن الـ docker شغّال
docker compose ps
# لازم تشوف postgres, redis, mailpit, backend, frontend → "Up"

# 2. تأكد إن الـ tunnels شغّالة
curl -s -o /dev/null -w "%{http_code}\n" https://suggestion-glass-qui-teeth.trycloudflare.com
curl -s -o /dev/null -w "%{http_code}\n" https://send-premium-coast-protecting.trycloudflare.com/api/v1/health/live
# الاتنين لازم يرجّعوا 200

# 3. منع الـ Mac من النوم
caffeinate -d &

# 4. تأكد إن الـ KB متبذّر
docker compose exec backend /app/.venv/bin/python /app/scripts/seed_kb.py --verify
# لازم تشوف "✓ KB has N chunks"

# 5. افتح ٣ tabs في الـ browser:
#    tab 1 → tunnel/ar/login  (للديمو الرئيسي)
#    tab 2 → tunnel/en/login  (لو سُئلت عن الـ EN)
#    tab 3 → http://localhost:8000/docs  (Swagger للـ API reference)
```

### الحسابات الجاهزة / Pre-seeded accounts

| Role | Email | Password |
|------|-------|----------|
| Patient | `patient@medagent.com` | `Test1234!` |
| Doctor | `doctor@medagent.com` | `Test1234!` |
| Admin | `admin@medagent.com` | `Test1234!` |

> لو محتاج تفعّل حساب جديد بسرعة:
> ```bash
> docker compose exec backend /app/.venv/bin/python /app/scripts/verify_user.py <email>
> ```

### الـ Models الحالية / Currently configured models

| Layer | Provider | Model |
|-------|----------|-------|
| Chat LLM | Groq | `llama-3.3-70b-versatile` |
| Verifier | Groq | `llama-3.1-8b-instant` |
| Vision | Groq | `llama-4-scout-17b-16e-instruct` |

---

## 1. المقدمة / Opening pitch (5 min)

### 🎯 سكريبت الافتتاح (دقيقة واحدة)

> "السلام عليكم لجنة الـ DEPI، أنا [اسمك] من فريق MedAgent.
>
> **المشكلة اللي بنحلّها:** المريض في مصر بيستنى متوسط 4 ساعات في عيادة العام
> عشان فحص بسيط. الـ AI الموجود في السوق إما إنجليزي بس أو بيدّي توصيات خطيرة
> من غير سياق طبي حقيقي.
>
> **حلّنا:** MedAgent — agent ثنائي اللغة (عربي + إنجليزي) بيعمل فرز طبي
> مبدئي للمريض، بيشتغل بـ 14 أداة طبية موصولة بقاعدة معرفة من مصادر موثوقة
> (NICE CKS, WHO IMCI, AHA)، وبيحوّل المريض للدكتور بـ handoff جاهز فيه
> ملخّص SOAP و FHIR export.
>
> **اللي هتشوفوه دلوقتي:** هنعدّي على ٣ تجارب فعلية — مريض، دكتور، أدمن — وكل
> تجربة بتوضّح طبقة من المعمارية."

### 📐 الـ Tech Stack (دقيقتين)

اعرض شريحة أو افتح `docs/architecture.md`:

```
┌─────────────────────────────────────────────────────────────┐
│ Frontend: Next.js 16 · React 19 · Tailwind 4 · next-intl   │
└─────────────────────────────────────────────────────────────┘
          ↓ SSE streaming + JWT (refresh-rotation)
┌─────────────────────────────────────────────────────────────┐
│ Backend: FastAPI 0.115 · SQLAlchemy 2 async · Alembic      │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ AI Pipeline                                              │ │
│ │  ├─ ReAct agent (14 tools)                              │ │
│ │  ├─ Clinical KB (10 complaints + 22 drugs + 3 specs)   │ │
│ │  ├─ pgvector RAG (multilingual-e5-large 1024-d)        │ │
│ │  ├─ Safety gate (hallucination + PHI scrubber)         │ │
│ │  └─ Vision tool (Groq Llama-4-Scout)                   │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
          ↓
┌─────────────────────────────────────────────────────────────┐
│ Postgres + pgvector · Redis · Prometheus + Grafana · Sentry │
└─────────────────────────────────────────────────────────────┘
```

### 📊 الأرقام / The numbers (30 ثانية)

- **115** Python module في الـ backend
- **19** route في الـ frontend
- **305** test (≥75% coverage)
- **14** أداة طبية في الـ agent
- **10** chief complaints + **22** دواء + **3** specialty templates
- **15** جدول DB متوافق مع FHIR

---

## 2. Demo 1 — المريض / Patient flow (5-7 min)

> **الجمهور هيشوف:** intake محادثي ذكي، ربط KB، تصنيف الخطورة، Vision على صورة
> تحاليل، توليد handoff للدكتور.

### Setup

افتح **tab 1**: `https://suggestion-glass-qui-teeth.trycloudflare.com/ar/login`

سجل دخول كـ `patient@medagent.com` / `Test1234!`.

---

### Scenario 1.A — حالة Routine عادية (1 دقيقة)

**اهدف:** اعرض الـ intake-first flow، RAG citation، triage scoring.

**اعمل "محادثة جديدة" واكتب:**

```
عندي صداع من ٣ ساعات في الجبهة، مش شديد جدًا. مفيش غثيان أو ضعف.
أخدت بنادول مفعلش حاجة.
```

**اللي هيحصل:**

1. ⏱️ ~5-10 ثواني الـ agent بيشتغل
2. هتظهر **triage badge** (Routine — اللون أخضر)
3. هتظهر **Differential Diagnosis panel** فيها:
   - Tension headache (محتمل جدًا)
   - Migraine (محتمل)
   - Cluster headache (أقل احتمالاً)
4. هيسأل intake questions:
   - "هل في حساسية من أدوية؟"
   - "هل بتاخد أدوية تانية حاليًا؟"
   - "هل عندك أمراض مزمنة (ضغط/سكر)؟"

**ال talking point:**

> "لاحظوا إن الـ agent **ما اقترحش دواء فوراً** — ده مش غباء، ده Hard Rule
> في الـ system prompt. الـ rule بتقول إن أي رد بدوا يتأكد من: حساسية +
> أدوية حالية + أمراض مزمنة + حمل. هنشوف ليه دلوقتي."

**جاوب الـ intake:**

```
مفيش حساسية، مفيش أدوية، مفيش أمراض مزمنة، عمري ٢٨ سنة.
```

**اللي هيحصل في الرد الجاي:**

5. الـ agent بيشغّل `check_medication_interactions` + `assess_drug_safety`
6. الرد فيه:
   - تعاطف + تأكيد للسياق
   - **management plan** (paracetamol 500-1000mg, hydration, dark room)
   - **علامات تستدعي الطوارئ** ("watch signals") — لو الصداع زاد فجأة، رؤية ضبابية، قيء
   - **Citation** من الـ KB (NICE CKS Headache)

**Talk-through:**

> "كل sentence في الرد ده موصول بـ KB chunk حقيقي. لو وقفت على أي اقتراح
> أقدر أوريكم الـ source citation الـ agent استخدمه."

---

### Scenario 1.B — حالة حمل / Pregnancy safety (1.5 دقيقة)

**اعمل محادثة جديدة واكتب:**

```
حامل في الشهر السابع، عندي صداع ومحتاجة أعرف أقدر آخد إيه آمن.
```

**اللي هيحصل:**

1. الـ agent بيشغّل **`assess_pregnancy_safety`** — الأداة بتترجم "الشهر السابع"
   تلقائياً لـ trimester 3
2. هيرفض **categorically** Ibuprofen + Diclofenac + Aspirin:
   > "في الثلث الثالث ممنوع تماماً — بيسبب إغلاق قناة القلب الجنينية المبكرة"
3. هيقترح **Paracetamol** (Category B, آمن في الحمل) — بس بعد ما يسأل عن حساسية
   وأمراض مزمنة

**Talk-through:**

> "ده مثال على Branch-specific safety. أداة `assess_pregnancy_safety` فيها
> ٢٢ دواء مصنّفين على FDA Pregnancy Categories (A/B/C/D/X). لاحظوا إن لو
> المريضة قالت 'الشهر السابع' الـ tool حوّلها أوتوماتيكياً لـ trimester 3 —
> ده pydantic validator مرن (lenient schema). والـ Hard Rule في الـ prompt
> بيمنع أي اقتراح دواء قبل ما الـ tool ده يشتغل."

---

### Scenario 1.C — حالة Emergency / Red flag (1.5 دقيقة)

**اعمل محادثة جديدة واكتب:**

```
عندي صداع شديد جداً بدأ فجأة من نص ساعة، مع قيء وخدر في الجانب الأيمن
من جسمي ومش قادر أتكلم كويس.
```

**اللي هيحصل:**

1. الـ agent بيشغّل `detect_red_flags` → يلاقي "thunderclap headache" + "weakness"
   + "speech difficulty" = stroke signs
2. **Triage badge تتحوّل لأحمر (Emergency)** فوراً
3. هتظهر **Watch Signals card** بـ:
   - 🚨 "علامات تستدعي طوارئ فورية"
   - "اتجه فوراً للمستشفى — هذه أعراض سكتة دماغية محتملة"
   - رقم الإسعاف: 123
4. الـ Emergency Playbook بيتفعّل — first aid: NPO، اتصل بالإسعاف، dont drive

**Talk-through:**

> "Emergency detection بيشتغل **قبل** أي اقتراح طبي. الـ agent بيقفل الـ
> triage path العادي ويفتح Emergency Playbook اللي فيه crisis resources +
> first aid actions. ده hard-wired في الـ prompt — مفيش أي حل ذكي ممكن
> يتخطّى الـ rule ده."

---

### Scenario 1.D — Vision على صورة تحاليل (1.5 دقيقة)

**في نفس المحادثة أو محادثة جديدة:**

1. اضغط **Attach image**
2. اختار صورة تحاليل دم (Cholesterol panel — موجودة في مجلد screenshots لو محتاج)
3. اكتب:
   ```
   راجع تحاليل الكوليسترول دي من فضلك
   ```

**اللي هيحصل:**

1. الـ agent بيشغّل **`analyze_vision`** على الصورة → Groq Llama-4-Scout 17B
2. هتظهر **VisionResultCard** فيها:
   - الأرقام المستخرجة (LDL, HDL, T.Cholesterol, VLDL)
   - مقارنة مع الـ reference ranges
   - تفسير مبدئي
3. الـ chat response فيه السياق السريري:
   - "نتائج التحليل بتوضّح ..."
   - توصيات تغيير نمط الحياة
   - متى يلزم استشارة طبيب

**Talk-through:**

> "الـ Vision في MedAgent مش بيستبدل الطبيب — هو preliminary AI read. لاحظوا
> الـ disclaimer في الكارت. الـ Vision provider قابل للتبديل من dropdown
> (Groq, Gemini, OpenAI, OpenRouter) عشان نقدر نقارن النماذج."

---

### Scenario 1.E — توليد Handoff (دقيقة واحدة)

في نهاية المحادثة:

1. اضغط **"Send to Doctor"** زرار
2. هيظهر dialog فيه list الدكاترة المتاحين
3. اختار `Dr. doctor@medagent.com`
4. **اضغط Send**
5. هتظهر confirmation: "تم إرسال الحالة للدكتور"

**Talk-through:**

> "الـ handoff ده بيتولّد بالـ LLM من المحادثة كاملةً بصيغة SOAP note
> (Subjective/Objective/Assessment/Plan). والـ patient ID بيتشفّر بـ Fernet
> AES-256 قبل ما يتخزّن. هنشوف الدكتور بيستلمه ازاي دلوقتي."

---

## 3. Demo 2 — الدكتور / Doctor flow (3-4 min)

> **الجمهور هيشوف:** Inbox triaged، Status state machine، Private notes
> autosave، PDF + FHIR export.

### Setup

افتح **tab 1** جديد (أو tab تاني): `tunnel/ar/login`

سجّل **Sign out** من حساب المريض، وادخل كـ `doctor@medagent.com` / `Test1234!`.

---

### Scenario 2.A — Inbox + فلاتر (دقيقة واحدة)

1. هتفتح على `/doctor/inbox` مباشرةً
2. هتشوف القائمة فيها الحالة اللي بعتها المريض دلوقتي:
   - مع badge "Emergency" أحمر / "Routine" أخضر / "Urgent" برتقالي
   - timestamp + اسم المريض + ملخص (snippet) أول 100 حرف
3. جرّب الفلاتر:
   - **Status** filter: New / Acknowledged / In review / Reviewed / Closed
   - **Triage level** filter
   - **Search** (q): اكتب "صداع" → بتلاقي بس الحالات المتعلقة
   - **Sort**: Priority / sent_at / created_at

**Talk-through:**

> "الـ inbox بيرتّب الحالات بأولوية (Emergency first). كل حالة فيها priority
> score بيتحسب من triage level + الـ waiting time. الـ filters كلها بتعمل
> server-side pagination — مش بنحمّل آلاف الحالات في الـ client."

---

### Scenario 2.B — مراجعة Handoff (1.5 دقيقة)

1. اضغط على حالة الـ Emergency stroke (Scenario 1.C)
2. هيفتح `/doctor/handoff/[id]` فيها:
   - **Status timeline** (chips بتعرض المراحل: new → acknowledged → in_progress → reviewed → closed)
   - **Patient info** (الاسم، اللغة، الـ conversation ID)
   - **Medical summary** — SOAP note بالـ Markdown (Chief Complaint, HPI, Symptoms, Red Flags, Plan)
   - **Workflow actions**: Acknowledge, Begin review, Mark reviewed, Close case
   - **Private notes** textarea بـ autosave

3. اضغط **Acknowledge** → الـ status يتحوّل لـ "Acknowledged" فوراً (optimistic UI)
4. اكتب في الـ Private Notes:
   ```
   مريض يحتاج CT scan فوري. أبلغت قسم الطوارئ، رقم الاتصال 01234567890.
   ```
5. استنى ~1.5 ثانية → "Saved at HH:MM" تظهر تحت textarea (autosave)
6. اضغط **Begin review** → status بيتحول لـ "In review"

**Talk-through:**

> "الـ status transitions بتشتغل optimistic — الـ UI بيتحدّث فوراً ولو الـ
> backend رجّع error بنعمل rollback. والـ private notes بتاخد autosave بـ
> debounced timer (1.5 ثانية بعد آخر keystroke). الـ notes دي doctor-only —
> المريض ما بيشوفهاش أبداً."

---

### Scenario 2.C — PDF + FHIR Export (دقيقة واحدة)

1. اضغط **Download PDF** فوق على اليمين
2. هتنزل PDF كاملة فيها:
   - ترويسة بمعلومات المريض
   - الـ SOAP note كاملةً
   - الـ disclaimer + AI model used

3. (اختياري) افتح Swagger وأرّيهم الـ FHIR export endpoint:
   ```
   GET /api/v1/handoffs/{id}/export?format=fhir
   ```

**Talk-through:**

> "الـ PDF بـ ReportLab، والـ FHIR export بـ FHIR R4 Bundle جاهز للـ
> integration مع أي HIS/EMR. الـ HL7 v2 endpoint موجود بردو لو في
> integration قديمة. كل export بيتسجّل في `handoff_exports` audit table."

4. **اضغط Mark reviewed → Close case** → status timeline يتقفل

---

## 4. Demo 3 — الأدمن / Admin flow (2-3 min)

> **الجمهور هيشوف:** Doctor approval, Audit chain verification, Safety
> dashboard.

### Setup

Sign out من حساب الدكتور، ادخل كـ `admin@medagent.com` / `Test1234!`.

---

### Scenario 3.A — Doctor approval (دقيقة واحدة)

1. روح `/admin/doctors`
2. هتشوف list دكاترة فيه `pending approval`
3. اضغط على دكتور بتاع pending → هيظهر:
   - License number
   - Specialty
   - Email
4. اضغط **Approve**
5. هيـ trigger:
   - email notification للدكتور بإن الحساب اتفعّل
   - audit log entry بـ `approve_doctor` action

**Talk-through:**

> "الـ doctor approval flow بيمنع أي حد من إنشاء حساب 'دكتور' من غير
> verification يدوية. والـ approval action نفسها بتتسجّل في الـ audit log
> اللي عمره ما بيتعدّل."

---

### Scenario 3.B — Audit chain verification (دقيقة واحدة)

1. روح `/admin/audit`
2. هتشوف table بكل actions اللي حصلت اليوم:
   - `user_register`, `email_verify`, `chat_request`, `create_handoff`,
     `update_status`, `download_pdf`, `approve_doctor`...
   - كل entry فيها `previous_hash` و `current_hash` (SHA-256)
3. اضغط **Verify chain** زر
4. لو الشيكول صحيح: ✅ "Chain valid — N entries verified"
5. لو حد عدّل في الـ DB يدوياً: ❌ "Chain broken at entry #X"

**Talk-through:**

> "الـ audit log بيستخدم SHA-256 hash chain — كل entry هاش الـ previous +
> الـ payload الحالي. لو حد فتح postgres وعدّل أي صف، الـ chain هينكسر
> والـ verification هترصد ده. ده tamper detection من غير ما نعتمد على
> external service. متطلّب لـ HIPAA-style compliance."

---

### Scenario 3.C — Safety dashboard (30 ثانية)

1. روح `/admin/safety`
2. هتشوف:
   - عدد الـ red flags المكتشفة آخر 24 ساعة
   - عدد الـ hallucinations اللي الـ verifier اكتشفها
   - متوسط الـ citation completeness score
   - أكتر الـ tools استخداماً

**Talk-through:**

> "الـ safety metrics بتساعد فريق الجودة الطبية على إيجاد cases احتاجت تدخل
> بشري. لو شفنا zero red flags لمدة طويلة، ده غالباً يعني الـ detector
> ضعيف ومحتاج tuning."

---

## 5. Q&A المتوقع / Anticipated questions

### الأسئلة التقنية / Technical questions

| السؤال (محتمل) | الجواب القصير |
|---------------|---------------|
| **ليه ReAct agent مش function calling مباشر؟** | ReAct بيدّينا قدرة على multi-step reasoning + intermediate observations نقدر نـ stream للـ UI كـ events. Function calling مباشر بيدّي الإجابة بس بدون شفافية. |
| **إزاي بتمنعوا الـ hallucination؟** | ٣ طبقات: (1) RAG citation من KB موثّق، (2) `verify_no_hallucination` tool ببعد LLM call، (3) `post_llm_gate` بيعيد كتابة العبارات الخطرة. |
| **ليه pgvector مش Pinecone/Weaviate؟** | Pgvector في نفس الـ Postgres → ACID transactions، مفيش data sync issues، أرخص للـ MVP. ممكن نهاجر لـ vendor managed لو الـ scale طلب. |
| **إيه الـ encryption strategy للـ PHI؟** | Fernet AES-128-CBC + HMAC على mode column في SQLAlchemy. الـ key في env var (محمي بـ KMS في production). كل قراءة/كتابة بتعمل decrypt/encrypt تلقائياً. |
| **إزاي بتدعموا اللغتين بنفس quality؟** | (1) `multilingual-e5-large` embedder بيشتغل على AR+EN, (2) Prompts منفصلة بالـ tone الطبي المحلي، (3) Clinical KB synonyms ثنائية اللغة. |
| **الـ Agent بيتأخذ تقرار طبي بدل الدكتور؟** | لأ. الـ agent بيعمل **preliminary triage** بس. كل رد فيه disclaimer واضح + watch signals + ممنوع يقترح prescription dosage في أول رد. |
| **إيه الـ tests coverage؟** | ≥75% backend (305 tests inc. integration), 10+ Playwright E2E specs, CI gate بيرفض أي PR ينقّص الـ coverage. |
| **إزاي بتعملوا scale لـ 1000 concurrent users؟** | (1) FastAPI async, (2) Connection pooling في SQLAlchemy, (3) Redis للـ session state, (4) SSE streaming بدل polling, (5) Stateless workers → horizontal scale. |
| **الـ LLM costs؟** | حالياً free tier (Groq 14400 req/day). للـ production: مخططين OpenAI gpt-4o-mini ($0.15/1M input tokens). على 1000 user/day بمتوسط 5K tokens، ~$3/day. |
| **إيه الـ failure modes؟** | (1) LLM API down → cached fallback responses, (2) DB down → 503 + retry queue, (3) Vision down → text-only flow, (4) Safety gate failure → degraded reply with warning. |

### الأسئلة الإكلينيكية / Clinical questions

| السؤال | الجواب |
|--------|--------|
| **الـ Clinical content مصادره إيه؟** | NICE CKS, WHO IMCI, AHA/ACC guidelines, BNF (drugs). كل complaint في YAML فيه citation. |
| **مين بيراجع الـ KB؟** | حالياً الفريق راجع كل complaint مع طبيب استشاري. للـ production، مخططين clinical review board بيراجع quarterly. |
| **إزاي بتحدّثوا الـ KB؟** | YAML files في git → PR review → auto-reload في الـ KB loader (مفيش migration). |
| **الـ Triage scoring مبني على إيه؟** | Manchester Triage System (MTS) كـ baseline، مع adjustments محلية للسياق المصري. |
| **بتغطّوا أي تخصصات؟** | الـ MVP فيه 10 chief complaints adult primary care + 3 specialty templates (GP, Pediatrics, ENT). الـ Cardiology + Dermatology في الـ roadmap. |

### أسئلة الأمان / Security questions

| السؤال | الجواب |
|--------|--------|
| **HIPAA compliant؟** | المعمارية compliant-ready (encryption, audit trail, RBAC). الـ formal certification محتاج SOC 2 audit — مش في الـ MVP scope. |
| **إيه السياسة لو حصل breach؟** | (1) Sentry بيرصد فوراً، (2) PHI scrubber في الـ error events، (3) Audit chain بيوريك إيه اللي اتعمل، (4) Notification flow للمستخدمين المتأثرين. |
| **الـ Authentication strong كفاية؟** | JWT access token (15min) + refresh token (7d rotatable) + bcrypt password hashing + account lockout بعد 5 محاولات فاشلة + email verification إجباري. الـ Admin MFA في الـ roadmap. |

---

## 6. الخاتمة / Closing remarks (1 min)

### السكريبت

> "في الـ ٢٠ دقيقة دي شفتم:
>
> - **Patient flow**: محادثة ثنائية اللغة، triage محترم للسياق، vision على
>   صور تحاليل، توليد handoff آمن.
> - **Doctor flow**: inbox triaged، state machine، autosave، PDF + FHIR export.
> - **Admin flow**: doctor approval، audit chain verification، safety
>   dashboard.
>
> ووراء كل ده: 14 أداة طبية، 10 chief complaints موثّقين، 305 test، و
> معمارية async قابلة للـ scale.
>
> الـ MedAgent مش بديل للدكتور — هو **partner** بيعمل intake مهنية وبيوفّر
> ٧٠٪ من وقت الطبيب في الأسئلة الروتينية. ده اللي إحنا حابّين نوفّره
> للمنظومة الصحية المصرية.
>
> شكراً ليكم على وقتكم. مستعدّين لأي أسئلة."

### الكلمات اللي تستحق التشديد

- **"بدون نموذج طبي"** ❌ → استبدلها بـ **"AI partner للطبيب"** ✅
- **"بيشخّص"** ❌ → **"بيعمل preliminary triage"** ✅
- **"بيوصف الدواء"** ❌ → **"بيقترح للطبيب يفكر في"** ✅

---

## 7. Backup / خطط بديلة لو حاجة وقعت

### لو الـ tunnel وقع

```bash
# اعمل tunnel جديد
cloudflared tunnel --url http://localhost:3000 &
# انسخ الـ URL الجديد ووزّعه على التيم
```

### لو الـ Groq هيت الـ daily limit

في الـ `.env`:
```
LLM_MODEL=groq/llama-3.1-8b-instant
```
بعدين:
```bash
docker compose up -d --force-recreate --no-deps backend
```

### لو الـ Vision tool فشل

افتح dropdown اختيار الـ Vision model في الـ UI، بدّل لـ:
- Gemini
- OpenAI gpt-4o
- OpenRouter Llama Vision

### لو الـ DB قام بمشاكل

```bash
# آخر حل — reset كامل (ممكن يخسّر demo data)
make reset && make seed-all
```

### لو الإيميل verification مش بيشتغل

استخدم السكريبت اللي عملناه:
```bash
docker compose exec backend /app/.venv/bin/python /app/scripts/verify_user.py <email>
```

### لو الـ chat رجّع error غريب

افتح conversation جديدة. الـ KB cache + tool registry بتتعاد بناء.

---

## 📌 ملاحظات أخيرة / Final tips

1. **خليك واثق** — المشروع شغّال على الـ tunnel من ساعات والـ team جربه قبل كده.
2. **متخوّش حد لما يسأل سؤال صعب** — قول "ده سؤال ممتاز، الإجابة الدقيقة في
   `docs/<X>.md`، بس باختصار…" وفسّر باختصار. الـ doc هيغطّي التفاصيل.
3. **خلّي الديمو يتكلّم بدالك** — متفسّرش أكتر من اللازم لمّا الـ UI واضح.
4. **خليك ready تجاوب بـ "in scope" vs "future work"** — مش كل حاجة مفروض
   تكون عاملاها. صدق إن نموذج الـ MVP محدود وفي roadmap واضح.
5. **اسكر التيم في الآخر بالأسماء** — Mohamed, Mahmoud, Ahmed, Hossam.

---

## 🎬 الـ timing breakdown ملخّص / Time budget at a glance

| الـ Segment | الوقت | المتراكم |
|------------|-------|---------|
| Pre-flight checklist | 10 min before | — |
| المقدمة (script + tech + numbers) | 5 min | 5 min |
| Demo 1 — Patient (5 scenarios) | 7 min | 12 min |
| Demo 2 — Doctor (3 scenarios) | 4 min | 16 min |
| Demo 3 — Admin (3 scenarios) | 3 min | 19 min |
| Q&A | flexible | — |
| Closing remarks | 1 min | 20 min |

---

_آخر تحديث: 2026-05-24 — قبل الـ defense بليلة._
