from fastapi import APIRouter

from app.schemas.assistant import AssistantIntentRequest, AssistantIntentResponse
from app.services.assistant_service import AssistantIntentService


router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post("/intent", response_model=AssistantIntentResponse)
def classify_intent(request: AssistantIntentRequest) -> AssistantIntentResponse:
    return AssistantIntentService.classify(request)
