from __future__ import annotations

import hashlib
from contextlib import contextmanager
import json
import secrets
import sqlite3
import threading
import time
from pathlib import Path
from typing import Callable

from .domain import validate_workspace


class Conflict(Exception):
    pass


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.lock = threading.RLock()
        with self.db() as db:
            db.executescript("""CREATE TABLE IF NOT EXISTS workspace (id INTEGER PRIMARY KEY, revision INTEGER, payload TEXT);
            INSERT OR IGNORE INTO workspace VALUES (1,0,'{"version":1,"sessions":[],"notes":{}}');
            CREATE TABLE IF NOT EXISTS commands (id TEXT PRIMARY KEY, session_id TEXT, result TEXT);
            CREATE TABLE IF NOT EXISTS tokens (digest TEXT PRIMARY KEY, session_id TEXT, expires REAL);
            CREATE TABLE IF NOT EXISTS pairs (code TEXT PRIMARY KEY, session_id TEXT, expires REAL);
            CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, payload TEXT);""")
        path.chmod(0o600)
        # A process restart must never silently resume exploration.
        with self.lock, self.db() as db:
            rev, raw = db.execute(
                "SELECT revision,payload FROM workspace WHERE id=1"
            ).fetchone()
            value = json.loads(raw)
            for s in value["sessions"]:
                if s["status"] == "active":
                    s["status"] = "paused"
            db.execute(
                "UPDATE workspace SET revision=?,payload=? WHERE id=1",
                (rev + 1, json.dumps(value)),
            )

    @contextmanager
    def db(self):
        conn = sqlite3.connect(self.path, timeout=10)
        try:
            conn.execute("PRAGMA foreign_keys=ON")
            with conn:
                yield conn
        finally:
            conn.close()

    def read(self) -> dict:
        with self.db() as db:
            revision, payload = db.execute(
                "SELECT revision,payload FROM workspace WHERE id=1"
            ).fetchone()
            return {"revision": revision, "workspace": json.loads(payload)}

    def replace(self, workspace: dict, expected: int) -> dict:
        value = validate_workspace(workspace)
        with self.lock, self.db() as db:
            row = db.execute(
                "UPDATE workspace SET revision=revision+1,payload=? WHERE id=1 AND revision=?",
                (json.dumps(value), expected),
            )
            if row.rowcount != 1:
                raise Conflict(
                    "Workspace changed in another client; reload before saving"
                )
        return self.read()

    def mutate(
        self, session_id: str, fn: Callable, command_id: str | None = None
    ) -> dict:
        with self.lock, self.db() as db:
            if command_id:
                row = db.execute(
                    "SELECT session_id,result FROM commands WHERE id=?", (command_id,)
                ).fetchone()
                if row:
                    if row[0] != session_id:
                        raise ValueError("Command ID belongs to another session")
                    return json.loads(row[1])
            rev, raw = db.execute(
                "SELECT revision,payload FROM workspace WHERE id=1"
            ).fetchone()
            value = json.loads(raw)
            s = next((s for s in value["sessions"] if s["id"] == session_id), None)
            if s is None:
                raise KeyError("Session not found")
            fn(s)
            validate_workspace(value)
            result = {"revision": rev + 1, "session": s}
            db.execute(
                "UPDATE workspace SET revision=?,payload=? WHERE id=1",
                (rev + 1, json.dumps(value)),
            )
            if command_id:
                db.execute(
                    "INSERT INTO commands VALUES (?,?,?)",
                    (command_id, session_id, json.dumps(result)),
                )
            return result

    def pair(self, session_id: str) -> str:
        code = secrets.token_hex(4).upper()
        with self.db() as db:
            db.execute(
                "DELETE FROM pairs WHERE session_id=? OR expires<?",
                (session_id, time.time()),
            )
            db.execute(
                "INSERT INTO pairs VALUES (?,?,?)",
                (code, session_id, time.time() + 120),
            )
        return code

    def redeem(self, code: str) -> tuple[str, str] | None:
        with self.lock, self.db() as db:
            row = db.execute(
                "SELECT session_id FROM pairs WHERE code=? AND expires>?",
                (code.upper(), time.time()),
            ).fetchone()
            if not row:
                return None
            db.execute("DELETE FROM pairs WHERE code=?", (code.upper(),))
            token = secrets.token_urlsafe(32)
            db.execute(
                "INSERT INTO tokens VALUES (?,?,?)",
                (
                    hashlib.sha256(token.encode()).hexdigest(),
                    row[0],
                    time.time() + 3600,
                ),
            )
            return token, row[0]

    def token_session(self, token: str) -> str | None:
        with self.db() as db:
            row = db.execute(
                "SELECT session_id FROM tokens WHERE digest=? AND expires>?",
                (hashlib.sha256(token.encode()).hexdigest(), time.time()),
            ).fetchone()
            return row[0] if row else None

    def put_job(self, job: dict) -> None:
        with self.db() as db:
            db.execute(
                "INSERT OR REPLACE INTO jobs VALUES (?,?)", (job["id"], json.dumps(job))
            )

    def jobs(self, session_id: str) -> list[dict]:
        with self.db() as db:
            return [
                j
                for row in db.execute("SELECT payload FROM jobs")
                if (j := json.loads(row[0]))["session_id"] == session_id
            ]
