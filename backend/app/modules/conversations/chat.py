"""Streaming chat endpoint with MedAgent integration."""

import json
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.core.deps import get_current_user, limiter
from app.modules.conversations.schemas import ChatRequest
from app.modules.conversations.service import (
    add_message,
    get_conversation,
    get_messages,
    update_triage,
)

chat_router = APIRouter(prefix="/conversations", tags=["chat"])

_agent = None


def _create_vision_provider(
    provider_override: str | None = None,
    model_override: str | None = None,
):
    """Build a VisionProvider from settings or an explicit per-request override.

    Resolution order:
      1. ``provider_override`` argument (from ChatRequest.vision_provider)
      2. ``VISION_PROVIDER`` env (settings)
      3. Implicit default: OpenAI if OPENAI_API_KEY, else OpenRouter

    ``model_override`` (from ChatRequest.vision_model) wins over VISION_MODEL.
    Each branch picks a sensible default model when no override exists — e.g.
    Gemini needs a bare ``gemini-2.0-flash``, OpenAI needs ``gpt-4o``. Sending
    the same string to every provider was the silent-failure bug — Gemini
    would 404 on Meta/OpenAI ids, the tool fell open, and the patient saw
    "the AI didn't look at my image".

    Returns ``None`` when no usable backend is configured (provider=disabled
    or no API key available for the chosen branch).
    """
    from app.ai.llm.vision_provider import VisionProvider

    explicit = (provider_override or settings.VISION_PROVIDER or "").lower()
    configured_model = model_override or settings.VISION_MODEL  # may be None

    if explicit == "disabled":
        return None

    if explicit == "groq" and os.environ.get("GROQ_API_KEY"):
        return VisionProvider(
            base_url=os.environ.get("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
            api_key=os.environ.get("GROQ_API_KEY", ""),
            model=configured_model or "meta-llama/llama-4-scout-17b-16e-instruct",
        )

    if explicit == "gemini" and os.environ.get("GEMINI_API_KEY"):
        return VisionProvider(
            base_url=os.environ.get(
                "GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai"
            ),
            api_key=os.environ.get("GEMINI_API_KEY", ""),
            # Gemini 1.5 Flash: widest free quota — newer models (2.0/2.5)
            # often ship with `limit: 0` on a fresh API key until you opt in.
            model=configured_model or "gemini-1.5-flash",
        )

    if explicit == "openai" or (not explicit and os.environ.get("OPENAI_API_KEY")):
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if api_key:
            return VisionProvider(
                base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                api_key=api_key,
                model=configured_model or "gpt-4o",
            )

    # Explicit "openrouter" or implicit fallback when LLM_API_KEY exists.
    if explicit in {"openrouter", ""}:
        api_key = settings.LLM_API_KEY or os.environ.get("OPENROUTER_API_KEY", "")
        if api_key:
            return VisionProvider(
                base_url=settings.LLM_BASE_URL,
                api_key=api_key,
                # Default to a free model so users without paid OpenRouter
                # credits still get a working vision backend. The 72B Qwen
                # was paid-only — failing with 402 was a confusing UX.
                model=configured_model or "meta-llama/llama-3.2-11b-vision-instruct:free",
            )

    return None


def _register_vision_tool(
    registry,
    vision_provider_override: str | None = None,
    vision_model_override: str | None = None,
):
    """Register the analyze_vision tool with a configured vision provider.

    When the user picks a vision backend in the UI we re-register the tool
    against that backend for this one request instead of reusing the cached
    one. Failures are swallowed deliberately — the agent should still run
    even if vision is misconfigured.
    """
    try:
        from app.ai.tools.analyze_vision import AnalyzeVisionTool

        provider = _create_vision_provider(
            provider_override=vision_provider_override,
            model_override=vision_model_override,
        )
        registry.register(AnalyzeVisionTool(vision_provider=provider))
    except Exception:
        pass


def _build_agent(
    llm,
    vision_provider_override: str | None = None,
    vision_model_override: str | None = None,
):
    """Build a fresh MedAgent with the given LLM — mirrors _get_agent but skips DB wiring."""
    from app.ai.agent.agent import MedAgent
    from app.ai.agent.registry import ToolRegistry
    from app.ai.tools.red_flag_detector import DetectRedFlagsTool

    registry = ToolRegistry()
    registry.register(DetectRedFlagsTool())
    _register_vision_tool(registry, vision_provider_override, vision_model_override)

    # Register stateless tools (no DB required)
    try:
        from app.ai.tools.triage_scorer import ScoreTriageTool

        registry.register(ScoreTriageTool())
    except Exception:
        pass

    # The KB-grounded lookup — *the* tool that turns this from a generic
    # chatbot into a clinically-grounded assistant. Returns curated NICE/WHO
    # content for the chief complaint instead of letting the LLM guess.
    try:
        from app.ai.tools.clinical_lookup import ClinicalLookupTool

        registry.register(ClinicalLookupTool())
    except Exception:
        pass

    try:
        from app.ai.tools.medication import CheckMedicationTool

        registry.register(CheckMedicationTool())
    except Exception:
        pass

    try:
        from app.ai.tools.mental_health import ScreenMentalHealthTool

        registry.register(ScreenMentalHealthTool())
    except Exception:
        pass

    try:
        from app.ai.tools.assess_pediatric_safety import AssessPediatricSafetyTool

        registry.register(AssessPediatricSafetyTool())
    except Exception:
        pass

    try:
        from app.ai.tools.assess_pregnancy_safety import AssessPregnancySafetyTool

        registry.register(AssessPregnancySafetyTool())
    except Exception:
        pass

    try:
        from app.ai.tools.calibrate_uncertainty import CalibrateUncertaintyTool

        registry.register(CalibrateUncertaintyTool())
    except Exception:
        pass

    try:
        from app.ai.tools.doctor_summary import SummarizeForDoctorTool

        summary_tool = SummarizeForDoctorTool()
        summary_tool.set_llm(llm)
        registry.register(summary_tool)
    except Exception:
        pass

    try:
        from app.ai.tools.tot_differential_diagnosis import ToTDifferentialDiagnosisTool

        registry.register(ToTDifferentialDiagnosisTool(llm))
    except Exception:
        pass

    try:
        from app.ai.tools.format_soap import FormatSOAPTool

        registry.register(FormatSOAPTool(llm))
    except Exception:
        pass

    return MedAgent(llm=llm, registry=registry)


def _create_llm(model_override: str | None = None):
    """Factory: create LLM provider, auto-routing by model prefix.

    Prefix convention:
      groq/    → Groq (OpenAI-compatible, free tier)
      oa/      → OpenAI direct
      gemini/  → Google Gemini (OpenAI-compatible endpoint)
      hf/      → HuggingFace Inference API
      (no prefix) → OpenRouter (default)
    """
    model = model_override or settings.LLM_MODEL

    from app.ai.llm.openai_compat import OpenAICompatProvider

    # ── Groq ──
    if model.startswith("groq/"):
        actual = model.replace("groq/", "", 1)
        return OpenAICompatProvider(
            base_url=os.environ.get("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
            api_key=os.environ.get("GROQ_API_KEY", ""),
            model=actual,
        )

    # ── OpenAI direct ──
    if model.startswith("oa/"):
        actual = model.replace("oa/", "", 1)
        return OpenAICompatProvider(
            base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            api_key=os.environ.get("OPENAI_API_KEY", ""),
            model=actual,
        )
    if model.startswith("openai/"):
        actual = model.replace("openai/", "", 1)
        return OpenAICompatProvider(
            base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            api_key=os.environ.get("OPENAI_API_KEY", ""),
            model=actual,
        )

    # ── Google Gemini (OpenAI-compatible endpoint) ──
    if model.startswith("gemini/"):
        actual = model.replace("gemini/", "", 1)
        return OpenAICompatProvider(
            base_url=os.environ.get(
                "GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai"
            ),
            api_key=os.environ.get("GEMINI_API_KEY", ""),
            model=actual,
        )

    # ── HuggingFace Inference ──
    if model.startswith("hf/"):
        actual = model.replace("hf/", "", 1)
        from app.ai.llm.hf_inference import HfInferenceProvider

        return HfInferenceProvider(
            base_url=f"https://api-inference.huggingface.co/models/{actual}",
            api_key=os.environ.get("HF_API_KEY", ""),
        )

    # ── Default: OpenRouter ──
    return OpenAICompatProvider(
        base_url=settings.LLM_BASE_URL,
        api_key=settings.LLM_API_KEY,
        model=model,
    )


def _get_agent():
    """Initialize or return the singleton MedAgent with all tools wired."""
    global _agent
    if _agent is not None:
        return _agent

    from app.ai.agent.agent import MedAgent
    from app.ai.agent.registry import ToolRegistry
    from app.ai.tools.red_flag_detector import DetectRedFlagsTool

    registry = ToolRegistry()

    # Register stateless tools first
    registry.register(DetectRedFlagsTool())
    _register_vision_tool(registry)

    # Try to register tools that need external deps
    try:
        import asyncio

        from app.ai.retrieval.retriever import Retriever
        from app.ai.retrieval.vectorstore import VectorStore
        from app.ai.tools.doctor_summary import SummarizeForDoctorTool
        from app.ai.tools.retrieve_knowledge import RetrieveKnowledgeTool
        from app.ai.tools.triage_scorer import ScoreTriageTool

        llm = _create_llm()

        # Retriever needs a VectorStore with real DB session
        # For now, skip if no DB (agent will work without retrieval)
        async def _wire():
            try:
                from app.core.database import get_session

                async with get_session() as session:
                    store = VectorStore(session)
                    retriever = Retriever(store)
                    registry.register(RetrieveKnowledgeTool(retriever))
            except Exception:
                pass

        asyncio.get_event_loop().run_until_complete(_wire())

        registry.register(ScoreTriageTool())

        # ── Clinical KB lookup (NICE/WHO grounded content) ──
        try:
            from app.ai.tools.clinical_lookup import ClinicalLookupTool

            registry.register(ClinicalLookupTool())
        except Exception:
            pass

        # ── Medication checker ──
        try:
            from app.ai.tools.medication import CheckMedicationTool

            registry.register(CheckMedicationTool())
        except Exception:
            pass

        # ── Mental health screener ──
        try:
            from app.ai.tools.mental_health import ScreenMentalHealthTool

            registry.register(ScreenMentalHealthTool())
        except Exception:
            pass

        # ── Pediatric safety ──
        try:
            from app.ai.tools.assess_pediatric_safety import AssessPediatricSafetyTool

            registry.register(AssessPediatricSafetyTool())
        except Exception:
            pass

        # ── Pregnancy safety ──
        try:
            from app.ai.tools.assess_pregnancy_safety import AssessPregnancySafetyTool

            registry.register(AssessPregnancySafetyTool())
        except Exception:
            pass

        # ── Calibrate uncertainty ──
        try:
            from app.ai.tools.calibrate_uncertainty import CalibrateUncertaintyTool

            registry.register(CalibrateUncertaintyTool())
        except Exception:
            pass

        summary_tool = SummarizeForDoctorTool()
        summary_tool.set_llm(llm)
        registry.register(summary_tool)

        # ── Register ToT tool ──
        try:
            from app.ai.tools.tot_differential_diagnosis import ToTDifferentialDiagnosisTool

            tot_tool = ToTDifferentialDiagnosisTool(llm)
            registry.register(tot_tool)
        except Exception:
            pass

        # ── Register SOAP formatter ──
        try:
            from app.ai.tools.format_soap import FormatSOAPTool

            soap_tool = FormatSOAPTool(llm)
            registry.register(soap_tool)
        except Exception:
            pass

        # ── إنشاء verifier LLM للبوابة الأمان ──
        # بنستخدم نفس الموديل لكن temperature=0 للدقة (مفيش إبداع في التدقيق)
        verifier = _create_verifier() if not os.environ.get("DISABLE_SAFETY_GATE") else None

        _agent = MedAgent(llm=llm, registry=registry, verifier=verifier)
    except Exception:
        # Fallback: agent with only red-flag detector
        try:
            llm = _create_llm()
            _agent = MedAgent(llm=llm, registry=registry)
        except Exception:
            _agent = MedAgent(
                llm=_create_llm(),
                registry=registry,
            )

    return _agent


def _create_verifier():
    """
    ينشئ HallucinationVerifier — مدقق هلاوس منفصل.

    بنستخدم نفس الـ provider لكن temperature=0.
    ممكن تستخدم env var `VERIFIER_MODEL` لتحديد موديل أصغر وأسرع.
    """
    from app.ai.tools.verify_no_hallucination import HallucinationVerifier

    verifier_model = settings.VERIFIER_MODEL
    if verifier_model:
        # موديل منفصل للمدقق
        from app.ai.llm.openai_compat import OpenAICompatProvider

        verifier_llm = OpenAICompatProvider(
            base_url=settings.LLM_BASE_URL,
            api_key=settings.LLM_API_KEY,
            model=verifier_model,
        )
    else:
        # نفس الموديل الأساسي (default)
        verifier_llm = _create_llm()

    return HallucinationVerifier(verifier_llm)


@chat_router.post("/{conv_id}/chat")
@limiter.limit("20/minute")
async def chat(
    request: Request,
    conv_id: uuid.UUID,
    body: ChatRequest,
    current_user: dict = Depends(get_current_user),
):
    """Send a message and stream the agent's response via SSE."""
    user_id = uuid.UUID(current_user["sub"])
    conv = await get_conversation(conv_id, user_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Persist the attached image alongside the user message so that when the
    # patient navigates back into this conversation the picture is still
    # visible (and we can re-render the VisionResultCard without re-running
    # the model). We keep the raw data URI in extra_meta — Message.text is
    # already encrypted via Fernet, but extra_meta is plain JSON so this is
    # deliberately scoped to the attached image only.
    user_meta: dict | None = None
    if body.image_data:
        user_meta = {"image_data": body.image_data}
        if body.image_kind:
            user_meta["image_kind"] = body.image_kind
    await add_message(conv_id, role="user", content=body.message, metadata=user_meta)

    history_msgs = await get_messages(conv_id)
    history = [{"role": m.role, "content": m.text} for m in history_msgs[:-1]]

    # We rebuild a fresh agent (instead of using the cached one) whenever the
    # request carries any per-call override — either a chat-model override OR
    # a vision-provider override coming from the new VisionModelSelector. The
    # cached agent is fine for the steady-state case, but it pins one vision
    # backend at startup, so we have to rebuild to A/B test models live.
    has_chat_override = bool(body.model)
    has_vision_override = bool(body.vision_provider or body.vision_model)
    if has_chat_override or has_vision_override:
        llm = _create_llm(body.model) if has_chat_override else _create_llm()
        agent = _build_agent(
            llm,
            vision_provider_override=body.vision_provider,
            vision_model_override=body.vision_model,
        )
        # Update conversation title to show model name (only when the chat
        # model itself was switched — vision changes don't deserve a title).
        if has_chat_override and not conv.title and body.model:
            model_label = (
                body.model.replace("groq/", "")
                .replace("oa/", "")
                .replace("gemini/", "")
                .replace("hf/", "")
            )
            try:
                conv.title = model_label[:100]
                from app.core.database import get_session

                async with get_session() as session:
                    session.add(conv)
                    await session.commit()
            except Exception:
                pass
    else:
        agent = _get_agent()

    async def stream():
        assistant_content = ""
        # Collect citations from tool results for enforcement
        citation_sources: list[dict] = []
        # نتيجة بوابة الأمان (بتتملي لو الـ safety gate اشتغل)
        safety_data: dict | None = None
        # Persist non-token rich events so the conversation hydrates exactly
        # the same UI (triage badge, watch signals, ToT panel, …) when the
        # user navigates back to it. Tokens themselves are reconstructed from
        # the saved `assistant_content`, so we skip them to keep the row small.
        persisted_events: list[dict] = []

        async for event in agent.run(
            user_message=body.message,
            conversation_history=history,
            language=conv.language,
            conversation_id=str(conv_id),
            image_data=body.image_data,
            image_kind=body.image_kind,
        ):
            if event.type not in {"token", "done", "thinking"}:
                persisted_events.append(event.model_dump())
            # Collect citations from retrieve_knowledge results
            if (
                event.type == "tool_result"
                and event.data.get("tool") == "retrieve_medical_knowledge"
            ):
                result = event.data.get("result", {})
                for chunk in result.get("chunks", []):
                    citation_sources.append(
                        {
                            "source": chunk.get("source", ""),
                            "title": chunk.get("title", ""),
                            "url": chunk.get("url", ""),
                        }
                    )

            # Emit citation events alongside tokens
            if event.type == "token" and citation_sources:
                # Yield citations as a separate event type
                sse_data = json.dumps(
                    {"type": "citations", "data": {"sources": citation_sources[-3:]}}
                )
                yield f"data: {sse_data}\n\n"
                citation_sources = []  # Only send once per batch

            sse_data = json.dumps(event.model_dump())
            yield f"data: {sse_data}\n\n"

            if event.type == "token":
                assistant_content += event.content
            elif event.type == "triage":
                await update_triage(
                    conv_id,
                    level=event.data.get("level", "routine"),
                    score=event.data.get("score"),
                    red_flags=event.data.get("flags"),
                )
            elif event.type == "red_flag":
                await update_triage(
                    conv_id,
                    level="emergency",
                    red_flags=event.data.get("flags", []),
                    set_flagged=True,
                )
            elif event.type == "safety":
                # حفظ تقييم السلامة في الداتابيز بعد حفظ الرسالة
                safety_data = event.data
                yield f"data: {json.dumps({'type': 'safety', 'data': safety_data})}\n\n"

        if assistant_content:
            msg = await add_message(
                conv_id,
                role="assistant",
                content=assistant_content,
                citations=citation_sources,
                metadata=({"events": persisted_events} if persisted_events else None),
            )

            # ── حفظ تقييم السلامة ──
            if safety_data:
                await _save_safety_assessment(msg.id, safety_data)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _save_safety_assessment(message_id: uuid.UUID, safety_data: dict) -> None:
    """
    يحفظ نتيجة تقييم السلامة في جدول safety_assessments.

    بنستخدم assessment_to_db عشان نحول dict البوابة لشكل جاهز للـ INSERT.
    """
    from app.core.database import get_session
    from app.models.safety_assessment import SafetyAssessment

    assessment = safety_data.get("assessment", {})
    db_data = SafetyAssessment(
        message_id=message_id,
        hallucination_score=assessment.get("hallucination_score"),
        citation_completeness=assessment.get("citation_completeness"),
        calibration_metadata=assessment.get("claims"),
        triage_consistent=True,
    )

    try:
        async with get_session() as session:
            session.add(db_data)
            await session.commit()
    except Exception:
        # Fail silently — مش هنوقف الـ request بسبب فشل حفظ التقييم
        # الـ assessment بيكون already اتبعت للـ frontend في الـ SSE
        pass
