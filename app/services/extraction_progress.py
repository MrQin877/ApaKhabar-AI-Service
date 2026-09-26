"""Small durable progress records. IDs are opaque capabilities issued by Laravel."""
import json
import sqlite3
import time
from pathlib import Path
from app.core.config import get_settings


def connection():
    path = get_settings().agent_db_path + '.extractions'
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10)
    db.execute('CREATE TABLE IF NOT EXISTS progress (id TEXT PRIMARY KEY, updated REAL, data TEXT)')
    return db


def record(run_id, stage, label, **details):
    if not run_id:
        return
    db = connection()
    try:
        with db:
            db.execute('DELETE FROM progress WHERE updated < ?', (time.time() - 86400,))
            db.execute('INSERT OR REPLACE INTO progress VALUES (?, ?, ?)',
                       (run_id, time.time(), json.dumps({'stage': stage, 'label': label, **details})))
    finally:
        db.close()


def inspect(run_id):
    db = connection()
    try:
        row = db.execute('SELECT data, updated FROM progress WHERE id=?', (run_id,)).fetchone()
        if not row:
            raise KeyError(run_id)
        return {**json.loads(row[0]), 'updated_at': row[1]}
    finally:
        db.close()
