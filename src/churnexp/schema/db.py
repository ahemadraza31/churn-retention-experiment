import sqlite3
import importlib.resources
from sqlite3 import Connection

def create_database(path: str = ":memory:") -> Connection:
    """Create a SQLite connection with the project schema and views.

    - Enables foreign‑key enforcement.
    - Sets ``PRAGMA user_version = 1``.
    - Loads ``schema.sql`` and ``views.sql`` from the package data.
    - Returns a connection with ``row_factory = sqlite3.Row`` for dict‑like access.
    """
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    # Enforce foreign keys
    cur.execute("PRAGMA foreign_keys = ON;")
    cur.execute("PRAGMA user_version = 1;")

    # Load schema.sql
    schema_path = importlib.resources.files("churnexp.schema").joinpath("schema.sql")
    cur.executescript(schema_path.read_text())
    # Load views.sql
    views_path = importlib.resources.files("churnexp.schema").joinpath("views.sql")
    cur.executescript(views_path.read_text())
    conn.commit()
    return conn
