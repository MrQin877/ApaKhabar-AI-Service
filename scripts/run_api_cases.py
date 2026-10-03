"""Opt-in real API evaluation. Expected answers are never sent to the model."""
import argparse
import json
import os
from pathlib import Path
import time
import uuid
import requests

ROOT = Path(__file__).resolve().parents[1]


def payload_for(case, extractions, run_id):
    items = [item for result in extractions for item in result['extraction']['information']]
    if case['mode'] == 'analysis':
        return '/assistant/respond', {'message': case['prompt'], 'information': [
            {'id': i, 'title': item['title'], 'summary': item['summary'],
             'fields': item['fields'], 'evidence': item['evidence'], 'review_status': 'pending'}
            for i, item in enumerate(items, 1)]}
    # Caller-provided extraction is used for this isolated model test, not production approval.
    clean = [{**item, 'information_id': None} for item in items]
    return '/news/generate', {'information': {'information': clean},
        'instructions': case['prompt'], 'language': 'id', 'owner_id': 'api-evaluation',
        'run_id': run_id, 'allow_web': False, 'eligible_information_ids': []}


def run_historical(case, session, base, directory, report, timeout, save):
    """Two independent turns with shared approved test knowledge, not shared fact text."""
    owner = 'eval-' + uuid.uuid4().hex
    ids = []
    def post(endpoint, payload):
        response = session.post(base + endpoint, json=payload, timeout=timeout)
        response.raise_for_status()
        return response.json()
    try:
        for turn_index, turn in enumerate(case['turns']):
            extracted = []
            for name in turn['files']:
                with (directory/'files'/name).open('rb') as file:
                    response = session.post(base+'/documents/extract-information', files={'file': (name, file)}, timeout=timeout)
                response.raise_for_status()
                extracted.append(response.json())
            report['extractions'].extend(extracted)
            mode = 'analysis' if turn_index == 0 else 'draft'
            endpoint, payload = payload_for({'mode': mode, 'prompt': turn['prompt']}, extracted, 'eval-'+uuid.uuid4().hex)
            if turn_index:
                payload.update(owner_id=owner, eligible_information_ids=ids)
            result = post(endpoint, payload)
            report.setdefault('turns', []).append({'prompt': turn['prompt'], 'result': result})
            save()
            if turn_index == 0:
                items = []
                for extraction in extracted:
                    for item in extraction['extraction']['information']:
                        iid = uuid.uuid4().hex
                        ids.append(iid)
                        items.append({**{k: item[k] for k in ('title', 'summary', 'labels', 'fields', 'evidence')},
                            'information_id': iid, 'document_id': extraction['document']['document_id'],
                            'owner_id': owner, 'source': extraction['document']['filename'],
                            'review_status': 'approved', 'is_active': True, 'archived': False})
                if not items:
                    raise ValueError('No historical information extracted; cannot test retrieval')
                post('/rag/information/index', {'items': items})
                report['test_approval'] = 'Simulated approval for isolated API test only'
            else:
                report['result'] = result
    finally:
        errors = []
        for iid in ids:
            try:
                response = session.delete(base+'/rag/information/'+iid, params={'owner_id': owner}, timeout=timeout)
                response.raise_for_status()
            except Exception as exc:
                errors.append(str(exc))
        report['cleanup_errors'] = errors
        save()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:8003')
    parser.add_argument('--case', action='append', help='Repeat to select multiple cases')
    parser.add_argument('--run', action='store_true', help='Without this flag, validate file availability only')
    parser.add_argument('--timeout', type=int, default=1200)
    args = parser.parse_args()
    directory = ROOT / 'evaluations/api_cases'
    cases = [json.loads(p.read_text()) for p in sorted(directory.glob('TC*.json'))]
    if args.case:
        unknown = set(args.case) - {c['id'] for c in cases}
        if unknown: parser.error('Unknown cases: ' + ', '.join(sorted(unknown)))
        cases = [c for c in cases if c['id'] in args.case]
    output = ROOT / 'evaluations/results' / (time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8])
    session = requests.Session()
    token = os.environ.get('APAKHABAR_AI_SERVICE_TOKEN')
    if token: session.headers['X-ApaKhabar-Service-Token'] = token
    failed = False
    for case in cases:
        missing = [name for name in case['files'] if not (directory/'files'/name).is_file()]
        if missing or case['mode'] == 'blocked':
            print(case['id'], 'BLOCKED:', missing or case['review_checklist'][0]); continue
        if not args.run:
            print(case['id'], 'READY:', ', '.join(case['files'])); continue
        output.mkdir(parents=True, exist_ok=True)
        report = {'case': case, 'status': 'running', 'extractions': [], 'human_review': 'pending'}
        path = output / (case['id'] + '.json')
        started = time.monotonic()
        try:
            if case['mode'] == 'historical':
                run_historical(case, session, args.base_url.rstrip('/'), directory, report, args.timeout,
                    lambda: path.write_text(json.dumps(report, ensure_ascii=False, indent=2)))
                report['status'] = 'awaiting_human_review'
                report['duration_seconds'] = round(time.monotonic()-started, 2)
                path.write_text(json.dumps(report, ensure_ascii=False, indent=2))
                print(case['id'], report['status'], path)
                continue
            for name in case['files']:
                with (directory/'files'/name).open('rb') as file:
                    response = session.post(args.base_url.rstrip('/')+'/documents/extract-information',
                        files={'file': (name, file)}, timeout=args.timeout)
                response.raise_for_status()
                report['extractions'].append(response.json())
                path.write_text(json.dumps(report, ensure_ascii=False, indent=2))
            endpoint, payload = payload_for(case, report['extractions'], 'eval-'+uuid.uuid4().hex)
            response = session.post(args.base_url.rstrip('/')+endpoint, json=payload, timeout=args.timeout)
            response.raise_for_status()
            report['result'] = response.json()
            report['status'] = 'awaiting_human_review'
        except Exception as exc:
            report['status'] = 'error'
            report['error'] = str(exc)
            failed = True
        report['duration_seconds'] = round(time.monotonic()-started, 2)
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2))
        print(case['id'], report['status'], path)
    return int(failed)


if __name__ == '__main__':
    raise SystemExit(main())
