"""Pytest fixtures and configuration for SusuTurn tests."""

import sqlite3
import pytest
from susuturn.database import init_db
from susuturn.service import SusuService


@pytest.fixture
def memory_db():
    """Provides an in-memory SQLite database initialized with schema and foreign keys."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    init_db(conn)
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def service(memory_db):
    """Provides a configured SusuService instance backed by an in-memory database."""
    return SusuService(memory_db)


@pytest.fixture
def sample_group(service):
    """Provides a standard savings group with 3 members: Ama, Kofi, Esi paying GHS 50.00 each."""
    group = service.create_group("KNUST Friends Susu", "50.00")
    m1 = service.add_member("Ama")
    m2 = service.add_member("Kofi")
    m3 = service.add_member("Esi")
    return {
        "group": group,
        "members": [m1, m2, m3],
        "service": service,
    }
