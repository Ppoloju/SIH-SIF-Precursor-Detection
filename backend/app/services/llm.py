"""Optional LLM assistance layer (Llama via Groq).

Design rules:
  * Never required — if GROQ_API_KEY is missing, the module returns None.
  * Output is validated with Pydantic before it is trusted.
  * On any failure (timeout, invalid JSON, bad model) we fall back to the
    deterministic result and surface `llm_unavailable=True` instead of
    crashing the pipeline.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.config import get_settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a safety-data assistant for a Serious Injury & Fatality (SIF) "
    "precursor detection prototype. You refine structured extraction produced "
    "by deterministic rules. Ground every claim in the report text. Never invent "
    "evidence. Return only valid JSON matching the requested schema. "
    "If the report text is in Hindi, Bengali or Assamese, write the explanation, "
    "summary and suggested actions in that same language (keep technical terms "
    "like Life-Saving-Rule names in English)."
)


class LlmRefinement(BaseModel):
    """Validated subset of the analysis an LLM may refine."""

    explanation: str | None = Field(default=None, description="Plain-language explanation grounded in the report")
    recommended_follow_up: str | None = Field(default=None, description="Concrete HSE follow-up action")
    summary: str | None = Field(default=None, description="Three short plain-language paragraphs: what happened / why it matters / next step")
    suggested_actions: list[str] | None = Field(default=None, description="Concrete corrective actions checklist")
    activity: str | None = Field(default=None, description="Activity name or null if not stated")
    location: str | None = Field(default=None, description="Location or null if not stated")
    hazard: str | None = Field(default=None, description="Dominant hazard or null if unclear")
    barrier_failure: list[str] | None = Field(default=None, description="Failed/missing barriers or empty list")
    equipment: list[str] | None = Field(default=None, description="Equipment mentioned or empty list")
    uncertainty_note: str | None = Field(default=None, description="Honest note when the model is uncertain")


def refine_with_llm(report_text: str, base: dict[str, Any]) -> LlmRefinement | None:
    """Try to refine the deterministic analysis with an LLM.

    Returns None (safe fallback) whenever the LLM is unavailable or its
    output fails validation.
    """
    settings = get_settings()
    if not settings.groq_api_key:
        return None

    try:
        from groq import Groq  # optional dependency
    except ImportError:
        logger.info("groq package not installed — skipping LLM refinement")
        return None

    prompt = (
        f"Report text:\n{report_text[:4000]}\n\n"
        "Deterministic analysis (verify, do not contradict):\n"
        f"{base}\n\n"
        "Return JSON: {\"explanation\": str|null, \"recommended_follow_up\": str|null, "
        "\"summary\": str|null, \"suggested_actions\": [str], "
        "\"activity\": str|null, \"location\": str|null, \"hazard\": str|null, "
        "\"barrier_failure\": [str], \"equipment\": [str], \"uncertainty_note\": str|null}"
    )

    try:
        client = Groq(api_key=settings.groq_api_key)
        response = client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=700,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or ""
        import json

        parsed = json.loads(content)
        return LlmRefinement.model_validate(parsed)
    except ValidationError as exc:
        logger.warning("LLM output failed validation: %s", exc)
    except Exception as exc:  # noqa: BLE001 — degrade gracefully on any failure
        logger.warning("LLM refinement unavailable: %s", exc)
    return None