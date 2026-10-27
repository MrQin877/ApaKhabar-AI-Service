"""Separately configured hosted judge; never falls back to the writer."""
from app.providers.models import GenerationModel


def build_evaluator(settings):
    if settings.evaluator_model == settings.ai_model:
        raise ValueError('Evaluator must use a different model from the writer')
    return GenerationModel(settings.model_copy(update={
        'ai_base_url': settings.evaluator_base_url,
        'ai_model': settings.evaluator_model,
        'ai_api_key': settings.evaluator_api_key,
        'ai_timeout_seconds': settings.evaluator_timeout_seconds,
        'ai_max_tokens': settings.evaluator_max_tokens,
    }))
