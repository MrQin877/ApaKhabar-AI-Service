from typing import Literal

from fastapi import APIRouter, HTTPException, status

from app.core.config import get_settings


router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def application_health() -> dict[str, str]:
    return {"status": "ok", "service": "ApaKhabar AI Service"}


@router.get('/models')
def models_health(target: Literal["writer", "evaluator"] = "writer"):
    """Capability probe must be explicitly called: no model inference on basic health."""
    from app.providers.models import GenerationModel, ModelError
    from pydantic import BaseModel
    class Probe(BaseModel):
        ok: bool
    try:
        if target == "evaluator":
            from app.providers.evaluator import build_evaluator
            settings = get_settings()
            if not settings.evaluator_enabled:
                raise HTTPException(409, "Separate evaluator is disabled")
            model = build_evaluator(settings)
        else:
            model = GenerationModel()
        probe = model.structured(Probe, 'Return JSON with ok=true.', 'Check structured output.')
        if not probe.ok:
            raise ModelError('Structured output probe was unsuccessful')
        return {'status': 'ok', 'model': model.name, 'target': target, 'structured_output': True,
                'tool_dispatch': 'validated_action_schema'}
    except (ModelError, ValueError) as exc:
        raise HTTPException(503, str(exc)) from exc
