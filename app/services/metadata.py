"""SQLite metadata store for documents, with a forward-only migration runner.

SQLite is the source of truth for document listing and status. A single connection is shared
across requests, guarded by a lock, since this is a single-process local service (see
docs/rules.md: "per-request connection or a locked shared connection - pick one").
"""

import sqlite3
import threading
from pathlib import Path

_MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


class MetadataStore:
    def __init__(self, data_dir: str):
        self._lock = threading.Lock()
        db_path = Path(data_dir)
        db_path.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path / "askdocs.db"), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._run_migrations()

    def _run_migrations(self) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                "version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
            )
            applied = {
                row[0] for row in self._conn.execute("SELECT version FROM schema_migrations")
            }
            migration_files = sorted(_MIGRATIONS_DIR.glob("*.sql"))
            for path in migration_files:
                version = int(path.name.split("_", 1)[0])
                if version in applied:
                    continue
                sql = path.read_text()
                self._conn.executescript(sql)
                self._conn.execute(
                    "INSERT INTO schema_migrations (version, applied_at) "
                    "VALUES (?, datetime('now'))",
                    (version,),
                )

    def insert_document(
        self,
        *,
        document_id: str,
        filename: str,
        content_type: str,
        size_bytes: int,
        num_chunks: int,
        status: str,
        error: str | None,
        created_at: str,
    ) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO documents "
                "(id, filename, content_type, size_bytes, num_chunks, status, error, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    document_id,
                    filename,
                    content_type,
                    size_bytes,
                    num_chunks,
                    status,
                    error,
                    created_at,
                ),
            )

    def list_documents(self) -> list[sqlite3.Row]:
        with self._lock:
            cursor = self._conn.execute("SELECT * FROM documents ORDER BY created_at DESC, id DESC")
            return cursor.fetchall()

    def get_document(self, document_id: str) -> sqlite3.Row | None:
        with self._lock:
            cursor = self._conn.execute("SELECT * FROM documents WHERE id = ?", (document_id,))
            return cursor.fetchone()

    def delete_document(self, document_id: str) -> bool:
        with self._lock, self._conn:
            cursor = self._conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))
            return cursor.rowcount > 0

    def count_documents(self) -> int:
        with self._lock:
            cursor = self._conn.execute("SELECT COUNT(*) FROM documents WHERE status = 'indexed'")
            return cursor.fetchone()[0]
