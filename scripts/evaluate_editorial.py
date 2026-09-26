"""Generate baseline/agent outputs for human comparison; does not claim measured accuracy."""
import argparse
import json
import sys
import tempfile
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.config import get_settings
from app.providers.models import GenerationModel
from app.schemas.news import NewsRequest, NewsArticle, CompletenessResult
from app.schemas.agent import ResumeRequest
from app.services.agent_service import AgentService


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['agent', 'legacy'], required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    cases = json.loads((root / 'evaluation/editorial_cases.json').read_text())
    results = []
    with tempfile.TemporaryDirectory() as temp:
        settings = get_settings().model_copy(update={'agent_db_path': str(Path(temp) / 'evaluation.sqlite')})
        for case in cases:
            model = GenerationModel(settings)
            start = time.monotonic()
            try:
                request = NewsRequest(information=case['information'], instructions=case['instructions'], owner_id='evaluation',
                    run_id=case['id'], available_categories=['Pendidikan', 'Lainnya'], default_category='Lainnya')
                if args.mode == 'agent':
                    service = AgentService(settings, model)
                    response = service.run(request)
                    paused = response.status
                    if paused == 'awaiting_answers':
                        response = service.run(run_id=case['id'], resume=ResumeRequest(owner_id='evaluation', answers=[{'field':'limitations','value':'Tidak ada fakta tambahan yang tersedia.'}]))
                    result = response.model_dump(mode='json')
                    result['initial_status'] = paused
                else:
                    completeness = model.structured(CompletenessResult, 'Check required who, what, where, when and contradictions. Return structured completeness.', case['information'])
                    article = None
                    if completeness.status == 'ready':
                        article = model.structured(NewsArticle, 'Write Indonesian news using only supplied evidence. No invented facts. Return a structured draft.', case['information'])
                    result = {'completeness': completeness.model_dump(), 'article': article.model_dump() if article else None}
                results.append({'id':case['id'], 'expected':case['expected'], 'result':result, 'elapsed_seconds':round(time.monotonic()-start, 2), 'model_calls':model.call_count})
            except Exception as exc:
                results.append({'id':case['id'], 'error':str(exc), 'elapsed_seconds':round(time.monotonic()-start, 2), 'model_calls':model.call_count})
    Path(args.output).write_text(json.dumps({'mode':args.mode, 'cases':results, 'note':'Human factual-support review required; no accuracy claim.'}, ensure_ascii=False, indent=2))
    print(f"Wrote {len(results)} cases to {args.output}")
    return int(any('error' in r for r in results))


if __name__ == '__main__':
    raise SystemExit(main())
