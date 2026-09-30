"""Durable execution records and LangGraph checkpoints, independent of editorial DB records."""
from contextlib import contextmanager
import hashlib
import json
import sqlite3
import time
import uuid
from pathlib import Path
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command
from app.core.config import get_settings
from app.providers.models import GenerationModel
from app.skills.registry import SkillRegistry
from app.tools.editorial import EditorialTools
from app.services.knowledge_service import KnowledgeService
from app.workflows.editorial import EditorialWorkflow
from app.schemas.news import NewsGenerationResponse, CompletenessResult


class RunConflict(ValueError):
    pass


class AgentService:
    def __init__(self, settings=None, model=None, knowledge_factory=KnowledgeService, evaluator=None):
        self.settings = settings or get_settings()
        self.model = model or GenerationModel(self.settings)
        from app.providers.evaluator import build_evaluator
        self.evaluator = evaluator or (build_evaluator(self.settings) if self.settings.evaluator_enabled else self.model)
        self.registry = SkillRegistry(self.settings.agent_skills_path)
        self.tools = EditorialTools(self.settings, self.registry, knowledge_factory)
        Path(self.settings.agent_db_path).parent.mkdir(parents=True, exist_ok=True)
        self.records_path = self.settings.agent_db_path + '.runs'
        with self.db() as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY, owner TEXT NOT NULL, request_hash TEXT NOT NULL,
                status TEXT NOT NULL, response TEXT, lease REAL NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL, data TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS events_run ON events(run_id);''')

    @contextmanager
    def db(self):
        conn = sqlite3.connect(self.records_path, timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    @staticmethod
    def key(run_id, owner):
        return hashlib.sha256(f'{owner}:{run_id}'.encode()).hexdigest()

    def event(self, key, kind, label, tool=None, payload=None):
        data = {'event_type': kind, 'label': label, 'content': label, 'tool_name': tool,
                'payload': payload or {}, 'timestamp': time.time()}
        with self.db() as db:
            db.execute('INSERT INTO events(run_id,data) VALUES (?,?)', (key, json.dumps(data, ensure_ascii=False)))

    def events(self, key):
        with self.db() as db:
            return [dict(json.loads(row['data']), sequence=i) for i, row in enumerate(db.execute('SELECT data FROM events WHERE run_id=? ORDER BY id', (key,)), 1)]

    def inspect(self, run_id, owner):
        key = self.key(run_id, owner)
        with self.db() as db:
            row = db.execute('SELECT * FROM runs WHERE id=? AND owner=?', (key, owner)).fetchone()
        if not row:
            raise KeyError('Run not found')
        return {'run_id': run_id, 'status': row['status'], 'events': self.events(key),
                'result': json.loads(row['response']) if row['response'] else None}

    def run(self, request=None, run_id=None, resume=None):
        owner = resume.owner_id if resume else request.owner_id
        run_id = run_id or request.run_id or str(uuid.uuid4())
        key = self.key(run_id, owner)
        input_hash = hashlib.sha256(request.model_dump_json().encode()).hexdigest() if request else None
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM runs WHERE id=?', (key,)).fetchone()
            if not row and resume:
                raise KeyError('Run not found')
            if row:
                if request and row['request_hash'] != input_hash:
                    raise RunConflict('Run ID already belongs to a different request')
                if row['status'] == 'completed' or (not resume and row['status'].startswith('awaiting_')) or row['status'] == 'insufficient_evidence':
                    return NewsGenerationResponse.model_validate_json(row['response'])
                if row['status'] == 'running' and row['lease'] > time.time():
                    raise RunConflict('Run is already executing')
                if resume and not row['status'].startswith('awaiting_') and row['status'] != 'failed':
                    raise RunConflict('Run is not awaiting input')
                db.execute('UPDATE runs SET status=?, lease=? WHERE id=?', ('running', time.time() + self.settings.agent_max_seconds + self.settings.llama_cpp_timeout_seconds * 2 + 60, key))
            else:
                db.execute('INSERT INTO runs(id,owner,request_hash,status,lease) VALUES (?,?,?,?,?)',
                           (key, owner, input_hash, 'running', time.time() + self.settings.agent_max_seconds + self.settings.llama_cpp_timeout_seconds * 2 + 60))
        input_validated = not bool(resume)
        previous_status = row['status'] if row else 'failed'
        started = time.monotonic()
        initial_calls = getattr(self.model, "call_count", 0)
        try:
            with SqliteSaver.from_conn_string(self.settings.agent_db_path) as saver:
                workflow = EditorialWorkflow(self.model, self.registry, self.tools, self.settings,
                    lambda kind, label, **kwargs: self.event(key, kind, label, **kwargs), evaluator=self.evaluator)
                graph = workflow.build(saver)
                config = {'configurable': {'thread_id': key}, 'recursion_limit': 100}
                snapshot = graph.get_state(config)
                if resume:
                    if not snapshot.values or (not snapshot.interrupts and previous_status != 'failed'):
                        raise RunConflict('No resumable interruption or failed checkpoint')
                    pause = snapshot.interrupts[0].value if snapshot.interrupts else None
                    if pause and pause['kind'] == 'source_approval':
                        offered = {source['source_id'] for source in pause['web_sources']}
                        if not set(resume.approved_web_source_ids) <= offered:
                            raise ValueError('Approval contains unknown web sources')
                    elif pause and resume.approved_web_source_ids:
                        raise ValueError('This run is awaiting clarification, not source approval')
                    eligible = set(resume.eligible_information_ids)
                    values = snapshot.values
                    previous_sources = values.get('sources', {})
                    sources = {k: v for k, v in previous_sources.items() if not k.startswith('information:') or k.removeprefix('information:') in eligible}
                    updated_request = dict(values['request'])
                    updated_request['eligible_information_ids'] = sorted(eligible)
                    if isinstance(updated_request['information'], dict):
                        updated_request['information'] = {'information': [item for item in updated_request['information']['information']
                            if not item.get('information_id') or item['information_id'] in eligible]}
                        if not updated_request['information']['information'] and not updated_request['instructions'] and not updated_request['user_facts']:
                            updated_request['instructions'] = 'Continue using only eligible evidence, or report insufficient evidence.'
                    update = {'sources': sources, 'request': updated_request, 'deadline': time.time() + self.settings.agent_max_seconds}
                    if not pause and len(sources) != len(previous_sources) and values.get('article'):
                        # A failed run may already hold a draft. Recheck it from current evidence.
                        update.update(article=None, quality=None, best_article=None, best_quality=None)
                        graph.update_state(config, update, as_node='approval')
                    else:
                        graph.update_state(config, update)
                    input_validated = True
                    result = graph.invoke(Command(resume=resume.model_dump()) if pause else None, config)
                elif snapshot.values:
                    # Failed processes continue from their latest durable node boundary.
                    graph.update_state(config, {'deadline': time.time() + self.settings.agent_max_seconds})
                    result = graph.invoke(None, config)
                else:
                    result = graph.invoke({'request': request.model_dump(mode='json'), 'deadline': time.time() + self.settings.agent_max_seconds}, config)
                pauses = result.get('__interrupt__', [])
                status = result.get('status', 'completed')
                if pauses:
                    status = 'awaiting_approval' if pauses[0].value['kind'] == 'source_approval' else 'awaiting_answers'
                response = NewsGenerationResponse(
                    run_id=run_id, status=status,
                    completeness=result.get('completeness') or CompletenessResult(status='needs_information', missing=[], conflicts=[], known_facts=[]),
                    article=result.get('article'), quality=result.get('quality'),
                    events=self.events(key), skills_used=[{'name': n, 'version': v} for n, v in result.get('skills', {}).items()],
                    plan=result.get('plan', []) + [{'task': 'Write or revise draft', 'skill': 'indonesian-news-writing'}, {'task': 'Review evidence and revise within limits', 'skill': 'editorial-review'}],
                    web_sources=result.get('pending_web', []), guidance=result.get('guidance'),
                    metrics={'elapsed_seconds': round(time.monotonic() - started, 3), 'model_calls': getattr(self.model, 'call_count', 0) - initial_calls, 'tool_calls': result.get('tool_count', 0), 'revisions': result.get('revisions', 0)})
                with self.db() as db:
                    db.execute('UPDATE runs SET status=?,response=?,lease=0 WHERE id=?', (status, response.model_dump_json(), key))
                return response
        except Exception as exc:
            self.event(key, 'error', 'Eksekusi gagal', payload={'error_type': type(exc).__name__})
            with self.db() as db:
                db.execute('UPDATE runs SET status=?,lease=0 WHERE id=?', ('failed' if input_validated else previous_status, key))
            raise
