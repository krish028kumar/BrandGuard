
"""
BrandGuard - Shared Database
Uses Turso Cloud (SQLite-compatible libSQL).

Stores:
- Submissions
- Revision history
- Approval status
- Reviewer comments
- Insights / findings log
"""

import json
import os

import libsql


# ---------------- database configuration ----------------

def _get_setting(name, default=""):
    try:
        import streamlit as st
        value = st.secrets.get(name, default)
        if value:
            return value
    except Exception:
        pass

    return os.environ.get(name, default)


def get_connection():
    database_url = _get_setting("TURSO_DATABASE_URL")
    auth_token = _get_setting("TURSO_AUTH_TOKEN")

    if not database_url or not auth_token:
        raise RuntimeError(
            "Turso database is not configured. "
            "Add TURSO_DATABASE_URL and TURSO_AUTH_TOKEN "
            "to Streamlit secrets."
        )

    return libsql.connect(
        database=database_url,
        auth_token=auth_token
    )


# ---------------- initialize database ----------------

def init_db():
    conn = get_connection()

    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS brandguard_store (
                id INTEGER PRIMARY KEY,
                data TEXT NOT NULL
            )
        """)

        conn.execute("""
            INSERT OR IGNORE INTO brandguard_store (id, data)
            VALUES (1, '{"items": [], "log": []}')
        """)

        conn.commit()

    finally:
        conn.close()


# ---------------- load shared data ----------------

def load_data():
    init_db()

    conn = get_connection()

    try:
        result = conn.execute(
            "SELECT data FROM brandguard_store WHERE id = 1"
        )

        row = result.fetchone()

        if row is None:
            return {
                "items": [],
                "log": []
            }

        data = json.loads(row[0])

        data.setdefault("items", [])
        data.setdefault("log", [])

        return data

    finally:
        conn.close()


# ---------------- save shared data ----------------

def save_data(data):
    if not isinstance(data, dict):
        raise ValueError("Database data must be a dictionary.")

    data.setdefault("items", [])
    data.setdefault("log", [])

    serialized = json.dumps(
        data,
        ensure_ascii=False
    )

    init_db()

    conn = get_connection()

    try:
        conn.execute(
            """
            INSERT INTO brandguard_store (id, data)
            VALUES (1, ?)
            ON CONFLICT(id)
            DO UPDATE SET data = excluded.data
            """,
            (serialized,)
        )

        conn.commit()

    finally:
        conn.close()


# ---------------- reset shared data ----------------

def reset_data():
    save_data({
        "items": [],
        "log": []
    })


# ---------------- database health check ----------------

def check_connection():
    try:
        init_db()
        return True, "Database connected successfully."

    except Exception as e:
        return False, str(e)

