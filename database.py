
"""
BrandGuard - Shared Turso Database
Multi-role authentication, Google login, exclusive Admin,
jury demo account and isolated account workspaces.
"""

import os
import re
import json
import time
import hmac
import hashlib
import secrets

import streamlit as st
import libsql


# =====================================================
# CONSTANTS
# =====================================================

ALLOWED_ROLES = ("Creator", "Reviewer", "Manager", "Admin")
STANDARD_ROLES = ("Creator", "Reviewer", "Manager")

ADMIN_NAME = "Krish Kumar"
ADMIN_EMAIL = "krishkumar28@gmail.com"

DEMO_NAME = "BrandGuard Jury Demo"
DEMO_EMAIL = "brandguard.demo@gmail.com"
DEMO_PASSWORD = "BGDemo@2026"

PASSWORD_ITERATIONS = 600000
_INIT_DONE = False


# =====================================================
# CONFIGURATION
# =====================================================

def _get_setting(name, default=""):
    try:
        value = st.secrets.get(name, default)
        if value:
            return value
    except Exception:
        pass

    return os.environ.get(name, default)


def get_connection():
    url = _get_setting("TURSO_DATABASE_URL")
    token = _get_setting("TURSO_AUTH_TOKEN")

    if not url or not token:
        raise RuntimeError(
            "Configure TURSO_DATABASE_URL and "
            "TURSO_AUTH_TOKEN in Streamlit secrets."
        )

    return libsql.connect(
        database=url,
        auth_token=token
    )


def _timestamp():
    return time.strftime(
        "%Y-%m-%d %H:%M:%S",
        time.gmtime()
    )


def _normalise_email(email):
    return str(email or "").strip().lower()


def _valid_email(email):
    email = _normalise_email(email)

    if not re.fullmatch(
        r"^[a-z0-9][a-z0-9._%+-]*@gmail\.com$",
        email
    ):
        return False

    local = email.split("@")[0]

    return (
        len(local) <= 64
        and ".." not in local
        and not local.endswith(".")
    )


def _validate_password(password):
    password = str(password)

    if len(password) < 5:
        return False, "Password must contain at least 5 characters."

    if len(password) > 128:
        return False, "Password must not exceed 128 characters."

    if not re.search(r"[A-Za-z]", password):
        return False, "Password must contain at least one letter."

    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one number."

    return True, "Valid password."


# =====================================================
# PASSWORD SECURITY
# =====================================================

def _hash_password(password, salt):
    return hashlib.pbkdf2_hmac(
        "sha256",
        str(password).encode("utf-8"),
        bytes.fromhex(salt),
        PASSWORD_ITERATIONS,
    ).hex()


def _create_password_credentials(password):
    salt = secrets.token_hex(32)

    return (
        _hash_password(password, salt),
        salt
    )


# =====================================================
# ROLE HELPERS
# =====================================================

def _set_roles(conn, user_id, roles):

    conn.execute("""
        DELETE FROM brandguard_user_roles
        WHERE user_id = ?
    """, (user_id,))

    for role in roles:
        conn.execute("""
            INSERT INTO brandguard_user_roles
                (user_id, role, created_at)
            VALUES (?, ?, ?)
        """, (
            user_id,
            role,
            _timestamp()
        ))

    primary = "Admin" if "Admin" in roles else "Creator"

    conn.execute("""
        UPDATE brandguard_users
        SET role = ?
        WHERE id = ?
    """, (primary, user_id))


def _get_roles(conn, user_id):

    row = conn.execute("""
        SELECT LOWER(TRIM(email))
        FROM brandguard_users
        WHERE id = ?
    """, (user_id,)).fetchone()

    if not row:
        return []

    email = row[0]

    if email == ADMIN_EMAIL:
        return [
            "Admin",
            "Manager",
            "Reviewer",
            "Creator"
        ]

    return list(STANDARD_ROLES)


def _get_user_row(conn, user_id):
    return conn.execute("""
        SELECT id, name, email, password_hash, password_salt,
               role, created_at, active, google_sub
        FROM brandguard_users
        WHERE id = ?
    """, (user_id,)).fetchone()


def _public_user(row, roles):

    if not row:
        return None

    return {
        "id": row[0],
        "name": row[1],
        "email": row[2],
        "role": row[5],
        "roles": list(roles),
        "created_at": row[6],
        "active": bool(row[7]),
        "google_linked": bool(row[8]),
    }


def _user_result(conn, row):

    if not row:
        return None

    return _public_user(
        row,
        _get_roles(conn, row[0])
    )


# =====================================================
# WORKSPACE HELPERS
# =====================================================

def _ensure_workspace(conn, user_id):

    conn.execute("""
        INSERT OR IGNORE INTO brandguard_user_store
            (user_id, data, version)
        VALUES (?, ?, 0)
    """, (
        user_id,
        '{"items": [], "log": []}'
    ))


# =====================================================
# INITIAL ADMIN AND JURY DEMO PROVISIONING
# =====================================================

def _bootstrap_accounts():

    conn = get_connection()

    try:

        # -------------------------------------------------
        # ADMIN ACCOUNT
        # -------------------------------------------------

        admin_password = str(
            _get_setting("BRANDGUARD_ADMIN_PASSWORD", "")
        )

        existing_admin = conn.execute("""
            SELECT id
            FROM brandguard_users
            WHERE LOWER(TRIM(email)) = ?
            LIMIT 1
        """, (ADMIN_EMAIL,)).fetchone()

        if existing_admin:

            admin_id = existing_admin[0]

            conn.execute("""
                UPDATE brandguard_users
                SET name = ?,
                    role = 'Admin',
                    active = 1
                WHERE id = ?
            """, (
                ADMIN_NAME,
                admin_id
            ))

            _set_roles(
                conn,
                admin_id,
                ALLOWED_ROLES
            )

        elif admin_password:

            valid, message = _validate_password(
                admin_password
            )

            if not valid:
                raise ValueError(
                    "Admin password: " + message
                )

            password_hash, salt = (
                _create_password_credentials(
                    admin_password
                )
            )

            admin_id = secrets.token_hex(16)

            conn.execute("""
                INSERT INTO brandguard_users (
                    id,
                    name,
                    email,
                    password_hash,
                    password_salt,
                    role,
                    created_at,
                    active
                )
                VALUES (?, ?, ?, ?, ?, 'Admin', ?, 1)
            """, (
                admin_id,
                ADMIN_NAME,
                ADMIN_EMAIL,
                password_hash,
                salt,
                _timestamp()
            ))

            _set_roles(
                conn,
                admin_id,
                ALLOWED_ROLES
            )

        # -------------------------------------------------
        # RECONCILE EXISTING ACCOUNT ROLES
        # -------------------------------------------------

        rows = conn.execute("""
            SELECT id, LOWER(TRIM(email))
            FROM brandguard_users
        """).fetchall()

        for user_id, email in rows:

            roles = (
                ALLOWED_ROLES
                if email == ADMIN_EMAIL
                else STANDARD_ROLES
            )

            _set_roles(
                conn,
                user_id,
                roles
            )

            _ensure_workspace(
                conn,
                user_id
            )

        # -------------------------------------------------
        # JURY DEMO ACCOUNT
        # -------------------------------------------------

        demo = conn.execute("""
            SELECT id
            FROM brandguard_users
            WHERE LOWER(TRIM(email)) = ?
            LIMIT 1
        """, (DEMO_EMAIL,)).fetchone()

        # Reset ONLY the dedicated jury demo password.
        demo_password_hash, demo_salt = (
            _create_password_credentials(
                DEMO_PASSWORD
            )
        )

        if demo:

            demo_id = demo[0]

            conn.execute("""
                UPDATE brandguard_users
                SET name = ?,
                    password_hash = ?,
                    password_salt = ?,
                    role = 'Creator',
                    active = 1
                WHERE id = ?
            """, (
                DEMO_NAME,
                demo_password_hash,
                demo_salt,
                demo_id
            ))

        else:

            demo_id = secrets.token_hex(16)

            conn.execute("""
                INSERT INTO brandguard_users (
                    id,
                    name,
                    email,
                    password_hash,
                    password_salt,
                    role,
                    created_at,
                    active
                )
                VALUES (?, ?, ?, ?, ?, 'Creator', ?, 1)
            """, (
                demo_id,
                DEMO_NAME,
                DEMO_EMAIL,
                demo_password_hash,
                demo_salt,
                _timestamp()
            ))

        _set_roles(
            conn,
            demo_id,
            STANDARD_ROLES
        )

        _ensure_workspace(
            conn,
            demo_id
        )

        conn.commit()

    finally:
        conn.close()


# =====================================================
# DATABASE INITIALIZATION
# =====================================================

def init_db():

    global _INIT_DONE

    if _INIT_DONE:
        return

    conn = get_connection()

    try:

        conn.execute("""
            CREATE TABLE IF NOT EXISTS brandguard_store (
                id INTEGER PRIMARY KEY,
                data TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 0
            )
        """)

        conn.execute("""
            INSERT OR IGNORE INTO brandguard_store
                (id, data, version)
            VALUES (
                1,
                '{"items": [], "log": []}',
                0
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS brandguard_users (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL DEFAULT '',
                password_salt TEXT NOT NULL DEFAULT '',
                role TEXT NOT NULL DEFAULT 'Creator',
                created_at TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            )
        """)

        columns = conn.execute(
            "PRAGMA table_info(brandguard_users)"
        ).fetchall()

        column_names = {
            row[1] for row in columns
        }

        if "google_sub" not in column_names:

            conn.execute("""
                ALTER TABLE brandguard_users
                ADD COLUMN google_sub TEXT
            """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS brandguard_user_roles (
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (user_id, role)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS brandguard_user_store (
                user_id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 0
            )
        """)

        conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS
            idx_brandguard_google_sub
            ON brandguard_users(google_sub)
            WHERE google_sub IS NOT NULL
        """)

        # Preserve existing accounts and reconcile roles.
        rows = conn.execute("""
            SELECT id, LOWER(TRIM(email))
            FROM brandguard_users
        """).fetchall()

        for user_id, email in rows:

            roles = (
                ALLOWED_ROLES
                if email == ADMIN_EMAIL
                else STANDARD_ROLES
            )

            _set_roles(
                conn,
                user_id,
                roles
            )

            _ensure_workspace(
                conn,
                user_id
            )

        conn.commit()

    finally:
        conn.close()

    _bootstrap_accounts()

    _INIT_DONE = True


# =====================================================
# REGISTRATION
# =====================================================

def register_user(name, email, password):

    name = str(name or "").strip()
    email = _normalise_email(email)
    password = str(password)

    if not 2 <= len(name) <= 80:
        return False, "Name must contain 2–80 characters."

    if not _valid_email(email):
        return False, "Enter a valid Gmail address."

    valid, message = _validate_password(password)

    if not valid:
        return False, message

    if email == ADMIN_EMAIL:
        return False, "This Admin email is reserved."

    if email == DEMO_EMAIL:
        return False, "This email is reserved for the jury demo."

    init_db()

    password_hash, salt = (
        _create_password_credentials(password)
    )

    user_id = secrets.token_hex(16)

    conn = get_connection()

    try:

        conn.execute("""
            INSERT INTO brandguard_users (
                id,
                name,
                email,
                password_hash,
                password_salt,
                role,
                created_at,
                active
            )
            VALUES (?, ?, ?, ?, ?, 'Creator', ?, 1)
        """, (
            user_id,
            name,
            email,
            password_hash,
            salt,
            _timestamp()
        ))

        _set_roles(
            conn,
            user_id,
            STANDARD_ROLES
        )

        _ensure_workspace(
            conn,
            user_id
        )

        conn.commit()

        return (
            True,
            "Account created successfully. Sign in to continue."
        )

    except Exception as error:

        if "unique constraint" in str(error).lower():
            return (
                False,
                "An account with this Gmail address already exists."
            )

        raise

    finally:
        conn.close()


# =====================================================
# PASSWORD LOGIN
# =====================================================

def authenticate_user(email, password, selected_role=None):

    email = _normalise_email(email)
    password = str(password)

    if not email or not password:
        return None, "Enter your Gmail address and password."

    if not _valid_email(email):
        return None, "Enter a valid Gmail address."

    init_db()

    conn = get_connection()

    try:

        row = conn.execute("""
            SELECT id, name, email, password_hash, password_salt,
                   role, created_at, active, google_sub
            FROM brandguard_users
            WHERE LOWER(TRIM(email)) = ?
            LIMIT 1
        """, (email,)).fetchone()

        if not row:
            return None, "Invalid Gmail address or password."

        if not bool(row[7]):
            return None, "This account has been disabled."

        if not row[3] or not row[4]:
            return None, (
                "This account uses Google login. Continue with Google."
            )

        calculated = _hash_password(
            password,
            row[4]
        )

        if not hmac.compare_digest(
            calculated,
            row[3]
        ):
            return None, "Invalid Gmail address or password."

        user = _user_result(
            conn,
            row
        )

        if (
            selected_role
            and selected_role not in user["roles"]
        ):
            return None, "That role is not assigned to this account."

        return user, "Login successful."

    finally:
        conn.close()


# =====================================================
# GOOGLE LOGIN
# =====================================================

def authenticate_google_user(
    email,
    name,
    google_sub,
    email_verified=True
):

    email = _normalise_email(email)
    name = str(name or "").strip()
    google_sub = str(google_sub or "").strip()

    if not email_verified:
        return None, "Google email must be verified."

    if not _valid_email(email):
        return None, "Only verified Gmail accounts are supported."

    if not google_sub:
        return None, "Google did not provide a valid account identifier."

    if email == DEMO_EMAIL:
        return None, "The jury demo account uses password login only."

    init_db()

    conn = get_connection()

    try:

        row = conn.execute("""
            SELECT id, name, email, password_hash, password_salt,
                   role, created_at, active, google_sub
            FROM brandguard_users
            WHERE LOWER(TRIM(email)) = ?
            LIMIT 1
        """, (email,)).fetchone()

        if row:

            if not bool(row[7]):
                return None, "This account has been disabled."

            if row[8] and row[8] != google_sub:
                return None, (
                    "This email is linked to another Google identity."
                )

            conn.execute("""
                UPDATE brandguard_users
                SET google_sub = ?
                WHERE id = ?
            """, (
                google_sub,
                row[0]
            ))

            row = _get_user_row(
                conn,
                row[0]
            )

        else:

            user_id = secrets.token_hex(16)

            conn.execute("""
                INSERT INTO brandguard_users (
                    id,
                    name,
                    email,
                    password_hash,
                    password_salt,
                    role,
                    created_at,
                    active,
                    google_sub
                )
                VALUES (?, ?, ?, '', '', 'Creator', ?, 1, ?)
            """, (
                user_id,
                (name or email.split("@")[0])[:80],
                email,
                _timestamp(),
                google_sub
            ))

            roles = (
                ALLOWED_ROLES
                if email == ADMIN_EMAIL
                else STANDARD_ROLES
            )

            _set_roles(
                conn,
                user_id,
                roles
            )

            _ensure_workspace(
                conn,
                user_id
            )

            row = _get_user_row(
                conn,
                user_id
            )

        conn.commit()

        return (
            _user_result(conn, row),
            "Google login successful."
        )

    finally:
        conn.close()


# =====================================================
# USER LOOKUP
# =====================================================

def get_user(user_id):

    if not user_id:
        return None

    init_db()

    conn = get_connection()

    try:

        row = _get_user_row(
            conn,
            user_id
        )

        if not row or not bool(row[7]):
            return None

        return _user_result(
            conn,
            row
        )

    finally:
        conn.close()


# =====================================================
# ADMIN AUTHORIZATION
# =====================================================

def _require_admin(conn, actor_user_id):

    if not actor_user_id:
        raise PermissionError(
            "Admin authentication is required."
        )

    row = conn.execute("""
        SELECT LOWER(TRIM(email)), active
        FROM brandguard_users
        WHERE id = ?
    """, (actor_user_id,)).fetchone()

    if not row or not bool(row[1]):
        raise PermissionError(
            "Active Admin authentication is required."
        )

    if row[0] != ADMIN_EMAIL:
        raise PermissionError(
            "Only the designated BrandGuard Admin can do this."
        )


# =====================================================
# ADMIN ACCOUNT MANAGEMENT
# =====================================================

def list_users(actor_user_id=None):

    init_db()

    conn = get_connection()

    try:

        _require_admin(
            conn,
            actor_user_id
        )

        rows = conn.execute("""
            SELECT id, name, email, password_hash, password_salt,
                   role, created_at, active, google_sub
            FROM brandguard_users
            ORDER BY created_at DESC
        """).fetchall()

        return [
            _user_result(conn, row)
            for row in rows
        ]

    finally:
        conn.close()


def set_user_roles(user_id, roles, actor_user_id=None):

    roles = list(
        dict.fromkeys(roles or [])
    )

    if not user_id:
        raise ValueError("User ID is required.")

    if not roles or any(
        role not in ALLOWED_ROLES
        for role in roles
    ):
        raise ValueError("Select at least one valid role.")

    init_db()

    conn = get_connection()

    try:

        _require_admin(
            conn,
            actor_user_id
        )

        target = _get_user_row(
            conn,
            user_id
        )

        if not target:
            raise ValueError("User not found.")

        target_email = _normalise_email(
            target[2]
        )

        if target_email == ADMIN_EMAIL:
            raise PermissionError(
                "The designated Admin roles cannot be changed."
            )

        if "Admin" in roles:
            raise PermissionError(
                "Admin access is reserved for Krish Kumar."
            )

        _set_roles(
            conn,
            user_id,
            STANDARD_ROLES
        )

        conn.commit()

        return True, "Account roles updated successfully."

    finally:
        conn.close()


def set_user_role(user_id, role, actor_user_id=None):

    if role == "Admin":
        raise PermissionError(
            "Admin access is reserved for Krish Kumar."
        )

    return set_user_roles(
        user_id,
        [role],
        actor_user_id
    )


def set_user_active(user_id, active, actor_user_id=None):

    if not user_id:
        raise ValueError("User ID is required.")

    init_db()

    conn = get_connection()

    try:

        _require_admin(
            conn,
            actor_user_id
        )

        target = _get_user_row(
            conn,
            user_id
        )

        if not target:
            raise ValueError("User not found.")

        if _normalise_email(target[2]) == ADMIN_EMAIL:
            raise PermissionError(
                "The designated Admin account cannot be disabled."
            )

        conn.execute("""
            UPDATE brandguard_users
            SET active = ?
            WHERE id = ?
        """, (
            1 if active else 0,
            user_id
        ))

        conn.commit()

        return True, "Account status updated successfully."

    finally:
        conn.close()


# =====================================================
# ACCOUNT WORKSPACE STORAGE
# =====================================================

def load_account_data(user_id):

    if not user_id:
        raise ValueError("Account ID is required.")

    init_db()

    conn = get_connection()

    try:

        _ensure_workspace(
            conn,
            user_id
        )

        conn.commit()

        row = conn.execute("""
            SELECT data, version
            FROM brandguard_user_store
            WHERE user_id = ?
        """, (user_id,)).fetchone()

        if row is None:
            raise RuntimeError(
                "Account workspace could not be initialized."
            )

        data = json.loads(row[0])

        if not isinstance(data, dict):
            raise ValueError("Invalid account workspace.")

        data.setdefault("items", [])
        data.setdefault("log", [])
        data["_version"] = int(row[1] or 0)

        return data

    finally:
        conn.close()


def save_account_data(user_id, data):

    if not user_id or not isinstance(data, dict):
        raise ValueError("Invalid account workspace.")

    if not isinstance(data.get("items"), list):
        raise ValueError("Invalid submissions.")

    if not isinstance(data.get("log"), list):
        raise ValueError("Invalid insights.")

    expected = data.get("_version")

    if expected is None:
        raise RuntimeError(
            "Missing workspace version. Reload before saving."
        )

    stored = {
        key: value
        for key, value in data.items()
        if key != "_version"
    }

    init_db()

    conn = get_connection()

    try:

        result = conn.execute("""
            UPDATE brandguard_user_store
            SET data = ?,
                version = version + 1
            WHERE user_id = ?
              AND version = ?
        """, (
            json.dumps(
                stored,
                ensure_ascii=False
            ),
            user_id,
            int(expected)
        ))

        if result.rowcount != 1:
            raise RuntimeError(
                "Workspace update conflict. Reload and try again."
            )

        conn.commit()

        data["_version"] = int(expected) + 1

    finally:
        conn.close()


def reset_all_workspaces(actor_user_id):

    init_db()

    conn = get_connection()

    try:

        _require_admin(
            conn,
            actor_user_id
        )

        conn.execute("""
            DELETE FROM brandguard_user_store
        """)

        conn.commit()

    finally:
        conn.close()


# =====================================================
# LEGACY SHARED STORAGE
# =====================================================

def load_data():

    init_db()

    conn = get_connection()

    try:

        row = conn.execute("""
            SELECT data, version
            FROM brandguard_store
            WHERE id = 1
        """).fetchone()

        if not row:
            raise RuntimeError(
                "Shared database record is missing."
            )

        data = json.loads(row[0])

        data.setdefault("items", [])
        data.setdefault("log", [])

        data["_version"] = int(
            row[1] or 0
        )

        return data

    finally:
        conn.close()


def save_data(data):

    if not isinstance(data, dict):
        raise ValueError("Invalid data.")

    expected = data.get("_version")

    if expected is None:
        raise RuntimeError("Missing version.")

    stored = {
        key: value
        for key, value in data.items()
        if key != "_version"
    }

    init_db()

    conn = get_connection()

    try:

        result = conn.execute("""
            UPDATE brandguard_store
            SET data = ?,
                version = version + 1
            WHERE id = 1
              AND version = ?
        """, (
            json.dumps(
                stored,
                ensure_ascii=False
            ),
            int(expected)
        ))

        if result.rowcount != 1:
            raise RuntimeError(
                "Concurrent update detected."
            )

        conn.commit()

        data["_version"] = int(expected) + 1

    finally:
        conn.close()


def reset_data(actor_user_id=None):

    init_db()

    conn = get_connection()

    try:

        _require_admin(
            conn,
            actor_user_id
        )

        conn.execute("""
            UPDATE brandguard_store
            SET data = '{"items": [], "log": []}',
                version = version + 1
            WHERE id = 1
        """)

        conn.commit()

    finally:
        conn.close()


# =====================================================
# CONNECTION CHECK
# =====================================================

def check_connection():

    try:

        init_db()

        conn = get_connection()

        try:
            conn.execute("SELECT 1").fetchone()
        finally:
            conn.close()

        return True, "Database connected successfully."

    except Exception as error:

        return False, str(error)


# =====================================================
# DIRECT EXECUTION
# =====================================================

if __name__ == "__main__":

    success, message = check_connection()

    print(
        "SUCCESS:" if success else "ERROR:",
        message
    )
