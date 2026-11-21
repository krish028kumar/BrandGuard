
import json
import re
import uuid
import html
from datetime import datetime

import pandas as pd
import streamlit as st

import database
from engine import load_rulebook, review, apply_fixes, merge_findings
from ai_check import run_ai_check
import evidence
import uploads
import image_analysis
import ui


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="BrandGuard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

ROLES = ["Creator", "Reviewer", "Manager", "Admin"]
STANDARD_ROLES = ["Creator", "Reviewer", "Manager"]
ADMIN_EMAIL = "krishkumar28@gmail.com"

st.markdown(ui.CSS, unsafe_allow_html=True)

# Additional UI styling. Does not replace ui.py.
st.markdown("""
<style>
.bg-review-banner {
    padding: 17px 20px;
    border-radius: 13px;
    margin: 12px 0 20px 0;
    border: 1px solid;
    font-weight: 650;
}
.bg-verified {
    background: rgba(22,163,74,.10);
    border-color: #16a34a;
    color: #15803d;
}
.bg-unverified {
    background: rgba(220,38,38,.10);
    border-color: #dc2626;
    color: #dc2626;
}
.bg-local {
    background: rgba(217,119,6,.10);
    border-color: #d97706;
    color: #b45309;
}
.bg-score-wrap {
    display: flex;
    align-items: center;
    gap: 22px;
    padding: 18px;
    border: 1px solid rgba(128,128,128,.25);
    border-radius: 16px;
    margin: 12px 0 20px 0;
}
.bg-score-ring {
    width: 112px;
    height: 112px;
    min-width: 112px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    background: conic-gradient(var(--ring-color) var(--score), #80808022 0);
    position: relative;
}
.bg-score-ring:before {
    content: "";
    position: absolute;
    width: 88px;
    height: 88px;
    border-radius: 50%;
    background: var(--background-color, white);
}
.bg-score-inner {
    position: relative;
    z-index: 1;
    text-align: center;
}
.bg-score-number {
    font-size: 27px;
    font-weight: 800;
    line-height: 1.1;
}
.bg-score-label {
    font-size: 10px;
    opacity: .8;
}
.bg-finding-card {
    border: 1px solid rgba(128,128,128,.28);
    border-left: 5px solid var(--severity-color);
    border-radius: 12px;
    padding: 15px 17px;
    margin: 12px 0;
    background: rgba(128,128,128,.035);
}
.bg-finding-top {
    display: flex;
    gap: 9px;
    align-items: center;
    flex-wrap: wrap;
    margin-bottom: 9px;
}
.bg-chip {
    display: inline-block;
    border-radius: 20px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 750;
    background: var(--chip-bg);
    color: var(--chip-color);
}
.bg-rule {
    font-size: 12px;
    opacity: .75;
    font-weight: 650;
}
.bg-evidence {
    border-top: 1px solid rgba(128,128,128,.2);
    padding-top: 9px;
    margin-top: 10px;
    font-size: 12px;
}
.bg-draft {
    border: 1px solid rgba(128,128,128,.25);
    border-radius: 13px;
    padding: 17px;
    line-height: 1.85;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    background: rgba(128,128,128,.035);
}
.bg-flag {
    padding: 2px 4px;
    border-radius: 4px;
    font-weight: 750;
}
.bg-flag-critical { background: #dc262633; border-bottom: 2px solid #dc2626; }
.bg-flag-high { background: #ea580c33; border-bottom: 2px solid #ea580c; }
.bg-flag-medium { background: #d9770633; border-bottom: 2px solid #d97706; }
.bg-flag-low { background: #2563eb22; border-bottom: 2px solid #2563eb; }
.bg-status-chip {
    display: inline-block;
    padding: 6px 13px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 800;
}
.bg-approved { background: #16a34a20; color: #16a34a; }
.bg-rejected { background: #dc262620; color: #dc2626; }
.bg-changes { background: #d9770620; color: #d97706; }
.bg-pending { background: #64748b20; color: #64748b; }
.bg-evidence-verified { color: #16a34a; font-weight: 750; }
.bg-evidence-unsupported { color: #dc2626; font-weight: 750; }
.bg-evidence-safety { color: #d97706; font-weight: 750; }
</style>
""", unsafe_allow_html=True)


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

database.init_db()


def ensure_workspace_table():
    conn = database.get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS brandguard_user_store (
                user_id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT
            )
        """)

        columns = conn.execute(
            "PRAGMA table_info(brandguard_user_store)"
        ).fetchall()

        names = {row[1] for row in columns}

        if "version" not in names:
            conn.execute("""
                ALTER TABLE brandguard_user_store
                ADD COLUMN version INTEGER NOT NULL DEFAULT 0
            """)

        if "updated_at" not in names:
            conn.execute("""
                ALTER TABLE brandguard_user_store
                ADD COLUMN updated_at TEXT
            """)

        conn.commit()
    finally:
        conn.close()


ensure_workspace_table()


# ============================================================
# GENERAL HELPERS
# ============================================================

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def safe_json(value, default=None):
    if default is None:
        default = {}

    try:
        return json.loads(value) if isinstance(value, str) else value
    except Exception:
        return default


def is_gmail_address(email):
    email = str(email or "").strip().lower()

    if not re.fullmatch(
        r"^[a-z0-9][a-z0-9._%+-]*@gmail\.com$",
        email,
    ):
        return False

    local = email.split("@")[0]
    return ".." not in local and not local.endswith(".")


def valid_password(password):
    password = str(password)
    return (
        len(password) >= 5
        and any(char.isalpha() for char in password)
        and any(char.isdigit() for char in password)
    )


def is_guest():
    return st.session_state.get("guest", False)


def get_current_user():
    return st.session_state.get("current_user", {})


def get_active_role():
    return st.session_state.get("active_role", "Creator")


def is_designated_admin(user):
    return (
        not is_guest()
        and str(user.get("email", "")).strip().lower() == ADMIN_EMAIL
        and get_active_role() == "Admin"
    )


# ============================================================
# PERSISTENT FEEDBACK
# ============================================================

def queue_feedback(kind, message):
    """Store feedback before rerun so it is displayed on the next run."""
    st.session_state["pending_feedback"] = {
        "kind": kind,
        "message": message,
        "id": str(uuid.uuid4()),
    }


def show_pending_feedback():
    feedback = st.session_state.pop("pending_feedback", None)

    if not feedback:
        return

    kind = feedback.get("kind")
    message = feedback.get("message", "")

    if kind == "approved":
        st.success(message)
        st.balloons()
        st.snow()
        st.toast(message, icon="🎉")
    elif kind == "submitted":
        st.success(message)
        st.balloons()
        st.snow()
        st.toast(message, icon="🎉")
    elif kind == "login":
        st.toast(message, icon="🎉")
        st.balloons()
        st.snow()
    elif kind == "rejected":
        st.error(message)
        st.toast(message, icon="⛔")
    elif kind == "changes":
        st.warning(message)
        st.toast(message, icon="🟠")
    else:
        st.info(message)


# ============================================================
# GOOGLE SIGN-IN
# ============================================================

def google_auth_is_configured():
    try:
        settings = st.secrets.get("auth", {})
        if not hasattr(settings, "get"):
            return False

        return all([
            settings.get("client_id"),
            settings.get("client_secret"),
            settings.get("server_metadata_url"),
            settings.get("redirect_uri"),
            settings.get("cookie_secret"),
        ])
    except Exception:
        return False


def google_user_logged_in():
    if not google_auth_is_configured():
        return False

    try:
        return bool(st.user.is_logged_in)
    except Exception:
        return False


def get_google_value(key, default=None):
    try:
        return st.user.to_dict().get(key, default)
    except Exception:
        try:
            return st.user[key]
        except Exception:
            return default


# ============================================================
# WORKSPACE DATA
# ============================================================

def empty_workspace():
    return {
        "items": [],
        "logs": [],
        "version": 0,
        "created_at": now(),
    }


def account_load_data(user_id):
    stored = database.load_account_data(str(user_id)) or {}

    return {
        "items": stored.get("items", []),
        "logs": stored.get("logs", stored.get("log", [])),
        "version": stored.get("_version", 0),
        "created_at": stored.get("created_at", now()),
    }


def account_save_data(user_id, data):
    stored = {
        "items": data.get("items", []),
        "log": data.get("logs", data.get("log", [])),
        "_version": data.get("version", 0),
    }

    try:
        database.save_account_data(str(user_id), stored)
        data["version"] = stored["_version"]
        return True
    except Exception as exc:
        st.error(f"Could not save workspace: {exc}")
        return False


# ============================================================
# SESSION AND ROLE MANAGEMENT
# ============================================================

def get_user_roles(user):
    roles = user.get("roles") or [user.get("role", "Creator")]
    roles = [role for role in roles if role in ROLES]
    return roles or ["Creator"]


def begin_role_selection(user):
    fresh_user = database.get_user(user["id"])

    if not fresh_user:
        st.error("Your account could not be loaded. Please sign in again.")
        return

    st.session_state["pending_user"] = fresh_user
    st.session_state["pending_roles"] = get_user_roles(fresh_user)


def start_user_session(user, selected_role):
    fresh_user = database.get_user(user["id"])

    if not fresh_user:
        st.error("Account not found or disabled. Please sign in again.")
        return False

    roles = get_user_roles(fresh_user)

    if selected_role not in roles:
        st.error("That role is not assigned to this account.")
        return False

    st.session_state["authenticated"] = True
    st.session_state["guest"] = False
    st.session_state["current_user"] = fresh_user
    st.session_state["available_roles"] = roles
    st.session_state["active_role"] = selected_role
    st.session_state["workspace"] = account_load_data(fresh_user["id"])

    st.session_state.pop("pending_user", None)
    st.session_state.pop("pending_roles", None)

    queue_feedback(
        "login",
        f"Welcome to BrandGuard, {fresh_user.get('name', 'User')}!",
    )

    return True


def start_guest_session(name):
    name = str(name or "").strip()

    if not name:
        return False

    guest_id = "guest_" + str(uuid.uuid4())

    st.session_state["authenticated"] = True
    st.session_state["guest"] = True
    st.session_state["guest_name"] = name

    st.session_state["current_user"] = {
        "id": guest_id,
        "name": name,
        "email": "Guest session",
        "role": "Creator",
        "roles": STANDARD_ROLES.copy(),
        "active": True,
    }

    st.session_state["available_roles"] = STANDARD_ROLES.copy()
    st.session_state["active_role"] = "Creator"
    st.session_state["workspace"] = empty_workspace()

    queue_feedback("login", f"Welcome to BrandGuard, {name}!")

    return True


def logout():
    was_google_login = google_user_logged_in()

    for key in list(st.session_state.keys()):
        del st.session_state[key]

    if was_google_login:
        try:
            st.logout()
            return
        except Exception:
            pass

    st.rerun()


def get_workspace():
    if "workspace" not in st.session_state:
        if is_guest():
            st.session_state["workspace"] = empty_workspace()
        else:
            user = get_current_user()
            st.session_state["workspace"] = account_load_data(user["id"])

    return st.session_state["workspace"]


def save_workspace():
    if is_guest():
        return True

    user = get_current_user()
    return account_save_data(user["id"], get_workspace())


def add_log(action, details=""):
    data = get_workspace()

    data.setdefault("logs", []).append({
        "action": action,
        "details": details,
        "timestamp": now(),
        "role": get_active_role(),
    })

    save_workspace()


# ============================================================
# ADMIN: LOAD ALL USERS AND SUBMISSIONS
# ============================================================

def load_platform_data(admin_user):
    platform_users = []
    platform_submissions = []
    platform_logs = []

    accounts = database.list_users(actor_user_id=admin_user["id"]) or []

    for account in accounts:
        account_id = str(account.get("id", ""))
        account_name = account.get("name", "Unknown")
        account_email = account.get("email", "")

        if not account_id:
            continue

        try:
            workspace = account_load_data(account_id)
        except Exception:
            continue

        platform_users.append({
            "User": account_name,
            "Email": account_email,
            "Status": "Active" if account.get("active", True) else "Inactive",
            "Account ID": account_id,
        })

        for item in workspace.get("items", []):
            if isinstance(item, dict):
                submission = dict(item)
                submission["_owner_id"] = account_id
                submission["_owner_name"] = account_name
                submission["_owner_email"] = account_email
                platform_submissions.append(submission)

        for log in workspace.get("logs", []):
            if isinstance(log, dict):
                entry = dict(log)
                entry["Account"] = account_name
                entry["Email"] = account_email
                platform_logs.append(entry)

    return platform_users, platform_submissions, platform_logs


# ============================================================
# REGISTRATION
# ============================================================

def register_account(name, email, password):
    name = str(name or "").strip()
    email = str(email or "").strip().lower()

    if not name:
        return False, "Please enter your name."

    if not is_gmail_address(email):
        return False, "Please enter a valid Gmail address."

    if not valid_password(password):
        return False, (
            "Password must contain at least 5 characters, "
            "one letter and one number."
        )

    return database.register_user(name, email, password)


# ============================================================
# LOGIN INSTRUCTIONS
# ============================================================

def show_login_instructions():
    with st.expander(
        "📖 How to use BrandGuard — read these steps",
        expanded=False,
    ):
        st.markdown("""
        **Step 1 — Sign in or create an account**

        - Register using your Gmail address and password.
        - Existing users can sign in directly.
        - You can also use Continue with Google.

        **Step 2 — Choose your role**

        - Every registered account receives Creator, Reviewer and Manager.
        - Select a dashboard after signing in.
        - Switch between roles from the sidebar.

        **Step 3 — Role access**

        - **Creator:** Create and submit content or images.
        - **Reviewer:** Inspect submissions and make review decisions.
        - **Manager:** Review submissions and view insights.
        - **Admin:** View platform-wide activity and manage accounts.

        **Step 4 — Guest access**

        - Select Enter as Guest.
        - Enter your name.
        - Explore Creator, Reviewer and Manager dashboards.
        - Guest work is temporary and is not saved to a registered account.
        """)


# ============================================================
# AUTHENTICATION PAGE
# ============================================================

def show_auth_page():
    st.markdown(ui.hero(), unsafe_allow_html=True)
    st.caption("AI-powered brand compliance platform")
    st.divider()

    show_login_instructions()

    if "auth_view_next" in st.session_state:
        st.session_state["auth_view"] = st.session_state.pop("auth_view_next")

    if "auth_view" not in st.session_state:
        st.session_state["auth_view"] = "Sign in"

    auth_view = st.radio(
        "Choose how to enter BrandGuard",
        ["Sign in", "Create account", "Enter as Guest"],
        horizontal=True,
        key="auth_view",
    )

    if auth_view == "Sign in":
        st.subheader("Welcome back")

        if st.session_state.get("registration_success_message"):
            st.success(st.session_state.pop("registration_success_message"))

        st.info(
            "Jury demo account\n\n"
            "Email: brandguard.demo@gmail.com\n\n"
            "Password: BGDemo@2026\n\n"
            "The demo account has Creator, Reviewer and Manager access."
        )

        email = st.text_input("Gmail address", key="login_email")
        password = st.text_input(
            "Password",
            type="password",
            key="login_password",
        )

        if st.button("Sign in", use_container_width=True, type="primary"):
            if not is_gmail_address(email):
                st.error("Enter a valid Gmail address.")
            elif not password:
                st.error("Enter your password.")
            else:
                try:
                    user, message = database.authenticate_user(
                        email.strip().lower(),
                        password,
                    )

                    if user:
                        begin_role_selection(user)
                        st.rerun()
                    else:
                        st.error(message or "Sign-in failed.")
                except Exception as exc:
                    st.error(f"Sign-in error: {exc}")

        if google_auth_is_configured():
            st.divider()
            st.markdown("**Or sign in with Google**")

            if st.button(
                "Continue with Google",
                use_container_width=True,
                key="google_login_button",
            ):
                try:
                    st.login()
                except Exception as exc:
                    st.error(f"Could not start Google sign-in: {exc}")
        else:
            st.caption(
                "Google sign-in is not configured yet. "
                "You can still use Gmail and password."
            )

    elif auth_view == "Create account":
        st.subheader("Create your BrandGuard account")

        name = st.text_input("Full name", key="register_name")
        email = st.text_input("Gmail address", key="register_email")
        password = st.text_input(
            "Create password",
            type="password",
            key="register_password",
        )
        confirm = st.text_input(
            "Confirm password",
            type="password",
            key="register_confirm",
        )

        st.caption(
            "Password must contain at least 5 characters, "
            "one letter and one number."
        )

        st.success(
            "Every new account automatically receives "
            "Creator, Reviewer and Manager access."
        )

        if st.button(
            "Create account",
            use_container_width=True,
            type="primary",
        ):
            if password != confirm:
                st.error("Passwords do not match.")
            else:
                try:
                    success, message = register_account(
                        name,
                        email,
                        password,
                    )

                    if success:
                        st.session_state["registration_success_message"] = (
                            "Account created successfully! "
                            "Sign in using your Gmail and password."
                        )
                        st.session_state["auth_view_next"] = "Sign in"
                        st.rerun()
                    else:
                        st.error(message)
                except Exception as exc:
                    st.error(f"Registration error: {exc}")

    elif auth_view == "Enter as Guest":
        st.subheader("Explore BrandGuard without registering")

        st.info("""
        **Temporary Guest Access**

        Explore these three dashboards without creating an account:

        - Creator
        - Reviewer
        - Manager

        Switch between dashboards from the sidebar. Guest changes are
        temporary and are not saved to a registered account.
        """)

        guest_name = st.text_input(
            "Enter your name",
            placeholder="Your name",
            key="guest_name_input",
        )

        if st.button(
            "Enter BrandGuard as Guest",
            use_container_width=True,
            type="primary",
        ):
            if not guest_name.strip():
                st.warning("Please enter your name.")
            else:
                start_guest_session(guest_name)
                st.rerun()


# ============================================================
# ROLE SELECTION
# ============================================================

def show_role_selection():
    user = st.session_state.get("pending_user")

    if not user:
        return

    fresh_user = database.get_user(user["id"])

    if not fresh_user:
        st.error("Account could not be found. Please sign in again.")
        st.session_state.pop("pending_user", None)
        st.session_state.pop("pending_roles", None)
        return

    roles = get_user_roles(fresh_user)
    st.session_state["pending_user"] = fresh_user
    st.session_state["pending_roles"] = roles

    st.markdown(ui.hero(), unsafe_allow_html=True)

    st.success(
        f"Welcome, {fresh_user.get('name', 'User')}! "
        "Your account has been authenticated."
    )

    st.divider()
    st.header("Choose your BrandGuard role")

    selected_role = st.radio(
        "Available roles",
        roles,
        horizontal=True,
        key="login_selected_role",
    )

    st.info(f"You are about to enter as **{selected_role}**.")

    if st.button(
        "Enter BrandGuard",
        type="primary",
        use_container_width=True,
    ):
        if start_user_session(fresh_user, selected_role):
            st.rerun()

    if st.button("Back to sign in"):
        st.session_state.pop("pending_user", None)
        st.session_state.pop("pending_roles", None)
        st.rerun()


# ============================================================
# GOOGLE LOGIN PROCESSING
# ============================================================

def process_google_login():
    if not google_user_logged_in():
        return False

    try:
        email = get_google_value("email", "")
        name = get_google_value("name", "Google User")
        google_sub = get_google_value("sub", "")
        verified = get_google_value("email_verified", False)

        if not email or not verified:
            st.error("Google account email could not be verified.")
            st.logout()
            return False

        if not is_gmail_address(email):
            st.error("Please sign in using a Gmail account.")
            st.logout()
            return False

        user, message = database.authenticate_google_user(
            email=email,
            name=name,
            google_sub=google_sub,
            email_verified=verified,
        )

        if not user:
            st.error(message or "Google sign-in failed.")
            return False

        begin_role_selection(user)
        st.rerun()

    except Exception as exc:
        st.error(f"Google sign-in failed: {exc}")

    return False


# ============================================================
# AUTHENTICATION FLOW
# ============================================================

if not st.session_state.get("authenticated", False):

    if (
        not st.session_state.get("pending_user")
        and google_user_logged_in()
    ):
        process_google_login()

    if st.session_state.get("pending_user"):
        show_role_selection()
        st.stop()

    show_auth_page()
    st.stop()


# ============================================================
# REFRESH REGISTERED USER AND PERMISSIONS
# ============================================================

if not is_guest():
    try:
        session_user = get_current_user()
        fresh_user = database.get_user(session_user["id"])

        if not fresh_user:
            st.error("Your account could not be found. Please sign in again.")
            logout()

        if not fresh_user.get("active", True):
            st.error("Your account has been deactivated.")
            logout()

        roles = get_user_roles(fresh_user)

        st.session_state["current_user"] = fresh_user
        st.session_state["available_roles"] = roles

        if st.session_state.get("active_role") not in roles:
            st.session_state["active_role"] = roles[0]

    except Exception as exc:
        st.error(f"Account verification failed: {exc}")
        st.stop()

else:
    st.session_state["available_roles"] = STANDARD_ROLES.copy()

    if st.session_state.get("active_role") not in STANDARD_ROLES:
        st.session_state["active_role"] = "Creator"


# Show messages queued before st.rerun().
show_pending_feedback()


# ============================================================
# SIDEBAR
# ============================================================

user = get_current_user()
role = get_active_role()
available_roles = st.session_state.get("available_roles", ["Creator"])

if role == "Admin" and (
    is_guest()
    or user.get("email", "").strip().lower() != ADMIN_EMAIL
):
    st.error("Admin access is restricted to the designated administrator.")
    st.session_state["active_role"] = "Creator"
    st.rerun()

with st.sidebar:
    st.markdown("## 🛡️ BrandGuard")
    st.caption("Brand compliance workspace")
    st.divider()

    st.markdown("### Account")
    st.write(f"**{user.get('name', 'User')}**")

    if is_guest():
        st.warning("Temporary guest session")
    else:
        st.caption(user.get("email", ""))

    st.divider()
    st.markdown("### Switch dashboard")

    selected_role = st.selectbox(
        "Active role",
        available_roles,
        index=(
            available_roles.index(role)
            if role in available_roles
            else 0
        ),
        key="role_selector",
    )

    if selected_role != role:
        st.session_state["active_role"] = selected_role
        st.rerun()

    if is_guest():
        st.caption("Guest mode: Creator, Reviewer and Manager dashboards.")

    if role == "Admin":
        st.caption("Platform-wide administrator access")

    st.divider()

    if st.button("Log out", use_container_width=True):
        logout()


# ============================================================
# HEADER
# ============================================================

st.markdown(ui.hero(), unsafe_allow_html=True)

if role == "Admin":
    st.subheader(f"Welcome, {user.get('name', 'Admin')} · Admin dashboard")
else:
    st.subheader(
        f"Welcome, {user.get('name', 'User')} · {role} dashboard"
    )

if is_guest():
    st.info(
        "You are exploring BrandGuard as a guest. "
        "Your workspace is temporary and isolated from registered accounts."
    )

st.divider()


# ============================================================
# RULEBOOK
# ============================================================

def get_rulebook():
    try:
        return load_rulebook()
    except Exception as exc:
        st.warning(f"Could not load the rulebook: {exc}")
        return {}


# ============================================================
# FINDING AND REVIEW HELPERS
# ============================================================

def normalize_findings(result):
    if isinstance(result, dict):
        findings = result.get("findings", [])
        return findings if isinstance(findings, list) else []

    if isinstance(result, list):
        return result

    return []


def add_display_fields(findings):
    output = []

    for finding in findings:
        if isinstance(finding, str):
            finding = {"message": finding}

        if not isinstance(finding, dict):
            continue

        finding = dict(finding)

        finding.setdefault(
            "message",
            "%s · %s: %s. %s" % (
                finding.get("severity", "Info"),
                finding.get("category", ""),
                finding.get("text", ""),
                finding.get("why", ""),
            ),
        )

        if finding.get("suggestion"):
            finding.setdefault("recommendation", finding["suggestion"])

        if finding.get("recommendation"):
            finding.setdefault("suggestion", finding["recommendation"])

        source = finding.get("source", "Not specified")
        confidence = finding.get("confidence", "Not specified")
        verification = finding.get("verification", "")

        finding["evidence"] = (
            f"Source: {source} · Confidence: {confidence}"
        )

        if verification:
            finding["evidence"] += (
                " · " + str(verification).replace("_", " ")
            )

        output.append(finding)

    return output


def normalize_ai_result(raw):
    """
    Fail closed.

    Only an explicit successful status or explicit success=True is accepted.
    A missing status, exception, error, or ambiguous response is unverified.
    """
    findings = normalize_findings(raw)

    if not isinstance(raw, dict):
        return {
            "status": "failed",
            "error": "AI check did not return a verifiable status.",
            "findings": findings,
        }

    status = str(raw.get("status", "")).strip().lower()
    success = raw.get("success")

    successful_statuses = {
        "completed", "success", "successful", "passed", "ok"
    }

    failed_statuses = {
        "failed", "error", "unverified", "local_only",
        "local-only", "timeout", "cancelled", "canceled"
    }

    if status in successful_statuses or success is True:
        return {
            "status": "completed",
            "error": "",
            "findings": findings,
        }

    if status in failed_statuses or success is False:
        return {
            "status": "failed",
            "error": str(
                raw.get("error")
                or raw.get("message")
                or "AI verification did not complete."
            ),
            "findings": findings,
        }

    return {
        "status": "failed",
        "error": str(
            raw.get("error")
            or raw.get("message")
            or "AI check returned no confirmed completion status."
        ),
        "findings": findings,
    }


def run_content_review(text, title="Untitled"):
    rulebook = get_rulebook()

    try:
        local_findings = normalize_findings(review(text, rulebook))
    except Exception as exc:
        st.error(f"Content review failed: {exc}")
        local_findings = []

    retrieved = []
    ai_rulebook = rulebook

    try:
        retrieved = evidence.retrieve(text, rulebook)
        ai_rulebook = evidence.grounded_rulebook(rulebook, retrieved)
    except Exception:
        pass

    try:
        raw_ai_result = run_ai_check(
            text,
            ai_rulebook,
            brand_mode=True,
        )
        ai_result = normalize_ai_result(raw_ai_result)
        ai_findings = ai_result["findings"]
    except Exception as exc:
        ai_result = {
            "status": "failed",
            "error": str(exc),
            "findings": [],
        }
        ai_findings = []

    try:
        findings = merge_findings(local_findings, ai_findings)
    except Exception:
        findings = local_findings + ai_findings

    try:
        findings = evidence.verify_findings(findings, rulebook, retrieved)
    except Exception:
        pass

    findings = add_display_fields(findings)

    return {
        "title": title,
        "content": text,
        "findings": findings,
        "ai_result": ai_result,
        "evidence": {"retrieved": retrieved},
        "created_at": now(),
    }


def save_submission(item):
    data = get_workspace()

    item.setdefault("id", str(uuid.uuid4()))
    item.setdefault("created_at", now())
    item.setdefault("status", "Pending")
    item.setdefault("comments", [])
    item.setdefault("history", [])

    data.setdefault("items", []).append(item)
    save_workspace()

    add_log("Submission created", item.get("title", "Untitled"))


def finding_count(item):
    return len(item.get("findings", []))


def status_badge(status):
    normalized = str(status or "Pending").strip().lower()

    if normalized == "approved":
        return (
            '<span class="bg-status-chip bg-approved">✓ Approved</span>'
        )

    if normalized == "rejected":
        return (
            '<span class="bg-status-chip bg-rejected">✕ Rejected</span>'
        )

    if normalized in ["changes requested", "changes_requested"]:
        return (
            '<span class="bg-status-chip bg-changes">'
            '↻ Changes requested</span>'
        )

    return (
        '<span class="bg-status-chip bg-pending">● Pending</span>'
    )


def render_status_badge(status):
    st.markdown(status_badge(status), unsafe_allow_html=True)


# ============================================================
# RICH REVIEW UI HELPERS
# ============================================================

def severity_info(finding):
    severity = str(finding.get("severity", "Information")).lower()

    if any(word in severity for word in ["critical", "threat", "blocker"]):
        return "🚫", "Critical", "#dc2626", "critical"

    if "high" in severity:
        return "🔴", "High", "#ea580c", "high"

    if "medium" in severity or "moderate" in severity:
        return "🟠", "Medium", "#d97706", "medium"

    if "low" in severity:
        return "🔵", "Low", "#2563eb", "low"

    return "ℹ️", "Info", "#64748b", "low"


def is_threat_finding(finding):
    text = " ".join([
        str(finding.get("category", "")),
        str(finding.get("severity", "")),
        str(finding.get("message", "")),
        str(finding.get("text", "")),
    ]).lower()

    return any(word in text for word in [
        "threat", "malware", "phishing", "fraud",
        "scam", "malicious", "impersonation",
    ])


def calculate_score(findings, ai_status):
    if ai_status != "completed":
        return None

    score = 100

    for finding in findings:
        if not isinstance(finding, dict):
            continue

        _, severity, _, _ = severity_info(finding)

        if severity == "Critical":
            score -= 25
        elif severity == "High":
            score -= 15
        elif severity == "Medium":
            score -= 8
        elif severity == "Low":
            score -= 3

    return max(0, min(100, score))


def render_score_ring(findings, ai_status):
    if ai_status != "completed":
        st.markdown("""
        <div class="bg-score-wrap">
            <div style="font-size:48px">😰</div>
            <div>
                <div style="font-size:20px;font-weight:800">
                    Score unavailable
                </div>
                <div>AI verification is unverified. No Safe score is claimed.</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    score = calculate_score(findings, ai_status)

    if any(is_threat_finding(f) for f in findings if isinstance(f, dict)):
        face = "🚫"
        color = "#dc2626"
        label = "Threat detected"
    elif score >= 85:
        face = "😄"
        color = "#16a34a"
        label = "Strong compliance"
    elif score >= 65:
        face = "🙂"
        color = "#65a30d"
        label = "Minor improvements"
    elif score >= 40:
        face = "😟"
        color = "#d97706"
        label = "Needs attention"
    else:
        face = "😰"
        color = "#dc2626"
        label = "Significant issues"

    st.markdown(f"""
    <div class="bg-score-wrap">
        <div class="bg-score-ring"
             style="--score:{score}%;--ring-color:{color}">
            <div class="bg-score-inner">
                <div class="bg-score-number">{score}</div>
                <div class="bg-score-label">/ 100</div>
            </div>
        </div>
        <div>
            <div style="font-size:36px">{face}</div>
            <div style="font-size:20px;font-weight:800">{label}</div>
            <div style="opacity:.75">Brand compliance score</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_ai_banner(status, error=""):
    status = str(status or "").lower()

    if status == "completed":
        st.markdown("""
        <div class="bg-review-banner bg-verified">
            ✓ AI CHECK COMPLETED — Verification finished successfully.
            Findings are AI-assisted and should be reviewed by a human.
        </div>
        """, unsafe_allow_html=True)
    else:
        safe_error = html.escape(str(error or "AI verification did not complete."))
        st.markdown(f"""
        <div class="bg-review-banner bg-unverified">
            ⚠ UNVERIFIED — AI verification did not complete.
            This result is not Safe and must not be treated as approved.
            <div style="font-size:12px;font-weight:400;margin-top:7px">
                {safe_error[:500]}
            </div>
        </div>
        """, unsafe_allow_html=True)


def finding_evidence_label(finding):
    verification = str(
        finding.get("verification", "")
        or finding.get("evidence_status", "")
    ).lower()

    source = str(finding.get("source", "")).lower()
    category = str(finding.get("category", "")).lower()
    message = str(finding.get("message", "")).lower()

    if (
        "unsupported" in verification
        or "unverified" in verification
        or "unsupported" in message
    ):
        return "⚠ Unsupported claim", "bg-evidence-unsupported"

    if (
        "safety" in category
        or "safety" in source
        or "ai safety" in verification
        or "threat" in category
    ):
        return "🛡️ AI safety", "bg-evidence-safety"

    if (
        "verified" in verification
        or "approved" in verification
        or finding.get("evidence_verified") is True
    ):
        return "✓ Verified", "bg-evidence-verified"

    if finding.get("source") and finding.get("confidence"):
        return "✓ Evidence available", "bg-evidence-verified"

    return "⚠ Evidence not verified", "bg-evidence-unsupported"


def render_finding_card(finding, index):
    if isinstance(finding, str):
        finding = {"message": finding}

    if not isinstance(finding, dict):
        finding = {"message": str(finding)}

    icon, severity, color, _ = severity_info(finding)

    rule_id = (
        finding.get("rule_id")
        or finding.get("rule")
        or finding.get("id")
        or "BrandGuard finding"
    )

    message = (
        finding.get("message")
        or finding.get("description")
        or finding.get("issue")
        or finding.get("text")
        or "Potential compliance issue"
    )

    why = (
        finding.get("why")
        or finding.get("reason")
        or finding.get("explanation")
        or message
    )

    source = (
        finding.get("source")
        or finding.get("reference")
        or "No source specified"
    )

    suggestion = (
        finding.get("suggestion")
        or finding.get("recommendation")
        or finding.get("recommended_action")
        or "Review this item against the approved brand guidelines."
    )

    evidence_label, evidence_class = finding_evidence_label(finding)

    fields = [
        ("Rule ID", rule_id),
        ("Finding", message),
        ("Why flagged", why),
        ("Source", source),
        ("Suggestion", suggestion),
    ]

    body = "".join(
        f'<div style="margin:7px 0"><b>{html.escape(label)}:</b> '
        f'{html.escape(str(value))}</div>'
        for label, value in fields
    )

    st.markdown(f"""
    <div class="bg-finding-card" style="--severity-color:{color}">
        <div class="bg-finding-top">
            <span style="font-size:21px">{icon}</span>
            <span class="bg-rule">{html.escape(str(rule_id))}</span>
            <span class="bg-chip"
                  style="--chip-bg:{color}22;--chip-color:{color}">
                {html.escape(severity.upper())}
            </span>
        </div>
        {body}
        <div class="bg-evidence">
            <span class="{evidence_class}">
                Evidence: {html.escape(evidence_label)}
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_highlighted_draft(content, findings):
    escaped_content = html.escape(str(content or ""))

    replacements = []

    for finding in findings:
        if not isinstance(finding, dict):
            continue

        candidates = [
            finding.get("flagged_text"),
            finding.get("matched_text"),
            finding.get("offending_text"),
            finding.get("quoted_text"),
        ]

        for candidate in candidates:
            candidate = str(candidate or "").strip()

            if candidate and len(candidate) > 1:
                _, _, _, css_class = severity_info(finding)
                replacements.append((candidate, css_class))

        # Also highlight explicit terms if provided by the finding.
        terms = finding.get("flagged_words", [])
        if isinstance(terms, str):
            terms = [terms]

        if isinstance(terms, list):
            for term in terms:
                term = str(term or "").strip()
                if term and len(term) > 1:
                    _, _, _, css_class = severity_info(finding)
                    replacements.append((term, css_class))

    # Longer phrases first to avoid partial overlap.
    replacements.sort(key=lambda x: len(x[0]), reverse=True)

    for term, css_class in replacements:
        safe_term = html.escape(term)
        pattern = re.compile(re.escape(safe_term), re.IGNORECASE)

        escaped_content = pattern.sub(
            lambda match: (
                f'<mark class="bg-flag bg-flag-{css_class}">'
                f'{match.group(0)}</mark>'
            ),
            escaped_content,
        )

    st.markdown(
        '<div class="bg-draft">' + escaped_content + '</div>',
        unsafe_allow_html=True,
    )


def render_review_results(content, findings, ai_result, title="Review"):
    ai_status = ai_result.get("status", "failed")

    st.subheader(f"✨ {title} results")

    render_ai_banner(
        ai_status,
        ai_result.get("error", ""),
    )

    render_score_ring(findings, ai_status)

    st.subheader("📝 Reviewed draft")

    if content:
        render_highlighted_draft(content, findings)

    st.subheader("🔎 Findings")

    if not findings:
        if ai_status == "completed":
            st.success("No compliance findings were identified.")
        else:
            st.warning(
                "No verified result is available because the AI check "
                "did not complete. This does not mean the content is Safe."
            )
    else:
        for index, finding in enumerate(findings, start=1):
            render_finding_card(finding, index)


# ============================================================
# LOAD CURRENT WORKSPACE
# ============================================================

data = get_workspace()
items = data.get("items", [])


# ============================================================
# ADMIN PLATFORM-WIDE OVERVIEW
# ============================================================

def show_admin_overview():
    st.header("🌐 BrandGuard platform overview")

    st.write(
        "This dashboard shows submissions and account activity "
        "across all registered BrandGuard users."
    )

    try:
        with st.spinner("Loading platform-wide data..."):
            platform_users, all_submissions, all_logs = load_platform_data(user)

    except Exception as exc:
        st.error(f"Could not load platform data: {exc}")
        st.info(
            "Check that database.list_users() and "
            "database.load_account_data() are working."
        )
        return

    total_users = len(platform_users)
    total_submissions = len(all_submissions)

    pending = sum(1 for item in all_submissions if item.get("status") == "Pending")
    approved = sum(1 for item in all_submissions if item.get("status") == "Approved")
    rejected = sum(1 for item in all_submissions if item.get("status") == "Rejected")
    changes = sum(1 for item in all_submissions if item.get("status") == "Changes Requested")

    st.subheader("Platform statistics")

    a, b, c, d, e, f = st.columns(6)
    a.metric("Registered users", total_users)
    b.metric("Total submissions", total_submissions)
    c.metric("Pending", pending)
    d.metric("Approved", approved)
    e.metric("Rejected", rejected)
    f.metric("Changes requested", changes)

    st.divider()
    st.subheader("📋 All user submissions")

    if not all_submissions:
        st.info("No submissions have been made yet.")
    else:
        rows = []

        for item in sorted(
            all_submissions,
            key=lambda x: str(x.get("created_at", "")),
            reverse=True,
        ):
            rows.append({
                "Title": item.get("title", "Untitled"),
                "Type": item.get("type", "Content"),
                "Submitted by": item.get("_owner_name", "Unknown"),
                "Email": item.get("_owner_email", ""),
                "Status": item.get("status", "Pending"),
                "Submitted at": item.get("created_at", ""),
                "Findings": finding_count(item),
            })

        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
        )

        st.divider()
        st.subheader("Submission details")

        for index, item in enumerate(
            sorted(
                all_submissions,
                key=lambda x: str(x.get("created_at", "")),
                reverse=True,
            )
        ):
            title = item.get("title", "Untitled")
            owner = item.get("_owner_name", "Unknown")
            status = item.get("status", "Pending")

            with st.expander(f"{title} · {owner} · {status}"):
                st.write("**Submitted by:**", owner)
                st.write("**Email:**", item.get("_owner_email", ""))
                st.write("**Type:**", item.get("type", "Content"))
                render_status_badge(status)
                st.write("**Date:**", item.get("created_at", ""))

                if item.get("content"):
                    st.markdown("**Submitted content**")
                    st.text_area(
                        "Content",
                        value=item.get("content", ""),
                        height=130,
                        key=f"admin_content_{index}",
                        disabled=True,
                    )

                if item.get("filename"):
                    st.write("**Image file:**", item.get("filename"))

                if item.get("alt_text"):
                    st.write("**Alternative text:**", item.get("alt_text"))

                st.write("**Findings**")

                findings = item.get("findings", [])

                if not findings:
                    st.write("No findings recorded.")
                else:
                    for finding_index, finding in enumerate(findings, start=1):
                        render_finding_card(finding, finding_index)

                st.write("**Review history**")

                for entry in item.get("history", []):
                    st.write(
                        f"- {entry.get('action', '')} — "
                        f"{entry.get('by', '')} "
                        f"({entry.get('timestamp', '')})"
                    )

    st.divider()
    st.subheader("👥 Registered users")

    if platform_users:
        users_df = pd.DataFrame([
            {
                "Name": account["User"],
                "Email": account["Email"],
                "Status": account["Status"],
            }
            for account in platform_users
        ])

        st.dataframe(users_df, use_container_width=True, hide_index=True)
    else:
        st.info("No registered users found.")

    st.divider()
    st.subheader("📈 Submission status breakdown")

    if total_submissions:
        status_df = pd.DataFrame({
            "Status": ["Approved", "Pending", "Rejected", "Changes Requested"],
            "Count": [approved, pending, rejected, changes],
        })
        st.bar_chart(status_df.set_index("Status"))

    st.divider()
    st.subheader("🕒 Recent platform activity")

    if all_logs:
        logs_df = pd.DataFrame(all_logs)

        if "timestamp" in logs_df.columns:
            logs_df = logs_df.sort_values("timestamp", ascending=False)

        st.dataframe(logs_df.head(50), use_container_width=True, hide_index=True)
    else:
        st.info("No platform activity recorded yet.")


# ============================================================
# ROLE-SPECIFIC SUMMARY
# ============================================================

if role != "Admin":
    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Total submissions", len(items))
    c2.metric(
        "Pending",
        sum(1 for item in items if item.get("status") == "Pending"),
    )
    c3.metric(
        "Approved",
        sum(1 for item in items if item.get("status") == "Approved"),
    )
    c4.metric(
        "Changes requested",
        sum(1 for item in items if item.get("status") == "Changes Requested"),
    )

    st.divider()


# ============================================================
# NAVIGATION
# ============================================================

if role == "Admin":
    visible_tabs = [
        "Admin overview",
        "Rulebook",
        "Account management",
    ]
elif role == "Creator":
    visible_tabs = [
        "Review content",
        "Image review",
        "Approval queue",
        "Rulebook",
    ]
elif role == "Reviewer":
    visible_tabs = [
        "Approval queue",
        "Review content",
        "Image review",
        "Rulebook",
    ]
else:
    visible_tabs = [
        "Approval queue",
        "Insights",
        "Review content",
        "Image review",
        "Rulebook",
    ]


selected_tab = st.radio(
    "Navigation",
    visible_tabs,
    horizontal=True,
    label_visibility="collapsed",
)


# ============================================================
# ADMIN OVERVIEW
# ============================================================

if selected_tab == "Admin overview":
    if not is_designated_admin(user):
        st.error("Only the designated administrator can access this page.")
        st.stop()

    show_admin_overview()


# ============================================================
# CONTENT REVIEW
# ============================================================

elif selected_tab == "Review content":
    st.header("📝 Content compliance review")

    st.write(
        "Check marketing copy, campaign descriptions and other "
        "brand communication against your approved brand rules."
    )

    title = st.text_input(
        "Content title",
        placeholder="Example: Summer campaign announcement",
    )

    uploaded_doc = st.file_uploader(
        "Upload a document (optional)",
        type=["txt", "pdf", "docx"],
        key="content_document",
    )

    content = st.text_area(
        "Enter content to review",
        height=220,
        placeholder="Paste your content here...",
    )

    if uploaded_doc is not None:
        try:
            extracted, _doc_note = uploads.extract_text(
                uploaded_doc.name,
                uploaded_doc.getvalue(),
            )

            if extracted:
                content = st.text_area(
                    "Extracted document content",
                    value=extracted,
                    height=220,
                    key="extracted_content",
                )
        except Exception as exc:
            st.error(f"Document extraction failed: {exc}")

    if st.button(
        "Run BrandGuard review",
        type="primary",
        use_container_width=True,
    ):
        if not content.strip():
            st.warning("Enter some content before reviewing.")
        else:
            with st.spinner("Checking brand compliance..."):
                result = run_content_review(
                    content,
                    title or "Untitled content",
                )

            st.session_state["latest_content_review"] = result

    result = st.session_state.get("latest_content_review")

    if result:
        ai_result = result.get("ai_result", {
            "status": "failed",
            "error": "AI verification status is missing.",
            "findings": [],
        })

        render_review_results(
            result.get("content", ""),
            result.get("findings", []),
            ai_result,
            "BrandGuard content review",
        )

        if role == "Creator":
            if st.button(
                "Submit content for approval",
                type="primary",
                disabled=not bool(result.get("content")),
            ):
                item = {
                    "id": str(uuid.uuid4()),
                    "type": "Content",
                    "title": result["title"],
                    "content": result["content"],
                    "findings": result["findings"],
                    "ai_status": ai_result.get("status", "failed"),
                    "ai_error": ai_result.get("error", ""),
                    "status": "Pending",
                    "created_by": user.get("name"),
                    "created_at": now(),
                    "comments": [],
                    "history": [{
                        "action": "Submitted for approval",
                        "timestamp": now(),
                        "by": user.get("name"),
                    }],
                }

                save_submission(item)
                queue_feedback(
                    "submitted",
                    "Submitted, status: Pending review",
                )
                st.session_state.pop("latest_content_review", None)
                st.rerun()

        if st.button("Apply suggested fixes"):
            try:
                fixed = apply_fixes(
                    result["content"],
                    result["findings"],
                )

                if isinstance(fixed, dict):
                    fixed = fixed.get("text", fixed.get("content", ""))

                st.session_state["fixed_content"] = str(fixed)
                st.success("Suggested fixes generated.")
            except Exception as exc:
                st.error(f"Could not apply fixes: {exc}")

    if "fixed_content" in st.session_state:
        st.subheader("Revised content")
        st.text_area(
            "Suggested revised version",
            value=st.session_state["fixed_content"],
            height=200,
        )


# ============================================================
# IMAGE REVIEW
# ============================================================

elif selected_tab == "Image review":
    st.header("🖼️ Image compliance review")

    st.write(
        "Upload a campaign image to check its visible text, "
        "brand consistency and accessibility information."
    )

    image_file = st.file_uploader(
        "Upload image",
        type=["png", "jpg", "jpeg", "webp"],
        key="brand_image",
    )

    image_title = st.text_input(
        "Image or campaign title",
        key="image_title",
    )

    alt_text = st.text_input(
        "Alternative text",
        placeholder="Describe the image for accessibility",
    )

    if image_file:
        st.image(
            image_file,
            caption="Uploaded campaign image",
            use_container_width=True,
        )

    if st.button(
        "Analyze image",
        type="primary",
        use_container_width=True,
    ):
        if image_file is None:
            st.warning("Upload an image first.")
        else:
            try:
                with st.spinner("Analyzing image..."):
                    raw_image_result = image_analysis.analyze_image(
                        image_file.getvalue(),
                        alt_text=alt_text,
                        rulebook=get_rulebook(),
                    )

                    if not isinstance(raw_image_result, dict):
                        raw_image_result = {
                            "status": "unverified",
                            "error": "Image analysis returned an invalid result.",
                        }

                    raw_status = str(
                        raw_image_result.get("status", "")
                    ).strip().lower()

                    # Only an explicit completed result counts as verified.
                    if raw_status in [
                        "completed", "success", "successful", "passed", "ok"
                    ]:
                        normalized_image_status = "completed"
                    else:
                        normalized_image_status = "unverified"

                    st.session_state["latest_image_review"] = {
                        "title": image_title or image_file.name,
                        "filename": image_file.name,
                        "findings": add_display_fields(
                            normalize_findings(raw_image_result)
                        ),
                        "result": raw_image_result,
                        "alt_text": alt_text,
                        "status": normalized_image_status,
                        "error": raw_image_result.get(
                            "error",
                            "" if normalized_image_status == "completed"
                            else "Image AI verification did not complete.",
                        ),
                        "extracted_text": raw_image_result.get(
                            "extracted_text", ""
                        ),
                        "text_source": raw_image_result.get(
                            "text_source", ""
                        ),
                        "colour_coverage": raw_image_result.get(
                            "colour_coverage"
                        ),
                    }

            except Exception as exc:
                st.session_state["latest_image_review"] = {
                    "title": image_title or (
                        image_file.name if image_file else "Image review"
                    ),
                    "filename": image_file.name if image_file else "",
                    "findings": [],
                    "result": {},
                    "alt_text": alt_text,
                    "status": "unverified",
                    "error": str(exc),
                    "extracted_text": "",
                    "text_source": "",
                    "colour_coverage": None,
                }

    image_review = st.session_state.get("latest_image_review")

    if image_review:
        image_status = image_review.get("status", "unverified")
        findings = image_review.get("findings", [])

        ai_result_for_image = {
            "status": image_status,
            "error": image_review.get("error", ""),
        }

        st.subheader("✨ Image review results")

        render_ai_banner(
            image_status,
            image_review.get("error", ""),
        )

        render_score_ring(findings, image_status)

        if image_review.get("extracted_text"):
            st.subheader("📝 Text found inside the image")
            st.caption(
                "Text extraction source: "
                + str(image_review.get("text_source") or "Image analysis")
            )
            st.markdown(
                '<div class="bg-draft">'
                + html.escape(str(image_review["extracted_text"]))
                + '</div>',
                unsafe_allow_html=True,
            )
        else:
            st.info(
                "No text was extracted from the image, or text extraction "
                "was not available."
            )

        if image_review.get("colour_coverage") is not None:
            try:
                coverage = float(image_review["colour_coverage"])
                st.metric(
                    "Approved brand colour coverage",
                    f"{coverage:.0f}%",
                )
            except (TypeError, ValueError):
                st.caption(
                    "Colour coverage: "
                    + str(image_review["colour_coverage"])
                )

        if image_review.get("alt_text"):
            st.caption("Accessibility alt text: " + image_review["alt_text"])
        else:
            st.warning("No alternative text was provided.")

        st.subheader("🔎 Image findings")

        if not findings:
            if image_status == "completed":
                st.success("No image compliance findings were identified.")
            else:
                st.warning(
                    "No verified image result is available. "
                    "This does not mean the image is Safe."
                )
        else:
            for index, finding in enumerate(findings, start=1):
                render_finding_card(finding, index)

        if role == "Creator":
            if st.button(
                "Submit image for approval",
                type="primary",
            ):
                item = {
                    "id": str(uuid.uuid4()),
                    "type": "Image",
                    "title": image_review["title"],
                    "filename": image_review["filename"],
                    "alt_text": image_review["alt_text"],
                    "findings": findings,
                    "status": "Pending",
                    "ai_status": image_status,
                    "ai_error": image_review.get("error", ""),
                    "extracted_text": image_review.get("extracted_text", ""),
                    "text_source": image_review.get("text_source", ""),
                    "colour_coverage": image_review.get("colour_coverage"),
                    "created_by": user.get("name"),
                    "created_at": now(),
                    "comments": [],
                    "history": [{
                        "action": "Image submitted for approval",
                        "timestamp": now(),
                        "by": user.get("name"),
                    }],
                }

                save_submission(item)
                queue_feedback(
                    "submitted",
                    "Submitted, status: Pending review",
                )
                st.session_state.pop("latest_image_review", None)
                st.rerun()


# ============================================================
# APPROVAL QUEUE
# ============================================================

elif selected_tab == "Approval queue":
    st.header("📋 Approval queue")

    items = get_workspace().get("items", [])

    if not items:
        st.info("No submissions are available in this workspace.")

    for item in reversed(items):
        with st.container(border=True):
            st.subheader(item.get("title", "Untitled"))

            st.caption(
                f"{item.get('type', 'Content')} · "
                f"Submitted by {item.get('created_by', 'Unknown')} · "
                f"{item.get('created_at', '')}"
            )

            render_status_badge(item.get("status", "Pending"))

            st.write(f"**Findings:** {finding_count(item)}")

            ai_status = str(item.get("ai_status", "failed")).lower()

            if ai_status not in ["completed", "success", "passed"]:
                st.warning(
                    "UNVERIFIED — AI verification did not complete. "
                    "This submission cannot be approved."
                )
            else:
                st.caption("✓ AI check completed")

            with st.expander("View submission"):
                if item.get("content"):
                    st.text_area(
                        "Submitted content",
                        value=item["content"],
                        height=150,
                        key=f"content_{item['id']}",
                        disabled=True,
                    )

                if item.get("extracted_text"):
                    st.markdown("**Text found inside image**")
                    st.write(item["extracted_text"])

                st.write("**Findings**")

                for finding_index, finding in enumerate(
                    item.get("findings", []),
                    start=1,
                ):
                    render_finding_card(finding, finding_index)

                st.write("**Comments**")

                for comment in item.get("comments", []):
                    st.write(
                        f"- {comment.get('by', 'User')}: "
                        f"{comment.get('text', '')} "
                        f"({comment.get('timestamp', '')})"
                    )

                st.write("**Revision history**")

                for history in item.get("history", []):
                    st.write(
                        f"- {history.get('action', '')} — "
                        f"{history.get('by', '')} "
                        f"({history.get('timestamp', '')})"
                    )

            comment = st.text_input(
                "Add comment",
                key=f"comment_{item['id']}",
            )

            if st.button("Post comment", key=f"post_{item['id']}"):
                if comment.strip():
                    item.setdefault("comments", []).append({
                        "by": user.get("name"),
                        "text": comment.strip(),
                        "timestamp": now(),
                    })
                    save_workspace()
                    st.success("Comment added.")
                    st.rerun()
                else:
                    st.warning("Write a comment first.")

            if role in ["Reviewer", "Manager"]:
                st.write("**Review decision**")

                can_decide = item.get("status") in [
                    "Pending",
                    "Changes Requested",
                ]

                # Fail-closed approval gate.
                can_approve = (
                    can_decide
                    and ai_status in ["completed", "success", "passed"]
                )

                col1, col2, col3 = st.columns(3)

                with col1:
                    if st.button(
                        "Approve",
                        key=f"approve_{item['id']}",
                        disabled=not can_approve,
                    ):
                        # Recheck at action time.
                        current_ai_status = str(
                            item.get("ai_status", "failed")
                        ).lower()

                        if current_ai_status not in [
                            "completed", "success", "passed"
                        ]:
                            st.error(
                                "Cannot approve: AI verification is unverified."
                            )
                        else:
                            item["status"] = "Approved"
                            item.setdefault("history", []).append({
                                "action": "Approved",
                                "by": user.get("name"),
                                "timestamp": now(),
                            })

                            save_workspace()
                            add_log("Submission approved", item["title"])

                            queue_feedback(
                                "approved",
                                "Approved",
                            )
                            st.rerun()

                with col2:
                    if st.button(
                        "Request changes",
                        key=f"changes_{item['id']}",
                        disabled=not can_decide,
                    ):
                        item["status"] = "Changes Requested"
                        item.setdefault("history", []).append({
                            "action": "Changes requested",
                            "by": user.get("name"),
                            "timestamp": now(),
                        })

                        save_workspace()
                        add_log("Changes requested", item["title"])

                        queue_feedback(
                            "changes",
                            "Changes requested",
                        )
                        st.rerun()

                with col3:
                    if role == "Manager":
                        if st.button(
                            "Reject",
                            key=f"reject_{item['id']}",
                            disabled=not can_decide,
                        ):
                            item["status"] = "Rejected"
                            item.setdefault("history", []).append({
                                "action": "Rejected",
                                "by": user.get("name"),
                                "timestamp": now(),
                            })

                            save_workspace()
                            add_log("Submission rejected", item["title"])

                            queue_feedback(
                                "rejected",
                                "Rejected",
                            )
                            st.rerun()


# ============================================================
# INSIGHTS
# ============================================================

elif selected_tab == "Insights":
    st.header("📊 BrandGuard insights")

    if role != "Manager":
        st.warning("Insights are available in the Manager dashboard.")
        st.stop()

    items = get_workspace().get("items", [])
    total = len(items)

    approved = sum(1 for item in items if item.get("status") == "Approved")
    pending = sum(1 for item in items if item.get("status") == "Pending")
    rejected = sum(1 for item in items if item.get("status") == "Rejected")
    changes = sum(
        1 for item in items
        if item.get("status") == "Changes Requested"
    )

    a, b, c, d = st.columns(4)
    a.metric("Total", total)
    b.metric("Approved", approved)
    c.metric("Pending", pending)
    d.metric("Rejected", rejected)

    if total:
        status_df = pd.DataFrame({
            "Status": [
                "Approved",
                "Pending",
                "Rejected",
                "Changes Requested",
            ],
            "Count": [
                approved,
                pending,
                rejected,
                changes,
            ],
        })

        st.subheader("Submission status")
        st.bar_chart(status_df.set_index("Status"))

        finding_rows = []

        for item in items:
            for finding in item.get("findings", []):
                if isinstance(finding, dict):
                    finding_rows.append({
                        "Title": item.get("title", ""),
                        "Severity": finding.get("severity", "Unspecified"),
                        "Category": finding.get("category", "Unspecified"),
                    })

        if finding_rows:
            finding_df = pd.DataFrame(finding_rows)

            st.subheader("Finding categories")
            st.bar_chart(finding_df["Category"].value_counts())

            st.subheader("Finding severity")
            st.bar_chart(finding_df["Severity"].value_counts())
    else:
        st.info("Submit content to start generating insights.")

    logs = get_workspace().get("logs", [])

    if logs:
        st.subheader("Recent activity")
        st.dataframe(
            pd.DataFrame(logs[::-1]),
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# RULEBOOK
# ============================================================

elif selected_tab == "Rulebook":
    st.header("📘 Brand rulebook")
    rulebook = get_rulebook()

    if not rulebook:
        st.info("No rulebook data was returned.")
    else:
        st.write(
            "The rulebook contains the approved standards "
            "used during BrandGuard checks."
        )

        if isinstance(rulebook, dict):
            for section, value in rulebook.items():
                with st.expander(str(section).replace("_", " ").title()):
                    if isinstance(value, (dict, list)):
                        st.json(value)
                    else:
                        st.write(value)
        else:
            st.json(rulebook)


# ============================================================
# ACCOUNT MANAGEMENT — DESIGNATED ADMIN ONLY
# ============================================================

elif selected_tab == "Account management":
    st.header("⚙️ Account and role management")

    if not is_designated_admin(user):
        st.error("Only the designated administrator can manage accounts.")
        st.stop()

    st.write(
        "Manage account access. Each person keeps one account "
        "and can switch between Creator, Reviewer and Manager."
    )

    try:
        accounts = database.list_users(actor_user_id=user["id"])

        if not accounts:
            st.info("No accounts found.")

        for account in accounts or []:
            account_id = str(account.get("id"))
            account_name = account.get("name", "User")
            account_email = account.get("email", "")
            account_email_lower = account_email.strip().lower()

            with st.container(border=True):
                st.subheader(account_name)
                st.caption(account_email)

                if account_email_lower == ADMIN_EMAIL:
                    st.success("Designated BrandGuard Admin")
                    st.write("Roles: Creator, Reviewer, Manager, Admin")
                    continue

                st.write("Current roles: Creator, Reviewer, Manager")

                st.caption(
                    "All standard roles are automatically enabled "
                    "for every registered account."
                )

                active = bool(account.get("active", True))
                st.write(
                    "Account status:",
                    "Active" if active else "Inactive",
                )

                new_active = st.toggle(
                    "Account active",
                    value=active,
                    key=f"active_{account_id}",
                )

                if new_active != active:
                    try:
                        success, message = database.set_user_active(
                            user_id=account_id,
                            active=new_active,
                            actor_user_id=user["id"],
                        )

                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)

                    except Exception as exc:
                        st.error(f"Could not update account: {exc}")

    except Exception as exc:
        st.error(f"Account management error: {exc}")


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "BrandGuard | AI-powered brand compliance and approval platform"
)

st.caption(
    f"Signed in as {user.get('name', 'User')} · "
    f"Active workspace: {role} · "
    f"{'Guest session' if is_guest() else 'Registered account'}"
)
