import sqlite3
from contextlib import contextmanager
from pathlib import Path
from app.core.config import settings

def connect():
    settings.db_file.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.db_file, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    with connect() as conn:
        conn.executescript('''
        CREATE TABLE IF NOT EXISTS papers (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            page_count INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'processed',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paper_id TEXT NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
            page_number INTEGER NOT NULL,
            section TEXT,
            content TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_chunks_paper ON chunks(paper_id);
        ''')
        try:
            conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(content, paper_id UNINDEXED, chunk_id UNINDEXED)")
        except sqlite3.OperationalError:
            pass

@contextmanager
def db_session():
    conn = connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
