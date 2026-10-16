"""Database connection, schema management, and transaction handling."""

import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager
from typing import Generator

DEFAULT_DB_PATH = "susuturn.db"

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS savings_groups (
    id INTEGER PRIMARY KEY CHECK (id = 1), -- Enforces single group per database
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    weekly_contribution_pesewas INTEGER NOT NULL CHECK (weekly_contribution_pesewas > 0),
    created_at TEXT NOT NULL,
    current_week INTEGER NOT NULL DEFAULT 1 CHECK (current_week >= 1),
    is_completed INTEGER NOT NULL DEFAULT 0 CHECK (is_completed IN (0, 1))
);

CREATE TABLE IF NOT EXISTS members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    normalized_name TEXT NOT NULL UNIQUE,
    joining_position INTEGER NOT NULL UNIQUE CHECK (joining_position >= 1),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS contributions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE RESTRICT,
    week_number INTEGER NOT NULL CHECK (week_number >= 1),
    amount_pesewas INTEGER NOT NULL CHECK (amount_pesewas > 0),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS payouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    week_number INTEGER NOT NULL UNIQUE CHECK (week_number >= 1),
    recipient_member_id INTEGER NOT NULL UNIQUE REFERENCES members(id) ON DELETE RESTRICT,
    amount_pesewas INTEGER NOT NULL CHECK (amount_pesewas > 0),
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_contributions_week_member 
ON contributions (week_number, member_id);

CREATE INDEX IF NOT EXISTS idx_members_position 
ON members (joining_position);
"""


def get_connection(db_path: str | Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Open and return a configured SQLite connection.
    
    Enforces foreign key support and returns sqlite3.Row for friendly column access.
    """
    path_str = str(db_path)
    # Ensure directory exists if path contains directories
    parent_dir = Path(path_str).parent
    if parent_dir and not parent_dir.exists():
        parent_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(path_str, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Initialize database tables, constraints, and indexes if they do not exist."""
    conn.executescript(SCHEMA_SQL)
    conn.commit()


@contextmanager
def transaction(conn: sqlite3.Connection) -> Generator[sqlite3.Connection, None, None]:
    """Provide a transactional scope around a series of operations."""
    try:
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
