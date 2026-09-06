"""Validated model-generated planning output; no fallback or invented plan text."""

import re

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from annie.core.llm import LLMBackendError


class Plan(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    first_action: str = Field(min_length=1, max_length=240)
    checklist: list[str] = Field(min_length=3, max_length=7)


def _checklist_text(item: str) -> str:
    text = item.strip()
    # Models sometimes include their own bullets/checkboxes inside JSON strings.
    # The UI supplies one unchecked marker; preserve the actual step text.
    marker = r"^(?:(?:[-*+]|\d+[.)])\s+|\[[ xX]\]\s*)"
    while re.match(marker, text):
        text = re.sub(marker, "", text, count=1).strip()
    return text


def render_plan(content: str) -> str:
    try:
        plan = Plan.model_validate_json(content)
        checklist = [_checklist_text(item) for item in plan.checklist]
        if any(not item for item in checklist):
            raise ValueError("Empty checklist item")
    except (ValidationError, ValueError) as exc:
        raise LLMBackendError(
            "The model returned an invalid plan. Expected a first action and 3-7 checklist items. Retry or choose another model."
        ) from exc
    return plan.first_action + "\n\n" + "\n".join(f"- [ ] {item}" for item in checklist)
