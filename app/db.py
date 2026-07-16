import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "nvr_service.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS nvrs (
    serial_number          TEXT PRIMARY KEY,
    make                   TEXT NOT NULL,
    model                  TEXT NOT NULL,
    maximum_input_channels INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS cameras (
    serial_number TEXT PRIMARY KEY,
    make          TEXT NOT NULL,
    model         TEXT NOT NULL,
    kind          TEXT NOT NULL CHECK (kind IN ('electro-optical','thermal','infrared')),
    location      TEXT NOT NULL,
    nvr_uuid      TEXT NOT NULL REFERENCES nvrs(serial_number) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_cameras_nvr_uuid ON cameras (nvr_uuid);
CREATE INDEX IF NOT EXISTS idx_cameras_location ON cameras (location);
CREATE INDEX IF NOT EXISTS idx_cameras_kind     ON cameras (kind);
"""

def get_connection(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row          # rows behave like dicts
    conn.execute("PRAGMA foreign_keys = ON") # SQLite has FKs OFF by default!
    return conn

def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()