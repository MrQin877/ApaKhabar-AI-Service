"""Separately configured judge; never falls back to the writer."""
from app.providers.models import GenerationModel


def build_evaluator(settings):
    writer_name = settings.llama_cpp_model if settings.ai_provider == 'llama_cpp' else settings.ollama_generation_model
    if settings.evaluator_model == writer_name:
        raise ValueError('Evaluator must use a different model from the writer')
    return GenerationModel(settings.model_copy(update={
        'ai_provider': settings.evaluator_provider,
        'llama_cpp_base_url': settings.evaluator_base_url,
        'ollama_base_url': settings.evaluator_base_url,
        'llama_cpp_model': settings.evaluator_model,
        'ollama_generation_model': settings.evaluator_model,
        'llama_cpp_api_key': settings.evaluator_api_key,
        'llama_cpp_timeout_seconds': settings.evaluator_timeout_seconds,
        'llama_cpp_max_tokens': settings.evaluator_max_tokens,
    }))
