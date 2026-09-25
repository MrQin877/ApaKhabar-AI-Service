from fastapi import APIRouter, HTTPException
from app.schemas.news import NewsRequest, NewsGenerationResponse
from app.schemas.agent import ResumeRequest
from app.services.agent_service import AgentService, RunConflict
from app.providers.models import ModelError

router = APIRouter(prefix='/agent', tags=['agent'])


def execute(operation):
    try:
        return operation()
    except KeyError as exc:
        raise HTTPException(404, 'Run not found') from exc
    except RunConflict as exc:
        raise HTTPException(409, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except ModelError as exc:
        raise HTTPException(503, str(exc)) from exc


@router.get('/skills')
def skills():
    return {'skills': AgentService().registry.discover()}


@router.post('/runs', response_model=NewsGenerationResponse)
def start(request: NewsRequest):
    return execute(lambda: AgentService().run(request))


@router.get('/runs/{run_id}')
def inspect(run_id: str, owner_id: str):
    return execute(lambda: AgentService().inspect(run_id, owner_id))


@router.post('/runs/{run_id}/resume', response_model=NewsGenerationResponse)
def resume(run_id: str, request: ResumeRequest):
    return execute(lambda: AgentService().run(run_id=run_id, resume=request))
