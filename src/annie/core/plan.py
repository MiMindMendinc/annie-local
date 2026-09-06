"""Validated model-generated planning output; no fallback or invented plan text."""

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from annie.core.llm import LLMBackendError


class Plan(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    first_action: str = Field(min_length=1, max_length=240)
    checklist: list[str] = Field(min_length=3, max_length=7)


def render_plan(content: str) -> str:
    try:
        plan = Plan.model_validate_json(content)
        if any(not item.strip() for item in plan.checklist):
            raise ValueError("Empty checklist item")
    except (ValidationError, ValueError) as exc:
        raise LLMBackendError(
            "The model returned an invalid plan. Expected a first action and 3-7 checklist items. Retry or choose another model."
        ) from exc
    return plan.first_action + "\n\n" + "\n".join(f"- [ ] {item.strip()}" for item in plan.checklist)
