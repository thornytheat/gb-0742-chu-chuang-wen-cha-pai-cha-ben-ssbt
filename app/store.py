import json
import sqlite3
from contextlib import closing, contextmanager

from app.errors import FieldError
from app.manifest import canonical


class ArchiveStore:
    def __init__(self, path):
        self.path = path

    @contextmanager
    def connect(self):
        with closing(sqlite3.connect(self.path, timeout=10)) as connection, connection:
            yield connection

    def setup(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("""
                CREATE TABLE IF NOT EXISTS shift_archives (
                    id TEXT PRIMARY KEY,
                    manifest TEXT NOT NULL,
                    evidence TEXT NOT NULL,
                    input TEXT NOT NULL
                )
            """)

    def insert(self, manifest, evidence, source):
        with self.connect() as connection:
            cursor = connection.execute("INSERT INTO shift_archives VALUES (?, ?, ?, ?) ON CONFLICT(id) DO NOTHING",
                                        (manifest["id"], canonical(manifest), canonical(evidence), canonical(source)))
            record = connection.execute("SELECT manifest FROM shift_archives WHERE id = ?", (manifest["id"],)).fetchone()
            return json.loads(record[0]), cursor.rowcount == 1

    def fetch(self, run_id):
        with self.connect() as connection:
            record = connection.execute("SELECT manifest, evidence, input FROM shift_archives WHERE id = ?", (run_id,)).fetchone()
        if record is None:
            raise FieldError("UNKNOWN_RUN", "该归卷未登记", 404)
        return tuple(json.loads(value) for value in record)

    def history(self):
        with self.connect() as connection:
            return [json.loads(row[0]) for row in connection.execute("SELECT manifest FROM shift_archives ORDER BY rowid DESC")]
