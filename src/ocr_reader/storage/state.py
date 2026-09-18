from contextlib import contextmanager
from pathlib import Path
import json
import os
import sqlite3

from ocr_reader.exporters.files import verify_bundle
from ocr_reader.processing.document import utc_now


@contextmanager
def instance_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError("Já existe outra execução neste projeto.") from exc
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


class State:
    def __init__(self, directory: Path):
        directory.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(directory / "state.sqlite")
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY, sha256 TEXT NOT NULL, fingerprint TEXT NOT NULL,
                status TEXT NOT NULL, source_name TEXT NOT NULL, output_rel TEXT NOT NULL,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL, error_code TEXT
            );
            CREATE INDEX IF NOT EXISTS lookup ON jobs(sha256, fingerprint, created_at);
        """)

    def close(self):
        self.connection.close()

    def latest(self, sha256: str, fingerprint: str):
        return self.connection.execute(
            "SELECT * FROM jobs WHERE sha256=? AND fingerprint=? ORDER BY rowid DESC LIMIT 1",
            (sha256, fingerprint)).fetchone()

    def create(self, job_id: str, sha256: str, fingerprint: str, name: str, output_rel: str):
        now = utc_now()
        with self.connection:
            self.connection.execute("INSERT INTO jobs VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL)",
                                    (job_id, sha256, fingerprint, "running", name, output_rel, now, now))

    def update(self, job_id: str, status: str, error_code: str | None = None):
        with self.connection:
            self.connection.execute("UPDATE jobs SET status=?, updated_at=?, error_code=? WHERE id=?",
                                    (status, utc_now(), error_code, job_id))

    def recover(self, project: Path):
        # Chamado apenas com o lock exclusivo. Um processo morto liberta o lock do SO.
        for row in self.connection.execute("SELECT * FROM jobs WHERE status='running'").fetchall():
            valid = verify_bundle(project / row["output_rel"], row["sha256"], row["id"])
            self.update(row["id"], "needs_review" if valid else "interrupted")

    def rows(self):
        return [dict(row) for row in self.connection.execute("SELECT * FROM jobs ORDER BY rowid DESC")]


def log_event(path: Path, event: str, **fields) -> None:
    record = {"timestamp": utc_now(), "event": event, **fields}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

