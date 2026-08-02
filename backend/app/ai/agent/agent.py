"""MedAgent ReAct loop — connects LLM, tools, safety, and conversation streaming."""

import json
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from app.ai.agent.branches.pediatric import PediatricContext
from app.ai.agent.branches.pregnancy import PregnancyContext
from app.ai.agent.pii import scrub_pii
from app.ai.agent.registry import ToolRegistry
from app.ai.agent.tot_mode import ToTOrchestrator
from app.ai.llm.base import LLMProvider
from app.ai.safety.post_llm_gate import PostLLMSafetyGate
from app.ai.tools.red_flag_detector import RedFlagDetector
from app.ai.tools.verify_no_hallucination import HallucinationVerifier

MAX_ITERATIONS = 5


class AgentEvent(BaseModel):
    """Single event emitted by the agent during a conversation turn."""

    type: str  # "token", "tool_start", "tool_result", "triage", "red_flag", "done", "error"
    content: str = ""
    data: dict[str, Any] = {}


class MedAgent:
    """ReAct agent — thinks → acts → observes loop with tools and safety."""

    def __init__(
        self,
        llm: LLMProvider,
        registry: ToolRegistry,
        patient_age: int | None = None,
        patient_conditions: list[str] | None = None,
        patient_is_pregnant: bool = False,
        verifier: HallucinationVerifier | None = None,
    ):
        self.llm = llm
        self.registry = registry
        self.patient_age = patient_age
        self.patient_conditions = patient_conditions or []
        self.patient_is_pregnant = patient_is_pregnant
        self.red_flag_detector = RedFlagDetector()
        self._system_prompts: dict[str, str] = {}

        # بوابة الأمان (اختيارية — بتشتغل لو موجودة)
        self._safety_gate = PostLLMSafetyGate(verifier) if verifier else None

        # Build branch contexts once
        self._pediatric_ctx: PediatricContext | None = (
            PediatricContext.from_age_years(float(patient_age))
            if patient_age is not None and patient_age < 18
            else None
        )
        self._pregnancy_ctx: PregnancyContext | None = (
            PregnancyContext(trimester=None) if patient_is_pregnant else None
        )

    def _resolve_branch(self, user_message: str) -> None:
        """Auto-detect pregnancy branch from conversation text if not already set."""
        if self._pregnancy_ctx is None and self._pediatric_ctx is None:
            detected = PregnancyContext.detect_from_text(user_message)
            if detected:
                self._pregnancy_ctx = detected
                self.patient_is_pregnant = True

    def _load_system_prompt(self, language: str) -> str:
        """Load and format the system prompt for the given language and patient context."""
        if self._pediatric_ctx:
            key = self._pediatric_ctx.system_prompt_key(language)
        elif self._pregnancy_ctx or self.patient_is_pregnant:
            key = f"{language}_pregnancy"
        else:
            key = language

        if key not in self._system_prompts:
            prompts_dir = Path(__file__).resolve().parent / "prompts"
            filename = f"system_{key}.txt"
            if not (prompts_dir / filename).exists():
                filename = f"system_{language}.txt"
            with open(prompts_dir / filename, encoding="utf-8") as f:
                template = f.read()
            self._system_prompts[key] = template.format(
                current_date=datetime.now(UTC).strftime("%Y-%m-%d"),
                patient_age=self.patient_age or "unknown",
                conditions=", ".join(self.patient_conditions) or "none reported",
            )
        return self._system_prompts[key]

    async def run(
        self,
        user_message: str,
        conversation_history: list[dict[str, str]] | None = None,
        language: str = "en",
        conversation_id: str | None = None,
        image_data: str | None = None,
        image_kind: str | None = None,
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Run one turn of the agent loop.

        Parameters
        ----------
        user_message : str
            The patient's latest message.
        conversation_history : list or None
            Previous messages in the conversation.
        language : str
            "ar" or "en".
        conversation_id : str or None
            Real conversation UUID from the database (injected into tool args).
        image_data : str or None
            Optional base64 data URI of an attached medical image. When present,
            forces a call to `analyze_vision` before normal LLM iteration.
        image_kind : str or None
            Optional hint about image type (xray | ct | photo | skin | wound | other).

        Yields
        ------
        AgentEvent
            Streaming events for the frontend.
        """
        # ── Step 0: PII scrub + branch auto-detect ──
        safe_message = scrub_pii(user_message)
        self._resolve_branch(safe_message)

        # ── Step 0.5: Force analyze_vision when image is attached ──
        # نُدخل تحليل الصورة مباشرةً قبل ما الـ LLM يقرر، لأن أغلب موديلات
        # الـ chat-only ما بتشوفش الصور، فبنحقن نتيجة analyze_vision كـ tool message.
        vision_tool_result: dict[str, Any] | None = None
        if image_data:
            vision_tool = self.registry.get("analyze_vision")
            if vision_tool:
                yield AgentEvent(
                    type="tool_start",
                    content="Analyzing image...",
                    data={"tool": "analyze_vision"},
                )
                try:
                    tool_input = vision_tool.input_schema(
                        image_url=image_data,
                        image_kind=image_kind or "other",
                        context=safe_message[:1500],
                        language=language,
                        conversation_id=conversation_id or "",
                    )
                    vision_tool_result = await vision_tool.run(tool_input)
                except Exception as e:
                    vision_tool_result = {
                        "findings": [],
                        "urgency": "routine",
                        "confidence": 0.0,
                        "is_medical": True,
                        "error": str(e),
                    }
                yield AgentEvent(
                    type="tool_result",
                    data={"tool": "analyze_vision", "result": vision_tool_result},
                )

        # ── Step 1: Red-flag fast path (base + branch-specific) ──
        # red_flag_result = self.red_flag_detector.detect(safe_message)
        # ── Step 1: Red-flag fast path (AI Semantic Triage) ──
        # نستخدم دالة الذكاء الاصطناعي وبنمررلها رسالة المريض والـ llm
        red_flag_result = await self.red_flag_detector.detect_with_ai(safe_message, self.llm)

        # Delegate to standalone branch tools for richer checks
        if self._pediatric_ctx:
            _apply_pediatric_red_flags(self._pediatric_ctx, safe_message, red_flag_result)

        if self._pregnancy_ctx or self.patient_is_pregnant:
            _apply_pregnancy_red_flags(safe_message, red_flag_result)

        # ── Emergency: emit the badge but DO NOT short-circuit the LLM ──
        #
        # The previous behavior was a `yield done; return` here — patient in
        # crisis (e.g. suicidal ideation, chest pain, stroke signs) got ONLY
        # the red badge and ZERO tokens of actual help. That's the opposite
        # of what an emergency triage assistant should do: emergencies are
        # the cases where the patient needs the MOST guidance (hotline
        # number, first-aid step, recovery position, what to say when they
        # call), not the least.
        #
        # We still emit the badge events (so the chip stays red and the
        # triage panel stays visible), but we then drop down into the
        # regular ReAct loop so the LLM produces an empathic, concrete
        # response. The Emergency Playbook section of the system prompt
        # tells the LLM what to include (hotlines, first aid, position).
        if red_flag_result["has_red_flag"] and red_flag_result["severity"] == "emergency":
            try:
                from app.core.metrics import red_flags_detected_total, triage_level_total

                branch = (
                    "pediatric"
                    if self._pediatric_ctx
                    else ("pregnancy" if self._pregnancy_ctx else "base")
                )
                red_flags_detected_total.labels("emergency", branch).inc()
                triage_level_total.labels("emergency").inc()
            except Exception:
                pass
            yield AgentEvent(
                type="red_flag",
                data=red_flag_result,
                content="Emergency red flag detected — seek immediate medical attention.",
            )
            yield AgentEvent(
                type="triage",
                data={
                    "level": "emergency",
                    "score": 100,
                    "reasoning": red_flag_result.get(
                        "reasoning",
                        "Emergency red flag detected",
                    ),
                    "flags": red_flag_result.get("flags", []),
                },
            )
            # Mark emergency in emergency_triage so the prompt path below
            # sees it and knows to run the emergency playbook. We don't
            # return — let the ReAct loop continue so the LLM writes the
            # actual response the patient needs.
            emergency_triage: dict[str, Any] | None = {
                "level": "emergency",
                "score": 100,
                "reasoning": red_flag_result.get(
                    "reasoning",
                    "Emergency red flag detected",
                ),
                "flags": red_flag_result.get("flags", []),
                "_emergency_short_circuit": True,
            }
        else:
            emergency_triage = None

        # ── Step 1.5: Server-side triage pre-flight ──
        # CX4: small/cheap models often skip score_triage even when the
        # prompt mandates it. We run the deterministic scorer ourselves and
        # inject the result as a tool message — the LLM gets the context,
        # AND the frontend sees a triage badge when one is actually warranted.
        #
        # CX5: skip the pre-flight entirely for greetings / yes-no / thanks.
        # A "السلام عليكم" should NOT produce a "Routine · Score 10" badge —
        # that's anti-clinical and looks unprofessional.
        # ── Server-side clinical-KB lookup (the substance layer) ──
        # Match the chief complaint against the curated YAML library and
        # inject the result as a synthesized tool message. This is what
        # turns the agent from "LLM guesses medical advice" to "LLM
        # paraphrases curated NICE/WHO content with Egyptian formulary
        # brand names". We run it for every symptom-shaped message even
        # before the LLM gets a turn, so the model can't write a reply
        # without the KB context in front of it.
        clinical_lookup_result: dict[str, Any] | None = None
        if _is_likely_symptom_message(safe_message):
            clinical_tool = self.registry.get("clinical_lookup")
            if clinical_tool:
                try:
                    lookup_input = clinical_tool.input_schema(
                        symptom_text=safe_message,
                        language=language,
                        age_years=self.patient_age,
                    )
                    clinical_lookup_result = await clinical_tool.run(lookup_input)
                    if (clinical_lookup_result or {}).get("matched"):
                        yield AgentEvent(
                            type="tool_result",
                            data={
                                "tool": "clinical_lookup",
                                "result": clinical_lookup_result,
                            },
                        )
                except Exception:
                    # KB miss is non-fatal — agent continues with general path.
                    clinical_lookup_result = None

        # Start the pre-flight with the emergency triage (if any) as the
        # baseline so the LLM always sees the emergency context even if
        # _is_likely_symptom_message decides not to re-run score_triage.
        # Emergency *always* wins — we skip the symptom-scorer entirely in
        # that case to avoid downgrading the level (e.g. the rule-based
        # scorer might return "urgent" for "chest pain" when the AI
        # detector already classified the same input as emergency).
        triage_pre_result: dict[str, Any] | None = emergency_triage
        if emergency_triage is None and _is_likely_symptom_message(safe_message):
            triage_tool = self.registry.get("score_triage")
            if triage_tool:
                try:
                    triage_input = triage_tool.input_schema(
                        symptoms=safe_message,
                        age_years=self.patient_age,
                        language=language,
                    )
                    triage_pre_result = await triage_tool.run(triage_input)
                except Exception as e:
                    triage_pre_result = {
                        "level": "routine",
                        "score": 0,
                        "reasoning": f"triage_failed: {e}",
                    }
                # CX5: only emit the triage event when the result is meaningful.
                # If the scorer returned the default "no rules matched" answer,
                # there's nothing useful to show — suppress the badge.
                if (
                    isinstance(triage_pre_result, dict)
                    and "level" in triage_pre_result
                    and _triage_is_meaningful(triage_pre_result)
                ):
                    # UX2: build the "Why urgent?" bullets up-front from
                    # detected red flags + scorer reasoning so the frontend
                    # can show explainability under the triage badge.
                    why_bullets: list[str] = []
                    for f in (red_flag_result or {}).get("flags", []) or []:
                        kw = (f or {}).get("keyword") if isinstance(f, dict) else None
                        if kw and kw not in why_bullets:
                            why_bullets.append(str(kw))
                    triage_reasoning = str(triage_pre_result.get("reasoning") or "").strip()
                    if triage_reasoning and triage_reasoning not in why_bullets:
                        why_bullets.append(triage_reasoning)

                    yield AgentEvent(
                        type="triage",
                        data={
                            "level": triage_pre_result.get("level"),
                            "score": triage_pre_result.get("score"),
                            "reasoning": triage_pre_result.get("reasoning", ""),
                            "flags": triage_pre_result.get("red_flags", []),
                            # UX2: front-end renders these as "لماذا؟" bullets
                            "why": why_bullets[:4],
                        },
                    )
                    yield AgentEvent(
                        type="tool_result",
                        data={"tool": "score_triage", "result": triage_pre_result},
                    )

                    # UX3: surface a patient-facing watch list of red flags
                    # to monitor for, picked by symptom category.
                    watch_signals = _get_watch_signals(safe_message, language)
                    if watch_signals:
                        yield AgentEvent(
                            type="watch_signals",
                            data={"signals": watch_signals},
                        )
                else:
                    # Don't inject a useless triage into the LLM context either.
                    triage_pre_result = None

        # ── Step 2: Build messages ──
        system_prompt = self._load_system_prompt(language)
        messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]

        if conversation_history:
            messages.extend(conversation_history)

        # لو في صورة، نضيف ملاحظة للرسالة عشان حتى الموديلات النصية البحتة
        # (زي Llama 3.x / Allam) تعرف إن المستخدم بعت صورة وإن نتيجة التحليل
        # هتبقى في tool message اللي بعد كده.
        user_content = safe_message
        if vision_tool_result is not None:
            attach_note = (
                "\n\n[المستخدم أرفق صورة طبية للتحليل — راجع نتيجة أداة analyze_vision]"
                if language == "ar"
                else "\n\n[The user attached a medical image — see the analyze_vision tool result below]"
            )
            user_content = f"{safe_message}{attach_note}"
        messages.append({"role": "user", "content": user_content})

        # ── Inject vision tool result as conversation context ──
        # بعد ما رسالة المستخدم النصية اتحطّت، بنضيف رسالة assistant وبعدها tool
        # علشان الـ LLM يلاقي تحليل الصورة كأنه استخدم الأداة بنفسه.
        if vision_tool_result is not None:
            vision_call_id = "call_vision_pre"
            # IMPORTANT: include every *required* field from VisionInput here.
            # Some providers (Groq with strict tool validation, certain
            # OpenRouter routes) validate every tool_call in the *history*
            # against the registered tool's schema — not just the live call.
            # Omitting `image_url` (which is min_length=1 + required) used to
            # explode the next turn with:
            #   tool call validation failed: missing properties: 'image_url'
            # We can't put the real base64 data here (would blow up the token
            # budget), and the LLM never re-runs this synthesized call, so a
            # short placeholder is enough to satisfy the schema gate.
            messages.append(
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": vision_call_id,
                            "type": "function",
                            "function": {
                                "name": "analyze_vision",
                                "arguments": json.dumps(
                                    {
                                        "image_url": "[image_already_analyzed]",
                                        "image_kind": image_kind or "other",
                                        "language": language,
                                    }
                                ),
                            },
                        }
                    ],
                }
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": vision_call_id,
                    "content": json.dumps(vision_tool_result, ensure_ascii=False),
                }
            )

        # Inject the clinical_lookup result as a synthesized tool message
        # so the LLM treats it as "I already pulled the NICE/WHO content".
        # We pass a *trimmed* projection — the full result still flows to
        # the frontend in the live event, but the LLM only needs the fields
        # it has to quote. The full payload (especially `_handoff_packet`
        # and `red_flag_rationales`) is several KB of JSON and chokes
        # smaller models: the LLM spends its `max_tokens` budget chewing
        # through it and never gets to writing the patient reply.
        if clinical_lookup_result is not None and clinical_lookup_result.get("matched"):
            trimmed_for_llm = {
                "matched": True,
                "complaint_id": clinical_lookup_result.get("complaint_id"),
                "complaint_name": clinical_lookup_result.get("complaint_name"),
                # Top 3 differentials only, and only the patient-facing fields
                "differentials": [
                    {
                        "name": d.get("name"),
                        "likelihood": d.get("likelihood"),
                        "key_features": (d.get("key_features") or [])[:3],
                    }
                    for d in (clinical_lookup_result.get("differentials") or [])[:3]
                ],
                # Self-care: keep instruction + duration + brand_names_eg + contraindications
                "self_care": [
                    {
                        "instruction": s.get("instruction"),
                        "duration": s.get("duration"),
                        "brand_names_eg": (s.get("brand_names_eg") or [])[:4],
                        "contraindications": (s.get("contraindications") or [])[:2],
                    }
                    for s in (clinical_lookup_result.get("self_care") or [])
                ],
                # Top 4 escalation signs — the most relevant ones already at top
                "when_to_escalate": (clinical_lookup_result.get("when_to_escalate") or [])[:4],
                # One sample followup the LLM can ask if needed
                "followup_questions": [
                    {"question": q.get("question")}
                    for q in (clinical_lookup_result.get("followup_questions") or [])[:3]
                ],
            }
            cl_call_id = "call_clinical_pre"
            messages.append(
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": cl_call_id,
                            "type": "function",
                            "function": {
                                "name": "clinical_lookup",
                                "arguments": json.dumps(
                                    {"symptom_text": safe_message, "language": language}
                                ),
                            },
                        }
                    ],
                }
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": cl_call_id,
                    "content": json.dumps(trimmed_for_llm, ensure_ascii=False),
                }
            )

        # CX4: inject the pre-computed triage as a tool message so the LLM
        # sees it as already-executed work. This stops it from either
        # (a) skipping triage entirely or (b) calling score_triage again.
        if triage_pre_result is not None:
            triage_call_id = "call_triage_pre"
            messages.append(
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": triage_call_id,
                            "type": "function",
                            "function": {
                                "name": "score_triage",
                                "arguments": json.dumps(
                                    {"symptoms": safe_message, "language": language}
                                ),
                            },
                        }
                    ],
                }
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": triage_call_id,
                    "content": json.dumps(triage_pre_result, ensure_ascii=False),
                }
            )

        # When the red-flag detector classified this as an emergency, inject
        # an explicit "you are in emergency mode" system note RIGHT before
        # the LLM generates so the model anchors on the Emergency Playbook
        # section of the prompt (hotlines, first aid, position, what to
        # bring). Without this nudge, weaker models tend to revert to a
        # generic "seek immediate care" line — which is exactly the 0-token
        # deflection the patient was complaining about.
        if emergency_triage is not None:
            flag_summary = ", ".join(
                str((f or {}).get("keyword", "")) for f in red_flag_result.get("flags", []) or []
            )

            # ── Emergency fast-path: skip the ReAct loop + drop the long
            # tool-heavy system prompt ──
            #
            # The patient is in a crisis. We want a direct empathic answer
            # following the Emergency Playbook, NOT a multi-step tool dance
            # (which is what the regular loop produces: the LLM keeps calling
            # tools without ever emitting final text, ending up with the same
            # 0-token deflection we just fixed).
            #
            # Important: we REPLACE the long system prompt with a focused
            # emergency-only one. With the original prompt that screams
            # "MUST call tools" and tools=None, the LLM gets confused and
            # produces zero tokens. A clean targeted prompt unblocks it.
            if language == "ar":
                em_system = (
                    "أنت MedAgent — مساعد طبي إنساني. المريض في أزمة طارئة. "
                    "ردّ مباشرة على رسالته بدون أسئلة وبدون تشخيص تفريقي طويل، "
                    "متبعًا هذه البنية بالضبط:\n"
                    "١. سطر تعاطف واحد قصير.\n"
                    "٢. رقم خط النجدة المناسب:\n"
                    "   • إسعاف عام: ١٢٣ (مصر) / ٩١١ (دولي)\n"
                    "   • أزمة نفسية أو فكرة إيذاء نفس: ١٦٣٢٨ (مصر، ٢٤ ساعة، سري) / ٩٨٨ (أمريكا) / ١١٦ ١٢٣ (أوروبا)\n"
                    "   • تسمم: ١٥٩ (مصر)\n"
                    "٣. خطوة محددة آمنة يقدر يعملها في ٦٠ ثانية (مثال: لو ألم صدر "
                    "→ مضغ aspirin 300 mg لو مفيش حساسية + جلوس متكئ للأمام؛ "
                    "لو فكرة إيذاء نفس → ابعد عن أي أداة تأذيك واتصل بحد قريب).\n"
                    "٤. ايه يقول لمشغل الإسعاف لما يتصل.\n"
                    "٥. علامات تخليه يستدعي إسعاف بدل ما يروح بنفسه.\n"
                    "ممنوع: «اذهب للطوارئ» لوحدها، أسئلة follow-up، حشو طبي.\n"
                    f"السبب اللي أشّر للأزمة: {flag_summary or 'غير محدد'}"
                )
            else:
                em_system = (
                    "You are MedAgent — a compassionate medical assistant. The "
                    "patient is in an acute emergency. Reply directly to their "
                    "message WITHOUT follow-up questions and WITHOUT a long "
                    "differential, following this exact structure:\n"
                    "1. One short empathic sentence.\n"
                    "2. The right hotline:\n"
                    "   • Ambulance: 123 (EG) / 911 (intl)\n"
                    "   • Mental-health / self-harm: 16328 (EG, 24/7, confidential) / 988 (US) / 116 123 (EU)\n"
                    "   • Poison: 159 (EG)\n"
                    "3. A specific safe first action they can do in 60 seconds "
                    "(e.g. cardiac chest pain → chew aspirin 300 mg if no allergy "
                    "+ sit leaning forward; suicidal ideation → move away from "
                    "anything they could use to harm themselves + call someone they trust).\n"
                    "4. What to tell the ambulance operator on the phone.\n"
                    "5. Signs that warrant calling an ambulance instead of self-transport.\n"
                    "Forbidden: 'go to the ER' alone, follow-up questions, medical filler.\n"
                    f"Detected red flag: {flag_summary or 'unspecified'}"
                )

            em_messages = [
                {"role": "system", "content": em_system},
                {"role": "user", "content": safe_message},
            ]

            accumulated_em = ""
            async for event in self.llm.generate_stream(
                messages=em_messages,
                tools=None,  # no tools → no tool-call ping-pong
                max_tokens=512,
                temperature=0.2,
            ):
                if event["type"] == "token":
                    yield AgentEvent(type="token", content=event["content"])
                    accumulated_em += event["content"]
                elif event["type"] == "error":
                    yield AgentEvent(
                        type="error",
                        content=event.get("content", "LLM API error"),
                        data=event,
                    )
                    break
                elif event["type"] == "done":
                    break

            # Fallback safety net: if the model still produced nothing, emit
            # a hardcoded crisis card so the patient is NEVER left with an
            # empty response. This is the floor on product value.
            if not accumulated_em.strip():
                fallback = (
                    "أنا فاهم إنك بتمر بوقت صعب جدًا. اتصل دلوقتي بخط النجدة "
                    "النفسية: **١٦٣٢٨** (متاح ٢٤ ساعة، الكلام سري). لو معاك حد "
                    "قريب، خليه يقعد جنبك. ابعد عن أي حاجة قد تأذيك. أنت مش لوحدك."
                    if language == "ar"
                    else "I hear you — you're going through something really hard. "
                    "Please call **988** (US) / **116 123** (EU) / **16328** (EG) "
                    "right now. The call is free and confidential. If someone "
                    "close is nearby, ask them to sit with you. Move away from "
                    "anything you could harm yourself with. You're not alone."
                )
                for ch in fallback:
                    yield AgentEvent(type="token", content=ch)

            yield AgentEvent(type="done")
            return

        # ── Step 2: ReAct loop ──
        tools = self.registry.to_openai_schema() if self.registry.list_all() else None

        for iteration in range(MAX_ITERATIONS):
            accumulated = ""
            tool_calls = []

            async for event in self.llm.generate_stream(
                messages=messages,
                tools=tools,
                max_tokens=768,
                temperature=0.3,
            ):
                if event["type"] == "token":
                    accumulated += event["content"]

                elif event["type"] == "tool_call":
                    tool_calls.append(event)

                elif event["type"] == "error":
                    yield AgentEvent(
                        type="error",
                        content=event.get("content", "LLM API error"),
                        data=event,
                    )
                    yield AgentEvent(type="done")
                    return

                elif event["type"] == "done":
                    break

            # If the LLM called tools — the preceding text is "thinking"
            # Send it as a separate thinking event (not shown in main message)
            if tool_calls and accumulated:
                yield AgentEvent(
                    type="thinking",
                    content=accumulated,
                    data={"iteration": iteration},
                )

            # If the LLM produced a final answer (no tools), stream it as normal tokens
            if not tool_calls and accumulated:
                # Stream the final response character by character for the frontend animation
                for chunk in accumulated:
                    yield AgentEvent(type="token", content=chunk)

            # If the LLM called a tool
            if tool_calls:
                for tc in tool_calls:
                    tool_name = tc.get("name", "")
                    tool = self.registry.get(tool_name)

                    if not tool:
                        yield AgentEvent(
                            type="error",
                            content=f"Unknown tool: {tool_name}",
                        )
                        continue

                    # Parse tool arguments
                    try:
                        args_str = tc.get("args", "{}")
                        args_dict = json.loads(args_str) if isinstance(args_str, str) else args_str

                        # Inject real conversation_id for tools that need it
                        if conversation_id and tool_name in (
                            "summarize_for_doctor",
                            "format_soap",
                        ):
                            args_dict["conversation_id"] = conversation_id

                        # Validate with pydantic
                        input_obj = tool.input_schema(**args_dict)
                    except Exception as e:
                        yield AgentEvent(
                            type="error",
                            content=f"Tool args error: {e}",
                        )
                        continue

                    yield AgentEvent(
                        type="tool_start",
                        content=f"Running {tool_name}...",
                        data={"tool": tool_name},
                    )

                    # Execute tool
                    from time import perf_counter as _pc

                    _tool_start = _pc()
                    try:
                        result = await tool.run(input_obj)
                        _tool_outcome = "success"
                    except Exception as e:
                        result = {"error": str(e)}
                        _tool_outcome = "error"
                    finally:
                        try:
                            from app.core.metrics import (
                                tool_calls_total,
                                tool_duration_seconds,
                            )

                            tool_calls_total.labels(tool_name, _tool_outcome).inc()
                            tool_duration_seconds.labels(tool_name).observe(_pc() - _tool_start)
                        except Exception:
                            pass

                    yield AgentEvent(
                        type="tool_result",
                        data={"tool": tool_name, "result": result},
                    )

                    # Emit triage event from score_triage result — but only
                    # when it actually carries clinical signal. The default
                    # "No triage rules matched — recommend routine evaluation
                    # with primary care" with score 10 was leaking through to
                    # the UI on greetings ("السلام عليكم" → green Routine
                    # badge), because the LLM kept calling score_triage even
                    # after the pre-flight skipped it. (FX3)
                    if (
                        tool_name == "score_triage"
                        and isinstance(result, dict)
                        and "level" in result
                        and _triage_is_meaningful(result)
                    ):
                        yield AgentEvent(
                            type="triage",
                            data=result,
                        )

                    # Feed tool result back to LLM
                    messages.append(
                        {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": f"call_{iteration}",
                                    "type": "function",
                                    "function": {
                                        "name": tool_name,
                                        "arguments": json.dumps(args_dict),
                                    },
                                }
                            ],
                        }
                    )
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": f"call_{iteration}",
                            "content": json.dumps(result),
                        }
                    )

                    # ── Tree-of-Thought trigger ──
                    # لو أداة score_triage رجّعت urgent، نشوف لو محتاجين ToT
                    if tool_name == "score_triage" and result.get("level") == "urgent":
                        tot_tool = self.registry.get("tot_differential_diagnosis")
                        if tot_tool:
                            try:
                                symptoms, history = ToTOrchestrator.build_tot_context(
                                    messages, self.patient_age, self.patient_conditions
                                )
                                # نجمع المصادر من الرسايل (زي ما بنعمل في safety gate)
                                tot_sources = self._extract_sources(messages)
                                tot_input = tot_tool.input_schema(
                                    symptoms=symptoms,
                                    history=history,
                                    sources=tot_sources,
                                    language=language,
                                )
                                tot_result = await tot_tool.run(tot_input)

                                yield AgentEvent(
                                    type="tot_branches",
                                    data=ToTOrchestrator.format_branches_for_ui(tot_result),
                                )

                                # نغذي نتيجة ToT للـ LLM عشان ياخدها في الاعتبار
                                messages.append(
                                    {
                                        "role": "assistant",
                                        "content": None,
                                        "tool_calls": [
                                            {
                                                "id": f"call_{iteration}_tot",
                                                "type": "function",
                                                "function": {
                                                    "name": "tot_differential_diagnosis",
                                                    "arguments": json.dumps(
                                                        {"symptoms": symptoms, "language": language}
                                                    ),
                                                },
                                            }
                                        ],
                                    }
                                )
                                messages.append(
                                    {
                                        "role": "tool",
                                        "tool_call_id": f"call_{iteration}_tot",
                                        "content": json.dumps(tot_result),
                                    }
                                )
                            except Exception:
                                pass  # فشل ToT — نكمل ReAct عادي
            else:
                # LLM responded without tool calls — reply is complete
                if accumulated:
                    # Yield triage event if score_triage result is detected in messages
                    for msg in reversed(messages):
                        if msg["role"] == "tool" and "level" in msg.get("content", ""):
                            try:
                                triage_data = json.loads(msg["content"])
                                if "level" in triage_data:
                                    yield AgentEvent(
                                        type="triage",
                                        data=triage_data,
                                    )
                            except json.JSONDecodeError:
                                pass
                            break
                break

        # ── Fallback: if tools completed but no text response ──
        if not accumulated and any(msg["role"] == "tool" for msg in messages):
            # Ask the LLM one final time to produce a text summary
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "لقد أكملت التحليل باستخدام الأدوات. "
                        "الآن قم بكتابة رد مختصر ومفيد للمريض باللغة العربية يلخص النتائج والتوصيات."
                        if language == "ar"
                        else "You have completed the analysis using tools. "
                        "Now write a brief, helpful response to the patient summarizing the findings and recommendations."
                    ),
                }
            )
            try:
                async for event in self.llm.generate_stream(
                    messages=messages,
                    tools=None,  # No more tool calls allowed
                    max_tokens=512,
                    temperature=0.3,
                ):
                    if event["type"] == "token":
                        accumulated += event["content"]
                        yield AgentEvent(type="token", content=event["content"])
                    elif event["type"] == "done":
                        break
            except Exception:
                pass

        # ── Post-LLM Safety Gate (Stage 3) ──
        # بعد ما الـ Agent يخلص رده، بنمرره على بوابة الأمان
        # اللي بتدقق كل claim طبي مقابل المصادر اللي رجعها الـ RAG
        if self._safety_gate and accumulated:
            retrieved_sources = self._extract_sources(messages)
            gate_result = await self._safety_gate.check(
                assistant_text=accumulated,
                sources=retrieved_sources,
            )
            yield AgentEvent(
                type="safety",
                data={
                    "action": gate_result.action,
                    "original_text": gate_result.original_text,
                    "safe_text": gate_result.safe_text,
                    "assessment": gate_result.assessment,
                },
            )

            # لو الرد اتعدل، نبعت النص الآمن بدل الأصلي
            # (لكن التوكينز الأصلية Already اتبعتت streaming —
            #  بنضيف تصحيح هنا)
            if gate_result.action in ("rewrite", "flag"):
                yield AgentEvent(
                    type="token",
                    content="\n\n---\n⚠️ "
                    + gate_result.safe_text[len(gate_result.original_text) :].lstrip(),
                )

        yield AgentEvent(type="done")

    # ── Helper: استخراج المصادر من رسايل الـ Agent ──

    @staticmethod
    def _extract_sources(messages: list[dict]) -> list[dict[str, str]]:
        """
        يستخرج المصادر الطبية اللي رجعها الـ RAG من رسايل الأدوات.

        بيدور في messages على tool_result بتاع retrieve_medical_knowledge
        وبياخد الـ chunks اللي رجعت — كل chunk فيه title + content_excerpt.
        """
        sources: list[dict[str, str]] = []
        for msg in messages:
            if msg.get("role") != "tool":
                continue
            try:
                data = json.loads(msg.get("content", "{}"))
            except json.JSONDecodeError:
                continue
            # ناخد chunks من نتيجة retrieve_medical_knowledge
            for chunk in data.get("chunks", []):
                sources.append(
                    {
                        "title": chunk.get("title", chunk.get("source", "")),
                        "content": chunk.get("content_excerpt", chunk.get("content", "")),
                    }
                )
        return sources


# ── Small-talk + triage-meaningfulness helpers (CX5) ──

# Greetings / acknowledgements / pleasantries that should NEVER trigger triage.
# Match conservatively — only block when the message is *just* small talk,
# not when it contains a greeting plus a symptom.
_SMALL_TALK_PATTERNS_AR = (
    "السلام عليكم",
    "وعليكم السلام",
    "صباح الخير",
    "مساء الخير",
    "أهلا",
    "أهلاً",
    "مرحبا",
    "مرحباً",
    "شكرا",
    "شكراً",
    "شكرا لك",
    "تمام",
    "حسنا",
    "حسناً",
    "أيوة",
    "أيوه",
    "نعم",
    "لا",
    "لأ",
    "ماشي",
    "اوكي",
    "أوكي",
    "ok",
)

_SMALL_TALK_PATTERNS_EN = (
    "hi",
    "hello",
    "hey",
    "yes",
    "no",
    "ok",
    "okay",
    "thanks",
    "thank you",
    "good morning",
    "good evening",
    "peace",
)

# Words that strongly indicate a medical complaint — if any appear, treat as
# a real symptom message even when it's short.
_SYMPTOM_HINT_WORDS = (
    # AR
    "ألم",
    "الم",
    "وجع",
    "صداع",
    "دوخة",
    "غثيان",
    "قيء",
    "حمى",
    "حرارة",
    "سعال",
    "كحة",
    "تعب",
    "ضيق",
    "نفس",
    "صدر",
    "بطن",
    "ظهر",
    "نزيف",
    "إغماء",
    "تشنج",
    "حساسية",
    "طفح",
    "حكة",
    "إسهال",
    "إمساك",
    "حامل",
    # EN
    "pain",
    "ache",
    "headache",
    "dizzy",
    "dizziness",
    "nausea",
    "vomit",
    "fever",
    "cough",
    "tired",
    "fatigue",
    "shortness",
    "breath",
    "chest",
    "bleeding",
    "rash",
    "seizure",
    "allergy",
    "pregnant",
)


def _is_likely_symptom_message(text: str) -> bool:
    """Return True if the message looks like a real medical complaint.

    Heuristic, intentionally lossy:
    1. If any symptom-hint word is present → True (even short messages count).
    2. Else if the message is just a known greeting / yes-no → False.
    3. Else (longer free-form text) → True; let the scorer decide.
    """
    t = (text or "").strip().lower()
    if not t:
        return False
    # Symptom hints win — never skip triage when a real complaint is in there.
    if any(hint in t for hint in _SYMPTOM_HINT_WORDS):
        return True
    # Strip punctuation so "نعم." / "yes!" still match.
    stripped = "".join(c for c in t if c.isalnum() or c.isspace()).strip()
    # Exact-match the small-talk dictionary first.
    if stripped in _SMALL_TALK_PATTERNS_AR or stripped in _SMALL_TALK_PATTERNS_EN:
        return False
    # Very short messages (≤ 12 chars) that contain a greeting but nothing
    # else are also small talk.
    return not (
        len(stripped) <= 12
        and any(
            stripped.startswith(p) for p in (*_SMALL_TALK_PATTERNS_AR, *_SMALL_TALK_PATTERNS_EN)
        )
    )


# UX3: per-symptom-category watch signals — patient-facing list of red flags
# to monitor for. Kept deterministic (no LLM call) so the safety advice never
# fails to render. Lists are short on purpose; 3-4 items max so they get read.
_WATCH_SIGNALS: dict[str, dict[str, list[str]]] = {
    "headache": {
        "ar": [
            "صداع مفاجئ شديد جداً («أسوأ صداع في حياتك»)",
            "تشوش في الرؤية أو فقدان رؤية مفاجئ",
            "ضعف أو خدر في طرف من الجسم",
            "تشنج أو فقدان وعي",
            "حمى مرتفعة مع تيبس في الرقبة",
        ],
        "en": [
            "Sudden, worst-ever headache",
            "Vision changes or sudden vision loss",
            "Weakness or numbness in one side of the body",
            "Seizure or loss of consciousness",
            "High fever with neck stiffness",
        ],
    },
    "chest": {
        "ar": [
            "ألم صدر يمتد للذراع أو الفك أو الكتف",
            "ضيق تنفس شديد",
            "تعرّق بارد مع غثيان",
            "إغماء أو دوار شديد",
        ],
        "en": [
            "Chest pain radiating to arm, jaw, or shoulder",
            "Severe shortness of breath",
            "Cold sweat with nausea",
            "Fainting or severe dizziness",
        ],
    },
    "abdominal": {
        "ar": [
            "ألم بطن شديد ومفاجئ",
            "قيء دم أو براز أسود",
            "حمى مرتفعة مع ألم بطن",
            "بطن متيبسة عند اللمس",
        ],
        "en": [
            "Sudden severe abdominal pain",
            "Vomiting blood or black stools",
            "High fever with abdominal pain",
            "Rigid abdomen on touch",
        ],
    },
    "dizziness": {
        "ar": [
            "إغماء أو فقدان وعي",
            "ضعف مفاجئ في طرف من الجسم",
            "صعوبة في النطق أو فهم الكلام",
            "صداع شديد مفاجئ مع الدوخة",
        ],
        "en": [
            "Fainting or loss of consciousness",
            "Sudden weakness on one side",
            "Difficulty speaking or understanding speech",
            "Severe sudden headache with the dizziness",
        ],
    },
    "fever": {
        "ar": [
            "حمى تتجاوز ٣٩.٥°م ولا تستجيب لخافض الحرارة",
            "تيبس في الرقبة أو حساسية للضوء",
            "صعوبة تنفس أو ألم في الصدر",
            "طفح جلدي ينتشر بسرعة",
        ],
        "en": [
            "Fever > 39.5°C not responding to antipyretics",
            "Neck stiffness or light sensitivity",
            "Trouble breathing or chest pain",
            "Rapidly spreading rash",
        ],
    },
    "breath": {
        "ar": [
            "صعوبة شديدة في التنفس أو الكلام",
            "ازرقاق الشفاه أو الأظافر",
            "ألم في الصدر مصاحب",
            "تورم في الوجه أو الحلق",
        ],
        "en": [
            "Severe difficulty breathing or talking",
            "Blue lips or fingernails",
            "Associated chest pain",
            "Facial or throat swelling",
        ],
    },
}

# Keyword → category mapping. Kept conservative so we only fire when the
# message clearly involves a recognised complaint.
_WATCH_KEYWORDS: dict[str, str] = {
    # AR
    "صداع": "headache",
    "راس": "headache",
    "صدر": "chest",
    "بطن": "abdominal",
    "معدة": "abdominal",
    "دوخ": "dizziness",
    "دوار": "dizziness",
    "غثيان": "dizziness",
    "حمى": "fever",
    "حرارة": "fever",
    "سخونة": "fever",
    "نفس": "breath",
    "تنفس": "breath",
    "كحة": "breath",
    "سعال": "breath",
    # EN
    "headache": "headache",
    "head pain": "headache",
    "chest": "chest",
    "abdom": "abdominal",
    "stomach": "abdominal",
    "dizzy": "dizziness",
    "vertigo": "dizziness",
    "nausea": "dizziness",
    "fever": "fever",
    "temperature": "fever",
    "breath": "breath",
    "cough": "breath",
    "wheez": "breath",
}


def _get_watch_signals(text: str, language: str) -> list[str]:
    """Return the watch-list (red flags to monitor) for the case.

    Best-effort: matches the patient's symptom keywords against a small,
    curated map. Returns at most 5 signals from at most 2 categories — more
    than that and the patient stops reading.
    """
    if not text:
        return []
    t = text.lower()
    lang = "ar" if language == "ar" else "en"
    matched_categories: list[str] = []
    for kw, cat in _WATCH_KEYWORDS.items():
        if kw in t and cat not in matched_categories:
            matched_categories.append(cat)
        if len(matched_categories) >= 2:
            break

    signals: list[str] = []
    for cat in matched_categories:
        signals.extend(_WATCH_SIGNALS.get(cat, {}).get(lang, []))
    # Dedupe while preserving order; cap at 5.
    seen: set[str] = set()
    out: list[str] = []
    for s in signals:
        if s not in seen:
            seen.add(s)
            out.append(s)
        if len(out) >= 5:
            break
    return out


def _triage_is_meaningful(result: dict) -> bool:
    """A triage result is worth surfacing when it actually carries signal.

    The deterministic scorer returns a default "No triage rules matched —
    recommend routine evaluation with primary care" with score 10 whenever it
    couldn't anchor on anything. Showing that as a green badge for a greeting
    is anti-clinical; suppress it.
    """
    reasoning = str(result.get("reasoning") or "").lower()
    if "no triage rules matched" in reasoning:
        return False
    if result.get("red_flags"):
        return True
    try:
        score = int(result.get("score") or 0)
    except (TypeError, ValueError):
        score = 0
    if score > 15:
        return True
    return (result.get("level") or "routine") != "routine"


# ── Branch red-flag helpers (called from agent.run fast-path) ──


def _apply_pediatric_red_flags(
    ctx: "PediatricContext",
    text: str,
    result: dict,
) -> None:
    """Augment red_flag_result with pediatric-specific rules."""
    from app.ai.tools.assess_pediatric_safety import PEDIATRIC_RED_FLAGS

    text_lower = text.lower()
    for rule in PEDIATRIC_RED_FLAGS:
        if rule["age_max_months"] is not None and ctx.age_months >= rule["age_max_months"]:
            continue
        matched = [kw for kw in rule["flags"] if kw.lower() in text_lower]
        if matched:
            result["has_red_flag"] = True
            if rule["level"] == "emergency":
                result["severity"] = "emergency"
            result["flags"].append(
                {
                    "keyword": matched[0],
                    "language": "rule",
                    "level": rule["level"],
                    "branch": "pediatric",
                    "reason": rule["reason"],
                }
            )


def _apply_pregnancy_red_flags(text: str, result: dict) -> None:
    """Augment red_flag_result with OB red-flag rules."""
    from app.ai.tools.assess_pregnancy_safety import OB_RED_FLAGS

    text_lower = text.lower()
    for rule in OB_RED_FLAGS:
        all_keywords = rule["keywords_en"] + rule["keywords_ar"]
        matched = [kw for kw in all_keywords if kw.lower() in text_lower]
        if matched:
            result["has_red_flag"] = True
            if rule["level"] == "emergency":
                result["severity"] = "emergency"
            result["flags"].append(
                {
                    "keyword": matched[0],
                    "language": "rule",
                    "level": rule["level"],
                    "branch": "pregnancy",
                    "condition": rule["condition"],
                }
            )
