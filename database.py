
"""
BrandGuard - Shared Database
Uses Turso Cloud (SQLite-compatible libSQL).

Stores:
- Submissions
- Revision history
- Approval status
- Reviewer comments
- Insights / findings log

Includes:
- Automatic migration of the existing database
- Shared cloud persistence
- Optimistic concurrency protection
- Protection against silent lost updates
"""

import json
import os

import libsql


# --------------------------------------------------
# DATABASE CONFIGURATION
# --------------------------------------------------

def _get_setting(name, default=""):
    """Read settings from Streamlit secrets or environment variables."""

    try:
        import streamlit as st

        value = st.secrets.get(name, default)

        if value:
            return value

    except Exception:
        pass

    return os.environ.get(name, default)


def get_connection():
    """Connect to the existing Turso database."""

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


# --------------------------------------------------
# DEFAULT DATA
# --------------------------------------------------

def _empty_data():
    return {
        "items": [],
        "log": []
    }


def _normalise_data(data):
    """Ensure the application data has the expected structure."""

    if not isinstance(data, dict):
        raise ValueError("Database data must be a dictionary.")

    data.setdefault("items", [])
    data.setdefault("log", [])

    if not isinstance(data["items"], list):
        data["items"] = []

    if not isinstance(data["log"], list):
        data["log"] = []

    return data


# --------------------------------------------------
# INITIALIZE DATABASE
# --------------------------------------------------

def init_db():
    """
    Create the shared storage table if it does not exist.

    Existing BrandGuard data is preserved.
    """

    conn = get_connection()

    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS brandguard_store (
                id INTEGER PRIMARY KEY,
                data TEXT NOT NULL
            )
        """)

        # Check whether the version column already exists.
        columns = conn.execute(
            "PRAGMA table_info(brandguard_store)"
        ).fetchall()

        column_names = {
            column[1] for column in columns
        }

        # Migrate the existing table without deleting its data.
        if "version" not in column_names:
            conn.execute("""
                ALTER TABLE brandguard_store
                ADD COLUMN version INTEGER NOT NULL DEFAULT 0
            """)

        # Create the initial record only if it does not exist.
        conn.execute("""
            INSERT OR IGNORE INTO brandguard_store
                (id, data, version)
            VALUES
                (1, '{"items": [], "log": []}', 0)
        """)

        conn.commit()

    finally:
        conn.close()


# --------------------------------------------------
# LOAD SHARED DATA
# --------------------------------------------------

def load_data():
    """
    Load the latest shared application data.

    _version is internal metadata used to detect
    concurrent changes before saving.
    """

    init_db()

    conn = get_connection()

    try:
        result = conn.execute("""
            SELECT data, version
            FROM brandguard_store
            WHERE id = 1
        """)

        row = result.fetchone()

        if row is None:
            data = _empty_data()
            data["_version"] = 0
            return data

        try:
            data = json.loads(row[0])

        except (json.JSONDecodeError, TypeError):
            raise RuntimeError(
                "The BrandGuard database contains invalid JSON. "
                "Existing data has not been changed."
            )

        data = _normalise_data(data)

        # Attach the database version to the loaded data.
        data["_version"] = int(row[1] or 0)

        return data

    finally:
        conn.close()


# --------------------------------------------------
# SAVE SHARED DATA
# --------------------------------------------------

def save_data(data):
    """
    Save application data using optimistic concurrency.

    Every load has a version number. A save succeeds only
    if the database still has that same version.

    This prevents one user's stale copy from silently
    overwriting another user's newer changes.
    """

    if not isinstance(data, dict):
        raise ValueError(
            "Database data must be a dictionary."
        )

    _normalise_data(data)

    # Read the version attached during load_data().
    expected_version = data.get("_version")

    if expected_version is None:
        raise RuntimeError(
            "Cannot safely save data without its database version. "
            "Reload the latest data before saving."
        )

    try:
        expected_version = int(expected_version)

    except (TypeError, ValueError):
        raise ValueError(
            "Invalid database version. Reload the data and try again."
        )

    # Never store internal metadata in the JSON application data.
    stored_data = {
        key: value
        for key, value in data.items()
        if key != "_version"
    }

    serialized = json.dumps(
        stored_data,
        ensure_ascii=False
    )

    init_db()

    conn = get_connection()

    try:
        # Atomic compare-and-update:
        # only one save can succeed for a given version.
        result = conn.execute(
            """
            UPDATE brandguard_store
            SET
                data = ?,
                version = version + 1
            WHERE
                id = 1
                AND version = ?
            """,
            (
                serialized,
                expected_version
            )
        )

        conn.commit()

        # Confirm that the update actually affected one record.
        if result.rowcount != 1:
            current = conn.execute("""
                SELECT version
                FROM brandguard_store
                WHERE id = 1
            """).fetchone()

            current_version = (
                int(current[0]) if current else None
            )

            raise RuntimeError(
                "Another user updated BrandGuard at the same time. "
                "Your older copy was not saved, to protect the latest "
                "data. Please reload the page and try again. "
                f"Expected version: {expected_version}; "
                f"current version: {current_version}."
            )

        # Update the caller's version for subsequent saves.
        data["_version"] = expected_version + 1

    finally:
        conn.close()


# --------------------------------------------------
# RESET SHARED DATA
# --------------------------------------------------

def reset_data():
    """
    Explicitly reset shared data.

    This is a destructive administrative operation.
    It uses the latest database version to avoid
    accidentally overwriting a concurrent update.
    """

    current_data = load_data()

    reset_contents = {
        "items": [],
        "log": []
    }

    current_data["items"] = reset_contents["items"]
    current_data["log"] = reset_contents["log"]

    save_data(current_data)


# --------------------------------------------------
# DATABASE HEALTH CHECK
# --------------------------------------------------

def check_connection():
    """Check whether the Turso database is reachable."""

    try:
        init_db()

        conn = get_connection()

        try:
            conn.execute(
                "SELECT id FROM brandguard_store WHERE id = 1"
            ).fetchone()

        finally:
            conn.close()

        return True, "Database connected successfully."

    except Exception as error:
        return False, str(error)


# --------------------------------------------------
# DIRECT TEST
# --------------------------------------------------

if __name__ == "__main__":
    success, message = check_connection()

    if success:
        print("SUCCESS:", message)

    else:
        print("ERROR:", message)
