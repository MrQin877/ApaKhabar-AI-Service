from fastapi import APIRouter, Response, Query
from app.api.agent import execute
from app.schemas.knowledge import KnowledgeIndex, KnowledgeSearch
from app.services.knowledge_service import KnowledgeService

router = APIRouter(prefix='/rag/information', tags=['approved knowledge'])


@router.post('/index')
def index(request: KnowledgeIndex):
    return execute(lambda: {'indexed': KnowledgeService().index(request.items)})


@router.post('/search')
def search(request: KnowledgeSearch):
    return execute(lambda: {'query': request.query, 'results': KnowledgeService().search(request.query, request.owner_id, request.information_ids, request.top_k)})


@router.delete('/{information_id}', status_code=204)
def delete(information_id: str, owner_id: str = Query(min_length=1)):
    execute(lambda: KnowledgeService().delete(owner_id, information_id))
    return Response(status_code=204)
