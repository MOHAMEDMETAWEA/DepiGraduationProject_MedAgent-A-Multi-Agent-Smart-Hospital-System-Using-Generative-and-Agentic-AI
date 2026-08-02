"""Tests for T2.13 (analyze_vision) and T2.16 (pediatric/pregnancy safety tools)."""

import base64
import struct
import zlib

import pytest
from app.ai.agent.agent import _apply_pediatric_red_flags, _apply_pregnancy_red_flags
from app.ai.agent.branches.pediatric import PediatricContext
from app.ai.agent.branches.pregnancy import PregnancyContext
from app.ai.llm.vision_provider import (
    DISCLAIMER_AR,
    DISCLAIMER_EN,
    _parse_vision_response,
    validate_image,
)
from app.ai.tools.analyze_vision import AnalyzeVisionTool, VisionInput
from app.ai.tools.assess_pediatric_safety import (
    AssessPediatricSafetyTool,
    PediatricSafetyInput,
)
from app.ai.tools.assess_pregnancy_safety import (
    AssessPregnancySafetyTool,
    PregnancySafetyInput,
)

# ─────────────────────────────────────────────
# Helpers — minimal valid image bytes
# ─────────────────────────────────────────────


def _minimal_jpeg() -> bytes:
    """Return a 1×1 pixel white JPEG."""
    return bytes(
        [
            0xFF,
            0xD8,
            0xFF,
            0xE0,
            0x00,
            0x10,
            0x4A,
            0x46,
            0x49,
            0x46,
            0x00,
            0x01,
            0x01,
            0x00,
            0x00,
            0x01,
            0x00,
            0x01,
            0x00,
            0x00,
            0xFF,
            0xDB,
            0x00,
            0x43,
            0x00,
            0x08,
            0x06,
            0x06,
            0x07,
            0x06,
            0x05,
            0x08,
            0x07,
            0x07,
            0x07,
            0x09,
            0x09,
            0x08,
            0x0A,
            0x0C,
            0x14,
            0x0D,
            0x0C,
            0x0B,
            0x0B,
            0x0C,
            0x19,
            0x12,
            0x13,
            0x0F,
            0x14,
            0x1D,
            0x1A,
            0x1F,
            0x1E,
            0x1D,
            0x1A,
            0x1C,
            0x1C,
            0x20,
            0x24,
            0x2E,
            0x27,
            0x20,
            0x22,
            0x2C,
            0x23,
            0x1C,
            0x1C,
            0x28,
            0x37,
            0x29,
            0x2C,
            0x30,
            0x31,
            0x34,
            0x34,
            0x34,
            0x1F,
            0x27,
            0x39,
            0x3D,
            0x38,
            0x32,
            0x3C,
            0x2E,
            0x33,
            0x34,
            0x32,
            0xFF,
            0xC0,
            0x00,
            0x0B,
            0x08,
            0x00,
            0x01,
            0x00,
            0x01,
            0x01,
            0x01,
            0x11,
            0x00,
            0xFF,
            0xC4,
            0x00,
            0x1F,
            0x00,
            0x00,
            0x01,
            0x05,
            0x01,
            0x01,
            0x01,
            0x01,
            0x01,
            0x01,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x01,
            0x02,
            0x03,
            0x04,
            0x05,
            0x06,
            0x07,
            0x08,
            0x09,
            0x0A,
            0x0B,
            0xFF,
            0xC4,
            0x00,
            0xB5,
            0x10,
            0x00,
            0x02,
            0x01,
            0x03,
            0x03,
            0x02,
            0x04,
            0x03,
            0x05,
            0x05,
            0x04,
            0x04,
            0x00,
            0x00,
            0x01,
            0x7D,
            0xFF,
            0xDA,
            0x00,
            0x08,
            0x01,
            0x01,
            0x00,
            0x00,
            0x3F,
            0x00,
            0xFB,
            0xD2,
            0x8A,
            0x28,
            0x03,
            0xFF,
            0xD9,
        ]
    )


def _minimal_png() -> bytes:
    """Return a 1×1 red pixel PNG."""

    def pack_chunk(chunk_type: bytes, data: bytes) -> bytes:
        c = chunk_type + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = pack_chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    raw = b"\x00\xff\x00\x00"  # filter byte + RGB
    idat = pack_chunk(b"IDAT", zlib.compress(raw))
    iend = pack_chunk(b"IEND", b"")
    return sig + ihdr + idat + iend


# ─────────────────────────────────────────────
# T2.13 — VisionProvider helpers
# ─────────────────────────────────────────────


class TestValidateImage:
    def test_accepts_jpeg(self):
        mime = validate_image(_minimal_jpeg())
        assert mime == "image/jpeg"

    def test_accepts_png(self):
        mime = validate_image(_minimal_png())
        assert mime == "image/png"

    def test_rejects_oversized(self):
        big = b"\xff\xd8" + b"\x00" * (11 * 1024 * 1024)
        with pytest.raises(ValueError, match="too large"):
            validate_image(big)

    def test_rejects_unknown_format(self):
        with pytest.raises(ValueError, match="Unsupported"):
            validate_image(b"not an image at all")


class TestParseVisionResponse:
    def test_parses_json(self):
        raw = '{"findings": ["consolidation in left lower lobe"], "urgency": "urgent", "confidence": 0.7, "is_medical": true}'
        result = _parse_vision_response(raw, "xray", DISCLAIMER_EN)
        assert result["urgency"] == "urgent"
        assert result["confidence"] == 0.7
        assert "consolidation" in result["findings"][0]
        assert result["disclaimer"] == DISCLAIMER_EN

    def test_parses_json_in_markdown_fence(self):
        raw = '```json\n{"findings": ["rash"], "urgency": "routine", "confidence": 0.5, "is_medical": true}\n```'
        result = _parse_vision_response(raw, "skin", DISCLAIMER_EN)
        assert result["urgency"] == "routine"

    def test_non_medical_refusal(self):
        result = _parse_vision_response("NON_MEDICAL this is a cat photo", "photo", DISCLAIMER_EN)
        assert result["is_medical"] is False
        assert "refusal_reason" in result
        assert result["urgency"] == "none"

    def test_arabic_disclaimer(self):
        raw = '{"findings": [], "urgency": "routine", "confidence": 0.1, "is_medical": true}'
        result = _parse_vision_response(raw, "other", DISCLAIMER_AR)
        assert result["disclaimer"] == DISCLAIMER_AR

    def test_fallback_on_bad_json(self):
        result = _parse_vision_response("Some plain text analysis", "photo", DISCLAIMER_EN)
        assert result["confidence"] == 0.3
        assert result["findings"][0] == "Some plain text analysis"


class TestAnalyzeVisionTool:
    def test_tool_name_and_schema(self):
        tool = AnalyzeVisionTool()
        assert tool.name == "analyze_vision"
        assert tool.input_schema == VisionInput

    @pytest.mark.asyncio(loop_scope="session")
    async def test_returns_disclaimer_always(self):
        tool = AnalyzeVisionTool()
        png_b64 = "data:image/png;base64," + base64.b64encode(_minimal_png()).decode()
        result = await tool.run(VisionInput(image_url=png_b64, language="en"))
        assert "disclaimer" in result
        assert result["disclaimer"] == DISCLAIMER_EN

    @pytest.mark.asyncio(loop_scope="session")
    async def test_arabic_disclaimer(self):
        tool = AnalyzeVisionTool()
        png_b64 = "data:image/png;base64," + base64.b64encode(_minimal_png()).decode()
        result = await tool.run(VisionInput(image_url=png_b64, language="ar"))
        assert result["disclaimer"] == DISCLAIMER_AR

    @pytest.mark.asyncio(loop_scope="session")
    async def test_invalid_url_returns_error(self):
        tool = AnalyzeVisionTool()
        result = await tool.run(VisionInput(image_url="not-a-url"))
        assert "error" in result

    @pytest.mark.asyncio(loop_scope="session")
    async def test_invalid_base64_returns_error(self):
        tool = AnalyzeVisionTool()
        result = await tool.run(VisionInput(image_url="data:image/jpeg;base64,NOTVALIDBASE64!!!"))
        assert "error" in result

    @pytest.mark.asyncio(loop_scope="session")
    async def test_no_llm_returns_graceful_message(self):
        tool = AnalyzeVisionTool(vision_provider=None)
        png_b64 = "data:image/png;base64," + base64.b64encode(_minimal_png()).decode()
        result = await tool.run(VisionInput(image_url=png_b64))
        assert "findings" in result
        assert isinstance(result["findings"], list)


# ─────────────────────────────────────────────
# T2.16 — Pediatric Safety Tool
# ─────────────────────────────────────────────


class TestAssessPediatricSafetyTool:
    def test_tool_name(self):
        assert AssessPediatricSafetyTool().name == "assess_pediatric_safety"

    @pytest.mark.asyncio(loop_scope="session")
    async def test_fever_young_infant_emergency(self):
        """Infant 2 months with fever → emergency."""
        tool = AssessPediatricSafetyTool()
        result = await tool.run(
            PediatricSafetyInput(
                age_months=2.0,
                symptoms=["fever", "temperature 38.5"],
            )
        )
        assert result["triage_level"] == "emergency"
        assert result["has_red_flags"] is True

    @pytest.mark.asyncio(loop_scope="session")
    async def test_seizure_any_age_emergency(self):
        """Seizure in any child → emergency."""
        tool = AssessPediatricSafetyTool()
        result = await tool.run(
            PediatricSafetyInput(
                age_months=36.0,
                symptoms=["seizure", "convulsion"],
            )
        )
        assert result["triage_level"] == "emergency"

    @pytest.mark.asyncio(loop_scope="session")
    async def test_no_red_flags_routine(self):
        tool = AssessPediatricSafetyTool()
        result = await tool.run(
            PediatricSafetyInput(
                age_months=48.0,
                symptoms=["mild cold", "runny nose"],
            )
        )
        assert result["triage_level"] == "routine"
        assert result["has_red_flags"] is False

    @pytest.mark.asyncio(loop_scope="session")
    async def test_dose_calculation_paracetamol(self):
        """10 kg child → paracetamol 15 mg/kg = 150 mg."""
        tool = AssessPediatricSafetyTool()
        result = await tool.run(
            PediatricSafetyInput(
                age_months=24.0,
                weight_kg=10.0,
                medications=["paracetamol"],
            )
        )
        doses = {d["generic"]: d for d in result["dose_assessments"]}
        assert "paracetamol" in doses
        assert doses["paracetamol"]["calculated_dose_mg"] == 150.0

    @pytest.mark.asyncio(loop_scope="session")
    async def test_ibuprofen_under_6_months_unsafe(self):
        """Ibuprofen for 4-month-old → unsafe (age restriction)."""
        tool = AssessPediatricSafetyTool()
        result = await tool.run(
            PediatricSafetyInput(
                age_months=4.0,
                medications=["ibuprofen"],
            )
        )
        doses = {d["generic"]: d for d in result["dose_assessments"]}
        assert doses["ibuprofen"]["safe"] is False

    @pytest.mark.asyncio(loop_scope="session")
    async def test_arabic_symptoms(self):
        """Arabic red flag keywords detected."""
        tool = AssessPediatricSafetyTool()
        result = await tool.run(
            PediatricSafetyInput(
                age_months=2.0,
                symptoms=["حرارة", "سخونية"],
                language="ar",
            )
        )
        assert result["triage_level"] == "emergency"

    @pytest.mark.asyncio(loop_scope="session")
    async def test_brand_alias_resolution(self):
        """Brand name 'بنادول' resolves to paracetamol."""
        tool = AssessPediatricSafetyTool()
        result = await tool.run(
            PediatricSafetyInput(
                age_months=24.0,
                weight_kg=12.0,
                medications=["بنادول"],
            )
        )
        assert result["dose_assessments"][0]["generic"] == "paracetamol"


# 20 gold-set pediatric cases — triage level assertions
PEDIATRIC_GOLD: list[tuple[float, list[str], str]] = [
    (1.0, ["fever"], "emergency"),  # 1mo infant + fever
    (2.0, ["temperature 38"], "emergency"),  # 2mo + temperature
    (0.5, ["won't eat", "lethargic"], "emergency"),  # neonate + poor feeding
    (6.0, ["seizure"], "emergency"),  # seizure any age
    (12.0, ["blue lips"], "emergency"),  # cyanosis
    (18.0, ["neck stiffness", "rash"], "emergency"),
    (24.0, ["not breathing"], "emergency"),
    (36.0, ["floppy"], "emergency"),
    (48.0, ["sunken eyes", "no wet diapers"], "emergency"),
    (60.0, ["non-blanching rash"], "emergency"),
    # Routine cases
    (24.0, ["mild cold"], "routine"),
    (36.0, ["runny nose"], "routine"),
    (48.0, ["mild cough"], "routine"),
    (60.0, ["slight temperature"], "routine"),
    (72.0, ["skin rash mild"], "routine"),
    (84.0, ["stomach ache mild"], "routine"),
    (96.0, ["sore throat"], "routine"),
    (108.0, ["headache mild"], "routine"),
    (120.0, ["ear pain"], "routine"),
    (144.0, ["nausea"], "routine"),
]


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize("age_months,symptoms,expected", PEDIATRIC_GOLD)
async def test_pediatric_gold_set(age_months, symptoms, expected):
    tool = AssessPediatricSafetyTool()
    result = await tool.run(PediatricSafetyInput(age_months=age_months, symptoms=symptoms))
    assert result["triage_level"] == expected, (
        f"age={age_months}mo, symptoms={symptoms}: "
        f"got {result['triage_level']}, expected {expected}"
    )


# ─────────────────────────────────────────────
# T2.16 — Pregnancy Safety Tool
# ─────────────────────────────────────────────


class TestAssessPregnancySafetyTool:
    def test_tool_name(self):
        assert AssessPregnancySafetyTool().name == "assess_pregnancy_safety"

    @pytest.mark.asyncio(loop_scope="session")
    async def test_severe_headache_vision_change_emergency(self):
        """Pre-eclampsia signs → emergency."""
        tool = AssessPregnancySafetyTool()
        result = await tool.run(
            PregnancySafetyInput(
                symptoms=["severe headache", "vision changes"],
            )
        )
        assert result["triage_level"] == "emergency"
        assert result["has_red_flags"] is True

    @pytest.mark.asyncio(loop_scope="session")
    async def test_heavy_bleeding_emergency(self):
        tool = AssessPregnancySafetyTool()
        result = await tool.run(
            PregnancySafetyInput(
                symptoms=["heavy vaginal bleeding"],
            )
        )
        assert result["triage_level"] == "emergency"

    @pytest.mark.asyncio(loop_scope="session")
    async def test_decreased_fetal_movement_emergency(self):
        tool = AssessPregnancySafetyTool()
        result = await tool.run(
            PregnancySafetyInput(
                symptoms=["decreased fetal movement", "baby not moving"],
            )
        )
        assert result["triage_level"] == "emergency"

    @pytest.mark.asyncio(loop_scope="session")
    async def test_ibuprofen_category_d_warning(self):
        """Ibuprofen → category D → contraindicated."""
        tool = AssessPregnancySafetyTool()
        result = await tool.run(
            PregnancySafetyInput(
                medications=["ibuprofen"],
            )
        )
        drug = next(d for d in result["drug_warnings"] if d["generic"] == "ibuprofen")
        assert drug["fda_pregnancy_category"] == "D"
        assert drug["contraindicated"] is True

    @pytest.mark.asyncio(loop_scope="session")
    async def test_warfarin_category_x(self):
        tool = AssessPregnancySafetyTool()
        result = await tool.run(PregnancySafetyInput(medications=["warfarin"]))
        drug = result["drug_warnings"][0]
        assert drug["fda_pregnancy_category"] == "X"
        assert drug["contraindicated"] is True

    @pytest.mark.asyncio(loop_scope="session")
    async def test_paracetamol_safe_category_b(self):
        tool = AssessPregnancySafetyTool()
        result = await tool.run(PregnancySafetyInput(medications=["paracetamol"]))
        drug = result["drug_warnings"][0]
        assert drug["fda_pregnancy_category"] == "B"
        assert drug["contraindicated"] is False

    @pytest.mark.asyncio(loop_scope="session")
    async def test_third_trimester_nsaid_note(self):
        """NSAID in trimester 3 → extra trimester_note."""
        tool = AssessPregnancySafetyTool()
        result = await tool.run(
            PregnancySafetyInput(
                medications=["ibuprofen"],
                trimester=3,
            )
        )
        drug = next(d for d in result["drug_warnings"] if d["generic"] == "ibuprofen")
        assert "trimester_note" in drug

    @pytest.mark.asyncio(loop_scope="session")
    async def test_arabic_symptoms(self):
        tool = AssessPregnancySafetyTool()
        result = await tool.run(
            PregnancySafetyInput(
                symptoms=["نزيف شديد"],
                language="ar",
            )
        )
        assert result["triage_level"] == "emergency"

    @pytest.mark.asyncio(loop_scope="session")
    async def test_crisis_resources_present_on_emergency(self):
        tool = AssessPregnancySafetyTool()
        result = await tool.run(
            PregnancySafetyInput(
                symptoms=["severe headache", "vision changes"],
            )
        )
        assert result["crisis_resources"] is not None
        assert "hotline" in result["crisis_resources"]

    @pytest.mark.asyncio(loop_scope="session")
    async def test_no_red_flags_routine(self):
        tool = AssessPregnancySafetyTool()
        result = await tool.run(
            PregnancySafetyInput(
                symptoms=["mild backache"],
            )
        )
        assert result["triage_level"] == "routine"


# 15 pregnancy gold-set cases
PREGNANCY_GOLD: list[tuple[list[str], list[str], str]] = [
    (["severe headache", "vision changes"], [], "emergency"),
    (["heavy bleeding"], [], "emergency"),
    (["decreased fetal movement"], [], "emergency"),
    (["severe abdominal pain"], [], "emergency"),
    (["water broke"], [], "urgent"),
    (["contractions"], [], "urgent"),
    (["fever", "burning urination"], [], "urgent"),
    (["shortness of breath", "chest pain"], [], "emergency"),
    # Drug-only cases — triage stays routine unless symptoms
    ([], ["warfarin"], "routine"),
    ([], ["ibuprofen"], "routine"),
    ([], ["paracetamol"], "routine"),
    # Arabic
    (["صداع شديد", "تغير في النظر"], [], "emergency"),
    (["نزيف شديد"], [], "emergency"),
    (["قلة حركة الجنين"], [], "emergency"),
    (["تقلصات منتظمة"], [], "urgent"),
]


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize("symptoms,meds,expected", PREGNANCY_GOLD)
async def test_pregnancy_gold_set(symptoms, meds, expected):
    tool = AssessPregnancySafetyTool()
    result = await tool.run(PregnancySafetyInput(symptoms=symptoms, medications=meds))
    assert result["triage_level"] == expected, (
        f"symptoms={symptoms}: got {result['triage_level']}, expected {expected}"
    )


# ─────────────────────────────────────────────
# T2.16 — Branch contexts
# ─────────────────────────────────────────────


class TestPediatricContext:
    def test_from_age_years_child(self):
        ctx = PediatricContext.from_age_years(5)
        assert ctx is not None
        assert ctx.age_months == 60.0

    def test_from_age_years_adult_returns_none(self):
        assert PediatricContext.from_age_years(20) is None

    def test_is_young_infant(self):
        ctx = PediatricContext(age_months=2.0)
        assert ctx.is_young_infant is True
        assert ctx.is_infant is True

    def test_is_not_young_infant(self):
        ctx = PediatricContext(age_months=6.0)
        assert ctx.is_young_infant is False

    def test_system_prompt_key(self):
        ctx = PediatricContext(age_months=12.0)
        assert ctx.system_prompt_key("en") == "en_pediatric"
        assert ctx.system_prompt_key("ar") == "ar_pediatric"


class TestPregnancyContext:
    def test_detect_from_english_text(self):
        ctx = PregnancyContext.detect_from_text("I am 28 weeks pregnant")
        assert ctx is not None
        assert ctx.trimester == 3

    def test_detect_from_arabic_text(self):
        ctx = PregnancyContext.detect_from_text("أنا حامل في الشهر السابع")
        assert ctx is not None

    def test_no_match_returns_none(self):
        ctx = PregnancyContext.detect_from_text("I have a headache")
        assert ctx is None

    def test_first_trimester_detection(self):
        ctx = PregnancyContext.detect_from_text("I am 8 weeks pregnant")
        assert ctx is not None
        assert ctx.trimester == 1

    def test_system_prompt_key(self):
        ctx = PregnancyContext(trimester=2)
        assert ctx.system_prompt_key("en") == "en_pregnancy"
        assert ctx.system_prompt_key("ar") == "ar_pregnancy"


# ─────────────────────────────────────────────
# T2.16 — Agent branch integration
# ─────────────────────────────────────────────


class TestAgentBranchHelpers:
    def test_apply_pediatric_red_flags_infant_fever(self):
        ctx = PediatricContext(age_months=2.0)
        result = {"has_red_flag": False, "severity": "routine", "flags": []}
        _apply_pediatric_red_flags(ctx, "my baby has fever", result)
        assert result["has_red_flag"] is True
        assert result["severity"] == "emergency"

    def test_apply_pediatric_red_flags_no_match(self):
        ctx = PediatricContext(age_months=48.0)
        result = {"has_red_flag": False, "severity": "routine", "flags": []}
        _apply_pediatric_red_flags(ctx, "mild cold runny nose", result)
        assert result["has_red_flag"] is False

    def test_apply_pregnancy_red_flags_heavy_bleeding(self):
        result = {"has_red_flag": False, "severity": "routine", "flags": []}
        _apply_pregnancy_red_flags("I have heavy vaginal bleeding", result)
        assert result["has_red_flag"] is True
        assert result["severity"] == "emergency"

    def test_apply_pregnancy_red_flags_no_match(self):
        result = {"has_red_flag": False, "severity": "routine", "flags": []}
        _apply_pregnancy_red_flags("I have mild back pain", result)
        assert result["has_red_flag"] is False


# ─────────────────────────────────────────────
# Agent integration — image attachment forces analyze_vision
# ─────────────────────────────────────────────


class TestAgentVisionWiring:
    @pytest.mark.asyncio(loop_scope="session")
    async def test_agent_forces_analyze_vision_when_image_attached(self):
        """When image_data is passed to agent.run(), it must call analyze_vision
        and emit tool_start + tool_result events even without the LLM asking for it."""
        from app.ai.agent.agent import MedAgent
        from app.ai.agent.registry import ToolRegistry
        from app.ai.tools.analyze_vision import AnalyzeVisionTool

        # Stub LLM that just emits a final text token so the loop terminates.
        class _StubLLM:
            async def generate_stream(self, **kwargs):
                yield {"type": "token", "content": "Image reviewed."}
                yield {"type": "done"}

        registry = ToolRegistry()
        registry.register(AnalyzeVisionTool(vision_provider=None))

        agent = MedAgent(llm=_StubLLM(), registry=registry)
        png_b64 = "data:image/png;base64," + base64.b64encode(_minimal_png()).decode()

        events = []
        async for ev in agent.run(
            user_message="check this image",
            language="en",
            image_data=png_b64,
            image_kind="skin",
        ):
            events.append(ev)

        types = [e.type for e in events]
        # Must see tool_start + tool_result for analyze_vision
        assert "tool_start" in types
        assert "tool_result" in types
        tool_results = [e for e in events if e.type == "tool_result"]
        assert any(e.data.get("tool") == "analyze_vision" for e in tool_results)
        # The forced-vision result must include disclaimer
        vision_result = next(
            e.data["result"] for e in tool_results if e.data.get("tool") == "analyze_vision"
        )
        assert "disclaimer" in vision_result

    @pytest.mark.asyncio(loop_scope="session")
    async def test_agent_no_image_does_not_call_analyze_vision(self):
        """Without image_data, analyze_vision must not be auto-invoked."""
        from app.ai.agent.agent import MedAgent
        from app.ai.agent.registry import ToolRegistry
        from app.ai.tools.analyze_vision import AnalyzeVisionTool

        class _StubLLM:
            async def generate_stream(self, **kwargs):
                yield {"type": "token", "content": "Hi."}
                yield {"type": "done"}

        registry = ToolRegistry()
        registry.register(AnalyzeVisionTool(vision_provider=None))
        agent = MedAgent(llm=_StubLLM(), registry=registry)

        events = []
        async for ev in agent.run(user_message="hello", language="en"):
            events.append(ev)

        tool_results = [e for e in events if e.type == "tool_result"]
        assert not any(e.data.get("tool") == "analyze_vision" for e in tool_results)
