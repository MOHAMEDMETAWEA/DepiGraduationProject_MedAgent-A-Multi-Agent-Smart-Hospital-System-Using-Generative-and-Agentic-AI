"""Clinical knowledge-base loader.

Loads every YAML file under ``chief_complaints/``, ``formulary/``, and
``specialties/`` once at startup, validates each against the typed pydantic
schemas in :mod:`schemas`, and exposes a small read-only API the rest of
the agent uses to find clinical content by symptom text or by id.

The whole point: this lets a clinician edit the YAML files at runtime and
the engine picks them up on next reload — no Python changes, no migrations.
"""

from __future__ import annotations

import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.clinical.schemas import (
    ChiefComplaint,
    Drug,
    SpecialtyTemplate,
)

logger = logging.getLogger(__name__)

CLINICAL_DIR = Path(__file__).parent


# ── Loaders ────────────────────────────────────────────────────────────


def _load_yaml(path: Path) -> dict[str, Any]:
    """Read a single YAML file. We do *no* error handling here — a malformed
    file should crash startup so we notice instead of shipping broken
    clinical content."""
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_chief_complaints() -> dict[str, ChiefComplaint]:
    """Load and validate every chief-complaint YAML.

    Filename (without ``.yaml``) must match the ``id`` field — that
    invariant lets us route URLs / API ids directly to file paths.
    """
    out: dict[str, ChiefComplaint] = {}
    src = CLINICAL_DIR / "chief_complaints"
    for path in sorted(src.glob("*.yaml")):
        try:
            data = _load_yaml(path)
            cc = ChiefComplaint.model_validate(data)
        except Exception as exc:
            logger.exception("Failed to load chief complaint %s", path.name)
            raise RuntimeError(f"Clinical KB load failed for {path.name}: {exc}") from exc
        if cc.id != path.stem:
            raise RuntimeError(f"{path.name}: id={cc.id!r} doesn't match filename {path.stem!r}")
        out[cc.id] = cc
    return out


def _load_drugs() -> dict[str, Drug]:
    """Load the (currently single) formulary file and index by drug id."""
    out: dict[str, Drug] = {}
    src = CLINICAL_DIR / "formulary"
    for path in sorted(src.glob("*.yaml")):
        try:
            payload = _load_yaml(path) or {}
            drugs = payload.get("drugs", [])
            for drug_data in drugs:
                drug = Drug.model_validate(drug_data)
                out[drug.id] = drug
        except Exception as exc:
            logger.exception("Failed to load formulary %s", path.name)
            raise RuntimeError(f"Drug formulary load failed for {path.name}: {exc}") from exc
    return out


def _load_specialties() -> dict[str, SpecialtyTemplate]:
    """Load every specialty intake template."""
    out: dict[str, SpecialtyTemplate] = {}
    src = CLINICAL_DIR / "specialties"
    for path in sorted(src.glob("*.yaml")):
        try:
            data = _load_yaml(path)
            sp = SpecialtyTemplate.model_validate(data)
        except Exception as exc:
            logger.exception("Failed to load specialty %s", path.name)
            raise RuntimeError(f"Specialty template load failed for {path.name}: {exc}") from exc
        out[sp.id] = sp
    return out


# ── Public API ─────────────────────────────────────────────────────────


class ClinicalKB:
    """In-memory clinical KB. Singleton; survives the process lifetime.

    Build once at startup via :func:`get_kb`; the lru_cache there gives
    us free reload-safety in dev (uvicorn reloads the module → cache
    invalidates → next call rebuilds the index).
    """

    def __init__(self) -> None:
        self.complaints: dict[str, ChiefComplaint] = _load_chief_complaints()
        self.drugs: dict[str, Drug] = _load_drugs()
        self.specialties: dict[str, SpecialtyTemplate] = _load_specialties()

        # Pre-build a lowercased synonym → complaint_id map so symptom
        # text lookups are O(n_synonyms). It's tiny (~100 entries) so we
        # don't need anything fancier than a dict.
        self._synonym_index: dict[str, str] = {}
        for cc in self.complaints.values():
            for syn in [*cc.synonyms, cc.name.ar, cc.name.en]:
                key = _normalize(syn)
                if key:
                    self._synonym_index[key] = cc.id

    # ── Chief complaint lookup ──────────────────────────────────────

    def find_complaint(self, symptom_text: str) -> ChiefComplaint | None:
        """Match free-form patient text to a chief complaint by synonym.

        We use a tiered match — exact (whole phrase) before partial (any
        synonym appears as a substring of the user text). That way a
        message like "صداع شديد جدًا" still maps to ``headache`` via
        the "صداع" partial match without false-positive on something
        long like "صدري وراسي" which contains neither.
        """
        if not symptom_text:
            return None
        norm = _normalize(symptom_text)

        # 1. Whole-string match (rare but cheap)
        if norm in self._synonym_index:
            return self.complaints[self._synonym_index[norm]]

        # 2. Partial: does any synonym appear as a token / substring?
        # Score by length of synonym so "chest pain" beats "pain" alone.
        best: tuple[int, str] | None = None
        for syn_key, complaint_id in self._synonym_index.items():
            if syn_key in norm:
                score = len(syn_key)
                if best is None or score > best[0]:
                    best = (score, complaint_id)
        if best:
            return self.complaints[best[1]]
        return None

    def get_complaint(self, complaint_id: str) -> ChiefComplaint | None:
        return self.complaints.get(complaint_id)

    def list_complaints(self) -> list[ChiefComplaint]:
        return list(self.complaints.values())

    # ── Drug lookup ─────────────────────────────────────────────────

    def get_drug(self, drug_id: str) -> Drug | None:
        return self.drugs.get(drug_id)

    def list_drugs(self) -> list[Drug]:
        return list(self.drugs.values())

    # ── Specialty templates ─────────────────────────────────────────

    def get_specialty(self, specialty_id: str) -> SpecialtyTemplate | None:
        return self.specialties.get(specialty_id)

    def list_specialties(self) -> list[SpecialtyTemplate]:
        return list(self.specialties.values())


def _normalize(text: str) -> str:
    """Lowercase + collapse whitespace + strip Arabic diacritics.

    The synonyms YAML uses bare unaccented Arabic, but patients type
    with random diacritics and extra spaces. Strip them all before
    indexing so the match isn't fragile.
    """
    if not text:
        return ""
    text = text.strip().lower()
    text = re.sub(r"\s+", " ", text)
    # Arabic diacritics (tashkeel) range
    text = re.sub(r"[ً-ْٰ]", "", text)
    # Normalize Arabic letter variants
    text = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    text = text.replace("ى", "ي").replace("ة", "ه")
    return text


@lru_cache(maxsize=1)
def get_kb() -> ClinicalKB:
    """Singleton accessor — call this everywhere. The lru_cache makes it
    cheap and reload-safe in dev (changes to YAML are picked up after
    uvicorn restarts the worker)."""
    return ClinicalKB()
