from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[1]
POLICY = "glass-1.0.0"
MAX_FILE_BYTES = 1024 * 1024


def database_path():
    return Path(os.environ.get("MUSEUM_DB", "glass-review.sqlite3"))
