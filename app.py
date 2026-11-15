import json
import os
import time
import uuid

import pandas as pd
import streamlit as st

import database
from engine import load_rulebook, review, apply_fixes, diff_html, merge_findings
from ai_check import run_ai_check
import uploads
import ui


# ---------------- page setup ----------------

st.set_page_config(
    page_title="BrandGuard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(ui.CSS, unsafe_allow_html=True)

# Button interaction and visual feedback.
# Decorative layers must not block real Streamlit controls.
st.markdown(
    """
    <style>
    /* Streamlit dims "stale" elements while a click is processing. Disable that fade. */
    [data-stale="true"],
    [data-stale="true"] *,
    .stApp [data-testid="stElementContainer"][data-stale],
    .stApp[data-teststate="running"] [data-testid="stVerticalBlock"] > div {
        opacity: 1 !important;
        filter: none !important;
        -webkit-filter: none !important;
        transition: none !important;
    }

    /* Main application must remain interactive. */
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    [data-testid="stMainBlockContainer"],
    [data-testid="stAppViewBlockContainer"] {
        filter: none !important;
        -webkit-filter: none !important;
        opacity: 1 !important;
        pointer-events: auto !important;
    }

    /* Decorative pseudo-elements must not intercept clicks. */
    [data-testid="stAppViewContainer"]::before,
    [data-testid="stAppViewContainer"]::after,
    [data-testid="stMain"]::before,
    [data-testid="stMain"]::after,
    .hero::before,
    .hero::after,
    .orb,
    .orb::before,
    .orb::after,
    .ring,
    .ring::before,
    .ring::after {
        pointer-events: none !important;
    }

    /* Keep Streamlit buttons clickable. */
    [data-testid="stButton"] {
        position: relative !important;
        pointer-events: auto !important;
    }

    [data-testid="stButton"] > button {
        position: relative !important;
        pointer-events: auto !important;
        cursor: pointer !important;
        transition:
            transform 0.15s ease,
            box-shadow 0.15s ease,
            background-color 0.15s ease,
            border-color 0.15s ease !important;
    }

    /* Hover movement. */
    [data-testid="stButton"] > button:hover:not(:disabled) {
        transform: translateY(-2px) !important;
        box-shadow: 0 5px 14px rgba(0, 0, 0, 0.15) !important;
    }

    /* Press feedback. */
    [data-testid="stButton"] > button:active:not(:disabled) {
        transform: scale(0.97) !important;
    }

    /* Keyboard focus. */
    [data-testid="stButton"] > button:focus-visible {
        outline: 2px solid #6C5CE7 !important;
        outline-offset: 3px !important;
    }

    [data-testid="stButton"] > button:disabled {
        cursor: not-allowed !important;
        opacity: 0.55 !important;
    }

    /* Other interactive controls. */
    [data-testid="stCheckbox"],
    [data-testid="stRadio"],
    [data-testid="stSelectbox"],
    [data-testid="stTextInput"],
    [data-testid="stTextArea"],
    [data-testid="stFileUploader"],
    [data-testid="stDownloadButton"],
    [data-testid="stTabs"] {
        pointer-events: auto !important;
    }

    @media (prefers-reduced-motion: reduce) {
        [data-testid="stButton"] > button {
            transition: none !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
)

RB = load_rulebook()


SAMPLES = {
    "Messy launch post": (
        "BrightKart is the BEST store in India!!! Our users get "
        "100% guaranteed delivery. Free shipping on orders above "
        "Rs 399, and 30-day returns. Click here to shop now, hurry!"
    ),
    "Plan price post": (
        "Our new Plus plan is just Rs 399 per month. Amazing deals "
        "for customers who love cheap prices."
    ),
    "Image post": (
        "Meet our summer range ![](summer.png) "
        "Fastest delivery in the city."
    ),
    "Clean post": (
        "Free shipping on orders above Rs 499. "
        "Easy 7-day returns. Shop the spring offer today."
    ),
}


ROLE_ICON = {
    "Creator": "✍️",
    "Reviewer": "🔍",
    "Manager": "📈",
    "Admin": "🛠️"
}


# ---------------- shared database storage ----------------

def load():
    """Load shared BrandGuard data from Turso."""

    data = database.load_data()

    if not isinstance(data, dict):
        raise RuntimeError(
            "BrandGuard could not load valid database data. "
            "Your existing data has not been reset. "
            "Check the Turso database connection."
        )

    data.setdefault("items", [])
    data.setdefault("log", [])

    if not isinstance(data["items"], list):
        raise RuntimeError(
            "Invalid submissions data returned by the database. "
            "No data was changed."
        )

    if not isinstance(data["log"], list):
        raise RuntimeError(
            "Invalid insights data returned by the database. "
            "No data was changed."
        )

    return data


def save(data):
    """Save shared records to Turso."""

    if not isinstance(data, dict):
        raise ValueError("Invalid database data.")

    if not isinstance(data.get("items"), list):
        raise ValueError("Invalid submissions data.")

    if not isinstance(data.get("log"), list):
        raise ValueError("Invalid insights data.")

    database.save_data(data)
    load_cached.clear()


@st.cache_data(ttl=5, show_spinner=False)
def load_cached():
    """Short-lived cached copy for display only. Writes always use load()."""

    return load()


def now():
    return time.strftime("%Y-%m-%d %H:%M")


POPPER_HTML = (
    "<style>"
    "@keyframes bgpop{0%{transform:translate(0,0) scale(.4);opacity:1}"
    "100%{transform:translate(var(--x),var(--y)) scale(1.4) rotate(360deg);opacity:0}}"
    ".bgpop{position:fixed;bottom:12vh;font-size:2rem;pointer-events:none;"
    "z-index:99999;opacity:0;animation:bgpop 1.6s ease-out forwards}"
    "</style>"
)
_POP_ITEMS = [
    ("🎉", "-35vw", "-55vh", "left:50%"), ("🎊", "35vw", "-60vh", "left:50%"),
    ("🎉", "-20vw", "-70vh", "left:50%"), ("🎊", "20vw", "-65vh", "left:50%"),
    ("✨", "-45vw", "-45vh", "left:50%"), ("✨", "45vw", "-50vh", "left:50%"),
    ("🎉", "-5vw", "-75vh", "left:50%"), ("🎊", "8vw", "-72vh", "left:50%"),
]


def party_poppers():
    """Confetti burst (CSS only). Pure string concat: no % formatting."""
    parts = [POPPER_HTML]
    for emoji, x, y, pos in _POP_ITEMS:
        parts.append(
            '<span class="bgpop" style="' + pos + ';--x:' + x + ';--y:' + y + '">'
            + emoji + "</span>"
        )
    st.markdown("".join(parts), unsafe_allow_html=True)


def new_id():
    return uuid.uuid4().hex


def add_insights(data, findings):
    """Add findings to the persistent insights history."""

    for finding in findings:
        data["log"].append({
            "rule": finding.get("rule", "Unknown"),
            "category": finding.get("category", "Other"),
            "dismissed": False,
            "time": now()
        })


def delete_submission(data, submission_id):
    """Permanently delete one submission from the shared queue."""

    original_count = len(data["items"])

    data["items"] = [
        item
        for item in data["items"]
        if str(item.get("id")) != str(submission_id)
    ]

    return len(data["items"]) < original_count


# ---------------- API settings ----------------

def _setting(name, default=""):
    try:
        value = st.secrets.get(name, default)

        if value:
            return value

    except Exception:
        pass

    return os.environ.get(name, default)


def api_key():
    return (
        _setting("GEMINI_API_KEY")
        or _setting("OPENAI_API_KEY")
        or _setting("OPENROUTER_API_KEY")
    )


def has_key():
    return bool(api_key())


def model_name():
    return _setting(
        "OPENROUTER_MODEL",
        "openrouter/free"
    )


def vision_model_name():
    return (
        _setting("OPENROUTER_VISION_MODEL", "")
        or model_name()
    )


# ---------------- submission helpers ----------------

def get_draft_id(title, author):
    """Generate a stable draft ID per creator and title."""

    if "draft_ids" not in st.session_state:
        st.session_state["draft_ids"] = {}

    key = (
        str(author).strip().lower()
        + "::"
        + str(title).strip().lower()
    )

    if key not in st.session_state["draft_ids"]:
        st.session_state["draft_ids"][key] = new_id()

    return st.session_state["draft_ids"][key]


def find_submission(data, draft_id, title, author):
    """Find a submission using its permanent ID."""

    for item in data["items"]:
        if item.get("draft_id") == draft_id:
            return item

    for item in data["items"]:
        if (
            not item.get("draft_id")
            and item.get("title") == title
            and item.get("author") == author
        ):
            item["draft_id"] = draft_id
            return item

    return None


def latest_ai_status(item):
    versions = item.get("versions", [])

    if not versions:
        return "legacy / unknown"

    return str(
        versions[-1].get(
            "ai_review",
            "legacy / unknown"
        )
    ).lower()


def is_ai_unverified(item):
    return latest_ai_status(item) == "unverified"


def image_draft_id(author, filename, size):
    """Stable image submission identity per creator and uploaded file."""

    identity = (
        str(author).strip().lower()
        + "::"
        + str(filename)
        + "::"
        + str(size)
    )

    return "image_" + uuid.uuid5(
        uuid.NAMESPACE_URL,
        identity
    ).hex


# ---------------- demo data ----------------

def seed():
    """Add demo submissions without duplicating existing records."""

    data = load()

    existing = {
        item.get("title")
        for item in data["items"]
    }

    plan = [
        ("Messy launch post", "Pending review"),
        ("Plan price post", "Changes requested"),
        ("Clean post", "Approved"),
        ("Image post", "Pending review")
    ]

    added = 0

    for name, status in plan:

        demo_title = name + " (demo)"

        if demo_title in existing:
            continue

        original = SAMPLES[name]
        findings = review(original, RB)

        for k, finding in enumerate(findings):
            data["log"].append({
                "rule": finding["rule"],
                "category": finding["category"],
                "dismissed": (
                    finding["rule"] in ("TN1", "TN4")
                    and k % 2 == 0
                ),
                "time": now()
            })

        fixed = apply_fixes(original, findings)

        comments = []

        if status == "Approved":
            comments.append({
                "who": "Demo reviewer",
                "role": "Reviewer",
                "time": now(),
                "action": "Approve",
                "msg": "Looks good."
            })

        elif status == "Changes requested":
            comments.append({
                "who": "Demo reviewer",
                "role": "Reviewer",
                "time": now(),
                "action": "Request changes",
                "msg": "Please double-check the price."
            })

        data["items"].append({
            "id": uuid.uuid4().hex[:6],
            "draft_id": new_id(),
            "title": demo_title,
            "author": "Demo creator",
            "status": status,
            "comments": comments,
            "versions": [
                {
                    "v": 1,
                    "text": original,
                    "time": now(),
                    "issues": len(findings),
                    "by": "Demo creator",
                    "ai_review": "demo / not run"
                },
                {
                    "v": 2,
                    "text": fixed,
                    "time": now(),
                    "issues": len(review(fixed, RB)),
                    "by": "Demo creator",
                    "ai_review": "demo / not run"
                }
            ]
        })

        existing.add(demo_title)
        added += 1

    if added:
        save(data)

    return added


# ---------------- sidebar ----------------

with st.sidebar:

    st.markdown("## 🛡️ BrandGuard")
    st.caption("Automation suggests. Humans decide.")

    role = st.selectbox(
        "Your role (demo mode)",
        list(ROLE_ICON),
        key="active_role"
    )

    who = st.text_input(
        "Display name",
        "Krish",
        key="display_name"
    )

    st.markdown(
        ui.profile_card(who, role, ROLE_ICON[role]),
        unsafe_allow_html=True
    )

    if st.button(
        "🎬 Demo data",
        use_container_width=True
    ):
        try:
            added = seed()

            if added:
                st.success(
                    f"Loaded {added} demo submission(s)."
                )
            else:
                st.info(
                    "Demo examples are already loaded. "
                    "No duplicates were added."
                )

        except Exception as e:
            st.error("Could not save demo data: %s" % e)

    if role == "Admin":

        st.markdown("**🛠️ Admin controls**")

        if not st.session_state.get("reset_pending", False):

            if st.button(
                "🧹 Reset all data",
                use_container_width=True
            ):
                st.session_state["reset_pending"] = True
                st.rerun()

        else:

            st.warning(
                "This clears submissions, comments and insights "
                "for everyone using BrandGuard."
            )

            confirm_col, cancel_col = st.columns(2)

            if confirm_col.button(
                "Confirm reset",
                type="primary"
            ):
                try:
                    save({
                        "items": [],
                        "log": []
                    })

                    for key in (
                        "res",
                        "img_res",
                        "celebrate",
                        "draft_ids",
                        "submitted_rid",
                        "delete_pending_id"
                    ):
                        st.session_state.pop(key, None)

                    st.session_state["reset_pending"] = False

                    st.success("All data was reset.")
                    st.rerun()

                except Exception as e:
                    st.error(
                        "Reset failed. Database error: %s" % e
                    )

            if cancel_col.button("Cancel"):
                st.session_state["reset_pending"] = False
                st.rerun()

    else:
        st.caption(
            "Reset is available to Admin only. "
            "Switch the role above to test it."
        )

    st.markdown(
        ui.privacy_card(),
        unsafe_allow_html=True
    )

    st.caption("Sample brand: " + RB["company"])

    st.caption(
        "Demo roles are for judging only; "
        "they are not authenticated accounts."
    )


# ---------------- header ----------------

st.markdown(ui.hero(), unsafe_allow_html=True)
st.markdown(ui.steps(), unsafe_allow_html=True)

T_review, T_image, T_queue, T_insights, T_rulebook = st.tabs([
    "✍️ Review content",
    "🖼️ Image review",
    "📥 Approval queue",
    "📊 Insights",
    "📘 Rulebook"
])


# ---------------- tab 1: review ----------------

with T_review:

    left, right = st.columns(
        [3, 2],
        gap="large"
    )

    with left:

        sample = st.radio(
            "Quick samples",
            ["✏️ Write my own"] + list(SAMPLES),
            horizontal=True
        )

        title = st.text_input(
            "Content title",
            sample if sample in SAMPLES else "My new post",
            key="t_" + sample
        )

        tkey = "x_" + sample

        up_doc = st.file_uploader(
            "📎 Or upload a document (.txt, .docx, .pdf) and review its text",
            type=["txt", "docx", "pdf"],
            key="doc_up"
        )

        is_document = up_doc is not None

        if up_doc is not None:

            sig = (
                up_doc.name,
                up_doc.size
            )

            if st.session_state.get("doc_sig") != sig:

                st.session_state["doc_sig"] = sig

                try:

                    doc_text, doc_note = uploads.extract_text(
                        up_doc.name,
                        up_doc.getvalue()
                    )

                    st.session_state[tkey] = doc_text

                    st.session_state["doc_msg"] = (
                        "ok",
                        "Loaded %d characters from %s. %s"
                        % (
                            len(doc_text),
                            up_doc.name,
                            doc_note
                        )
                    )

                except Exception as e:

                    st.session_state["doc_msg"] = (
                        "err",
                        "Could not read %s: %s"
                        % (up_doc.name, e)
                    )

            kind, msg_doc = st.session_state.get(
                "doc_msg",
                ("", "")
            )

            if kind == "ok":
                st.success(msg_doc)

            elif kind == "err":
                st.error(msg_doc)

        else:

            st.session_state.pop("doc_sig", None)
            st.session_state.pop("doc_msg", None)

        document_error = (
            is_document
            and st.session_state.get(
                "doc_msg",
                ("", "")
            )[0] != "ok"
        )

        if tkey in st.session_state:

            text = st.text_area(
                "Draft content",
                height=170,
                key=tkey,
                placeholder="Paste a post, caption, email or ad copy here…"
            )

        else:

            text = st.text_area(
                "Draft content",
                SAMPLES.get(sample, ""),
                height=170,
                key=tkey,
                placeholder="Paste a post, caption, email or ad copy here…"
            )

        if has_key():

            use_ai = st.checkbox(
                "🤖 Run multilingual AI moderation "
                "(marketing: brand governance; documents: safety only)",
                True
            )

        else:

            use_ai = False

            st.warning(
                "AI moderation is not configured. "
                "This run will check only your local rulebook. "
                "Add OPENAI_API_KEY or OPENROUTER_API_KEY "
                "to Streamlit secrets."
            )

        if st.button(
            "🚀 Run review",
            type="primary",
            disabled=document_error
        ):

            if not text.strip():

                st.warning("Add some text first.")

            else:

                st.toast("Review started…", icon="🔍")
                with st.spinner("🔍 Reviewing your content. The AI check can take up to ~30 seconds…"):
                    findings = (
                        []
                        if is_document
                        else review(text, RB)
                    )

                    ai_status = "rules_only"
                    ai_error = ""

                    if use_ai:

                        try:

                            ai_findings = run_ai_check(
                                text,
                                RB,
                                api_key(),
                                model_name(),
                                brand_mode=not is_document
                            )

                            findings = merge_findings(
                                findings,
                                ai_findings
                            )

                            ai_status = "completed"

                        except Exception as e:

                            ai_status = "unverified"
                            ai_error = str(e)

                draft_id = get_draft_id(title, who)

                st.session_state["res"] = (
                    time.time_ns(),
                    text,
                    findings,
                    title,
                    ai_status,
                    ai_error,
                    draft_id
                )

    with right:

        st.markdown(
            ui.panel(
                "🧭 What gets checked",
                "🎭 <b>Tone</b> and pressure wording<br>"
                "📖 <b>Terminology</b> and brand name<br>"
                "⚠️ <b>Claims</b> with no approved proof<br>"
                "🧾 <b>Facts</b> vs approved prices and policies<br>"
                "♿ <b>Accessibility</b> (alt text, link text)<br>"
                "📎 <b>Documents</b> (.txt, .docx, .pdf) and "
                "🖼️ <b>images</b> (see the Image review tab)<br><br>"
                "<small>Every finding cites its rule ID and source.</small>"
            ),
            unsafe_allow_html=True
        )

    # ---------------- review results ----------------

    if "res" in st.session_state:

        (
            rid,
            text0,
            F,
            title0,
            ai_status,
            ai_error,
            draft_id
        ) = st.session_state["res"]

        if ai_status == "completed":

            st.markdown(
                ui.score_card(F),
                unsafe_allow_html=True
            )

            st.success(
                "AI moderation completed. Findings are AI-assisted "
                "and should be confirmed by a human reviewer."
            )

            st.caption(
                "A clean result means these checks found no issue; "
                "it is not a guarantee of perfect detection."
            )

        elif ai_status == "unverified":

            st.error(
                "UNVERIFIED — the AI moderation did not complete. "
                "This is not a Safe result."
            )

            st.caption(
                "Reason: " + ui.E(ai_error[:500])
            )

            st.info(
                "Local rulebook findings are shown below, but general "
                "multilingual moderation could not be confirmed."
            )

        else:

            st.warning(
                "RULE-ONLY CHECK — AI moderation was not run. "
                "No overall Safe result is being claimed."
            )

        applied = {
            i
            for i, finding in enumerate(F)
            if (
                finding["replacement"] is not None
                and st.session_state.get(
                    "ap%s_%d" % (rid, i),
                    True
                )
                and not st.session_state.get(
                    "dm%s_%d" % (rid, i),
                    False
                )
            )
        }

        fixed = apply_fixes(
            text0,
            F,
            {
                i
                for i in range(len(F))
                if i not in applied
            }
        )

        a, b = st.columns(
            2,
            gap="large"
        )

        a.markdown(
            ui.annotate(text0, F),
            unsafe_allow_html=True
        )

        b.markdown(
            ui.panel(
                "✨ Suggested rewrite (meaning kept, nothing auto-applied)",
                diff_html(text0, fixed)
            ),
            unsafe_allow_html=True
        )

        if F:

            st.markdown(
                "#### 🔎 Findings: why each was flagged"
            )

            for i, finding in enumerate(F):

                st.markdown(
                    ui.finding_card(finding),
                    unsafe_allow_html=True
                )

                x1, x2, _ = st.columns(
                    [1.3, 1.8, 3]
                )

                if finding["replacement"] is not None:

                    x1.checkbox(
                        "Apply fix",
                        True,
                        key="ap%s_%d" % (rid, i)
                    )

                x2.checkbox(
                    "Dismiss (rule unclear / n.a.)",
                    key="dm%s_%d" % (rid, i)
                )

        st.markdown("#### 📝 Final text")

        final = st.text_area(
            "Edit freely before sending for approval",
            fixed,
            height=120,
            key="final_%s" % rid
        )

        already_submitted = (
            st.session_state.get("submitted_rid") == rid
        )

        if role == "Creator":

            submit_clicked = st.button(
                "📤 Submit for approval",
                type="primary",
                disabled=already_submitted,
                key="submit_" + str(rid)
            )

            if already_submitted:
                st.success(
                    "This review result has already been submitted."
                )

        else:

            st.info(
                "Only the Creator role can submit drafts. "
                "Switch to Creator to test submission."
            )

            submit_clicked = False

        if submit_clicked:

            if not final.strip():

                st.warning("Final text cannot be empty.")

            else:

                st.toast("Submitting your draft…", icon="⏳")

                try:

                    data = load()

                    item = find_submission(
                        data,
                        draft_id,
                        title0,
                        who
                    )

                    if item is None:

                        item = {
                            "id": uuid.uuid4().hex[:6],
                            "draft_id": draft_id,
                            "title": title0,
                            "author": who,
                            "status": "Pending review",
                            "versions": [],
                            "comments": []
                        }

                        data["items"].append(item)

                    item.setdefault("comments", [])
                    item.setdefault("versions", [])

                    if (
                        item["versions"]
                        and item["versions"][-1].get("review_id")
                        == str(rid)
                    ):

                        st.session_state["submitted_rid"] = rid
                        st.info("This review has already been saved.")

                    else:

                        version_number = len(item["versions"]) + 1

                        item["versions"].append({
                            "v": version_number,
                            "text": final,
                            "time": now(),
                            "issues": len(F),
                            "by": who,
                            "ai_review": ai_status,
                            "ai_error": (
                                ai_error[:500]
                                if ai_status == "unverified"
                                else ""
                            ),
                            "review_id": str(rid)
                        })

                        item["status"] = "Pending review"

                        add_insights(data, F)

                        save(data)

                        st.session_state["submitted_rid"] = rid

                        if any(
                            finding["severity"] == "Critical"
                            for finding in F
                        ):
                            st.warning(
                                "🚫 This draft has a safety flag. "
                                "A human reviewer must look at it before anything is published."
                            )

                        if ai_status == "unverified":
                            st.warning(
                                "⚠️ This submission has been saved for human review, "
                                "but its AI moderation is UNVERIFIED. "
                                "It cannot be approved until a successful AI review "
                                "is completed."
                            )

                        st.balloons()

                        party_poppers()

                        st.toast(
                            "Submitted as version %d. Open the Approval queue."
                            % version_number,
                            icon="📤"
                        )

                        st.success(
                            "🎉 Successfully submitted! "
                            "Your draft is now in the Approval Queue."
                        )

                except Exception as e:

                    st.error(
                        "Submission could not be saved. "
                        "Your review is still available on this page. "
                        "Database error: %s" % e
                    )


# ---------------- tab 2: image review ----------------

with T_image:

    st.markdown("#### 🖼️ Image review")

    st.caption(
        "Upload a post image or banner. BrandGuard runs quick local checks "
        "(alt text, size, contrast, brand colours) and, when configured, "
        "an AI vision review that reads text inside images and checks "
        "for unsafe content."
    )

    img = st.file_uploader(
        "Upload an image (.png, .jpg, .jpeg, .webp)",
        type=["png", "jpg", "jpeg", "webp"],
        key="img_up"
    )

    alt = st.text_input(
        "Alt text: describe the image for screen-reader users",
        key="img_alt"
    )

    current_image_sig = None

    if img is not None:

        current_image_sig = (
            img.name,
            img.size
        )

        if st.session_state.get("img_sig") != current_image_sig:

            st.session_state["img_sig"] = current_image_sig
            st.session_state.pop("img_res", None)

        st.image(
            img.getvalue(),
            caption=img.name,
            width=360
        )

        if st.button(
            "🔎 Run image review",
            type="primary",
            key="run_image_review"
        ):

            st.toast("Image review started…", icon="🔎")
            with st.spinner("🔎 Reviewing your image. The AI check can take up to ~30 seconds…"):
                data = img.getvalue()

                local = []
                vf = []
                extracted = ""
                vstatus = "not_configured"
                verr = ""

                try:

                    local = uploads.local_image_checks(
                        data,
                        alt,
                        RB
                    )

                    if has_key():

                        try:

                            extracted, vf = uploads.vision_review(
                                data,
                                RB,
                                api_key(),
                                vision_model_name(),
                                alt
                            )

                            vstatus = "completed"

                        except Exception as e:

                            vstatus = "unverified"
                            verr = str(e)

                    tf = (
                        review(extracted, RB)
                        if extracted.strip()
                        else []
                    )

                    st.session_state["img_res"] = {
                        "rid": time.time_ns(),
                        "sig": current_image_sig,
                        "name": img.name,
                        "alt": alt,
                        "local": local,
                        "vf": vf,
                        "vstatus": vstatus,
                        "verr": verr,
                        "extracted": extracted,
                        "tf": tf
                    }

                except Exception as e:

                    st.error(
                        "Could not review this image: %s" % e
                    )

    else:

        st.session_state.pop("img_sig", None)
        st.session_state.pop("img_res", None)

        st.info(
            "Upload an image to start. No image is stored; "
            "it is only used for this review."
        )

    r = st.session_state.get("img_res")

    if (
        r
        and current_image_sig is not None
        and r.get("sig") == current_image_sig
    ):

        allF = (
            r["local"]
            + r["vf"]
            + r["tf"]
        )

        st.markdown("---")

        st.markdown(
            "**Result for:** %s" % ui.E(r["name"])
        )

        if r["vstatus"] == "completed":

            st.markdown(
                ui.score_card(allF),
                unsafe_allow_html=True
            )

            st.success(
                "AI image review completed. Findings are AI-assisted "
                "and should be confirmed by a human reviewer."
            )

        elif r["vstatus"] == "unverified":

            st.error(
                "UNVERIFIED — the AI image review did not complete. "
                "This is not a Safe result."
            )

            st.caption(
                "Reason: " + ui.E(r["verr"][:500])
            )

            st.info(
                "Local image checks are shown below, but unsafe visual "
                "content and text inside the image could not be confirmed."
            )

        else:

            st.warning(
                "LOCAL-ONLY CHECK — AI image review was not run. "
                "No overall Safe result is being claimed."
            )

        if r["extracted"].strip():

            st.markdown(
                ui.annotate(
                    r["extracted"],
                    r["tf"]
                ).replace(
                    "Your draft, highlighted (hover a highlight)",
                    "Text found inside the image"
                ),
                unsafe_allow_html=True
            )

        if r["local"] or r["vf"]:

            st.markdown("#### 🔎 Image findings")

            for finding in r["local"] + r["vf"]:

                st.markdown(
                    ui.finding_card(finding),
                    unsafe_allow_html=True
                )

        elif r["vstatus"] == "completed":

            st.success(
                "No image issues found by the checks that ran."
            )

        if r["tf"]:

            st.markdown(
                "#### 🔤 Findings in the text inside the image"
            )

            for finding in r["tf"]:

                st.markdown(
                    ui.finding_card(finding),
                    unsafe_allow_html=True
                )

        if role == "Creator":

            image_submit_key = (
                "img_submit_" + str(r["rid"])
            )

            image_already_submitted = st.session_state.get(
                image_submit_key,
                False
            )

            if st.button(
                "📤 Submit image review for approval",
                type="primary",
                key="image_submit_button_" + str(r["rid"]),
                disabled=image_already_submitted
            ):

                st.toast("Submitting image review…", icon="⏳")

                try:

                    data = load()

                    t_img = "Image: " + r["name"]

                    draft_id = image_draft_id(
                        who,
                        r["sig"][0],
                        r["sig"][1]
                    )

                    item = find_submission(
                        data,
                        draft_id,
                        t_img,
                        who
                    )

                    if item is None:

                        item = {
                            "id": uuid.uuid4().hex[:6],
                            "draft_id": draft_id,
                            "title": t_img,
                            "author": who,
                            "status": "Pending review",
                            "versions": [],
                            "comments": []
                        }

                        data["items"].append(item)

                    item.setdefault("versions", [])
                    item.setdefault("comments", [])

                    if (
                        item["versions"]
                        and item["versions"][-1].get("image_review_id")
                        == str(r["rid"])
                    ):

                        st.session_state[image_submit_key] = True

                        st.info(
                            "This image review has already been submitted."
                        )

                    else:

                        version_number = len(item["versions"]) + 1

                        item["versions"].append({
                            "v": version_number,
                            "time": now(),
                            "issues": len(allF),
                            "by": who,
                            "ai_review": r["vstatus"],
                            "ai_error": (
                                r["verr"][:500]
                                if r["vstatus"] == "unverified"
                                else ""
                            ),
                            "image_review_id": str(r["rid"]),
                            "text": (
                                "[IMAGE] %s | Alt text: %s | Text found in image: %s"
                                % (
                                    r["name"],
                                    r["alt"] or "(none)",
                                    r["extracted"] or "(none)"
                                )
                            )
                        })

                        item["status"] = "Pending review"

                        add_insights(data, allF)

                        save(data)

                        st.session_state[image_submit_key] = True

                        st.balloons()

                        party_poppers()

                        st.toast(
                            "Image submitted. Open the Approval queue.",
                            icon="📤"
                        )

                        st.success(
                            "🎉 Image review submitted successfully! "
                            "It is now in the Approval Queue. "
                            "(The image itself is not stored.)"
                        )

                        if r["vstatus"] == "unverified":

                            st.warning(
                                "AI image moderation is UNVERIFIED. "
                                "This image cannot be approved until "
                                "a successful AI image review is completed."
                            )

                except Exception as e:

                    st.error(
                        "Image submission could not be saved: %s" % e
                    )

            if st.session_state.get(image_submit_key, False):

                st.success(
                    "This image review has already been submitted."
                )

        else:

            st.info(
                "Only the Creator role can submit. "
                "Switch to Creator to test submission."
            )


# ---------------- tab 3: approval queue ----------------

with T_queue:

    _flash = st.session_state.pop("queue_flash", None)

    if _flash:
        st.toast(_flash[0], icon=_flash[1])
        st.success(_flash[0])

    if st.session_state.pop("celebrate", False):

        st.balloons()

        party_poppers()

        st.toast(
            "Approved! Ready to publish.",
            icon="🎉"
        )

    try:

        d = load_cached()

    except Exception as e:

        st.error(
            "Could not load the approval queue: %s" % e
        )

        d = {
            "items": [],
            "log": []
        }

    if not d["items"]:

        st.markdown(
            ui.empty(
                "📭",
                "Nothing to review yet",
                "Submit a draft from the Review tab, "
                "or click 'Demo data' in the sidebar."
            ),
            unsafe_allow_html=True
        )

    for it in d["items"]:

        it.setdefault("versions", [])
        it.setdefault("comments", [])

        submission_id = str(it.get("id", ""))

        with st.container(border=True):

            st.markdown(
                "**%s** &nbsp; %s &nbsp; "
                "<small>v%d · by %s</small>"
                % (
                    ui.E(it.get("title", "Untitled")),
                    ui.status_chip(
                        it.get("status", "Pending review")
                    ),
                    len(it["versions"]),
                    ui.E(it.get("author", "Unknown"))
                ),
                unsafe_allow_html=True
            )

            latest_status = latest_ai_status(it)

            if latest_status == "unverified":

                st.error(
                    "⚠️ Latest AI moderation: UNVERIFIED. "
                    "Approval is disabled until a successful AI review "
                    "is completed in a new version."
                )

            elif latest_status == "rules_only":

                st.warning(
                    "Latest review used local rules only. "
                    "AI moderation was not run."
                )

            elif latest_status == "completed":

                st.caption(
                    "Latest AI moderation: completed. "
                    "Human review is still required."
                )

            with st.expander(
                "Revision history and comments"
            ):

                for k, v in enumerate(it["versions"]):

                    review_label = v.get(
                        "ai_review",
                        "legacy / unknown"
                    )

                    st.markdown(
                        "**🕘 Version %d** · %s · %s · "
                        "%d issues · AI: %s"
                        % (
                            v.get("v", k + 1),
                            v.get("time", ""),
                            ui.E(v.get("by", "Unknown")),
                            v.get("issues", 0),
                            ui.E(review_label)
                        )
                    )

                    if k > 0:

                        st.markdown(
                            ui.panel(
                                "Changes from previous version",
                                diff_html(
                                    it["versions"][k - 1].get(
                                        "text",
                                        ""
                                    ),
                                    v.get("text", "")
                                )
                            ),
                            unsafe_allow_html=True
                        )

                    else:

                        st.markdown(
                            ui.panel(
                                "Original",
                                ui.E(v.get("text", ""))
                            ),
                            unsafe_allow_html=True
                        )

                    if v.get("ai_error"):

                        st.caption(
                            "AI error: "
                            + ui.E(v["ai_error"])
                        )

                for c in it["comments"]:

                    st.markdown(
                        "💬 **%s** (%s, %s) · %s: %s"
                        % (
                            ui.E(c.get("who", "Unknown")),
                            ui.E(c.get("role", "")),
                            ui.E(c.get("time", "")),
                            ui.E(c.get("action", "")),
                            ui.E(c.get("msg", ""))
                        )
                    )

            if role in ("Reviewer", "Manager", "Admin"):

                msg = st.text_input(
                    "Comment for the creator",
                    key="cm" + submission_id
                )

                if role == "Reviewer":

                    decisions = (
                        ("✅ Approve", "Approved"),
                        ("✏️ Request changes", "Changes requested")
                    )

                    st.caption(
                        "Reviewer permissions: approve or request changes. "
                        "You can also delete an unnecessary queue item."
                    )

                else:

                    decisions = (
                        ("✅ Approve", "Approved"),
                        ("✏️ Request changes", "Changes requested"),
                        ("⛔ Reject", "Rejected")
                    )

                    if role == "Manager":

                        st.caption(
                            "Manager permissions: oversee submissions "
                            "and approve, request changes or reject."
                        )

                    else:

                        st.caption(
                            "Admin permissions: full review decisions "
                            "and session administration."
                        )

                cols = st.columns(len(decisions) + 1)

                for col, (label, status) in zip(
                    cols,
                    decisions
                ):

                    approval_blocked = (
                        status == "Approved"
                        and is_ai_unverified(it)
                    )

                    if col.button(
                        label,
                        key=label + submission_id,
                        disabled=approval_blocked,
                        use_container_width=True
                    ):

                        try:

                            latest_data = load()

                            latest_item = next(
                                (
                                    x
                                    for x in latest_data["items"]
                                    if str(x.get("id")) == submission_id
                                ),
                                None
                            )

                            if latest_item is None:

                                st.error(
                                    "This submission no longer exists. "
                                    "Refresh the page."
                                )

                                st.stop()

                            latest_item.setdefault("comments", [])
                            latest_item.setdefault("versions", [])

                            if (
                                status == "Approved"
                                and is_ai_unverified(latest_item)
                            ):

                                st.error(
                                    "Approval blocked. The latest AI "
                                    "moderation is UNVERIFIED."
                                )

                                st.stop()

                            latest_item["status"] = status

                            latest_item["comments"].append({
                                "who": who,
                                "role": role,
                                "time": now(),
                                "action": label.split(" ", 1)[1],
                                "msg": msg or "-"
                            })

                            save(latest_data)

                            if status == "Approved":
                                st.balloons()
                                party_poppers()
                                st.toast(
                                    "Approved! Ready to publish.",
                                    icon="🎉"
                                )
                                st.success(
                                    "🎉 Approved successfully! "
                                    "The status chip updates on your next click."
                                )

                            else:
                                if status == "Changes requested":
                                    st.session_state["queue_flash"] = (
                                        "Changes requested successfully.",
                                        "✏️"
                                    )
                                else:
                                    st.session_state["queue_flash"] = (
                                        "Submission rejected.",
                                        "⛔"
                                    )
                                st.rerun()

                        except Exception as e:

                            st.error(
                                "Decision could not be saved: %s" % e
                            )

                # ---------------- delete submission ----------------

                delete_col = cols[-1]

                if delete_col.button(
                    "🗑️ Delete",
                    key="delete_" + submission_id,
                    use_container_width=True
                ):

                    st.session_state["delete_pending_id"] = submission_id
                    st.rerun()

                if (
                    st.session_state.get("delete_pending_id")
                    == submission_id
                ):

                    st.warning(
                        "Are you sure you want to permanently delete "
                        "this submission, including its revision history "
                        "and comments? This cannot be undone."
                    )

                    confirm_col, cancel_col = st.columns(2)

                    if confirm_col.button(
                        "Yes, permanently delete",
                        key="confirm_delete_" + submission_id,
                        type="primary",
                        use_container_width=True
                    ):

                        try:

                            latest_data = load()

                            deleted = delete_submission(
                                latest_data,
                                submission_id
                            )

                            if not deleted:

                                st.error(
                                    "This submission was already deleted "
                                    "or no longer exists."
                                )

                            else:

                                save(latest_data)

                                st.session_state.pop(
                                    "delete_pending_id",
                                    None
                                )

                                st.session_state["queue_flash"] = (
                                    "Submission deleted from the queue.",
                                    "🗑️"
                                )

                            st.rerun()

                        except Exception as e:

                            st.error(
                                "Could not delete this submission: %s" % e
                            )

                    if cancel_col.button(
                        "Cancel",
                        key="cancel_delete_" + submission_id,
                        use_container_width=True
                    ):

                        st.session_state.pop(
                            "delete_pending_id",
                            None
                        )

                        st.rerun()

            else:

                st.caption(
                    "🔒 Creator access is view-only in the approval queue. "
                    "Switch to Reviewer to make decisions."
                )


# ---------------- tab 4: insights ----------------

with T_insights:

    if role not in ("Manager", "Admin"):

        st.info(
            "Insights are available to Manager and Admin roles. "
            "Switch roles in the sidebar to view them."
        )

    else:

        try:

            d = load_cached()
            log = pd.DataFrame(d["log"])

        except Exception as e:

            st.error(
                "Could not load insights: %s" % e
            )

            log = pd.DataFrame()

            d = {
                "items": [],
                "log": []
            }

        if log.empty:

            st.markdown(
                ui.empty(
                    "📊",
                    "No insights yet",
                    "Submit a few reviews, or click 'Demo data' "
                    "in the sidebar to see repeated mistakes."
                ),
                unsafe_allow_html=True
            )

        else:

            st.markdown(
                ui.metric_cards([
                    (
                        sum(
                            len(i.get("versions", []))
                            for i in d["items"]
                        ),
                        "📝 Drafts submitted"
                    ),
                    (
                        len(log),
                        "🔎 Issues found"
                    ),
                    (
                        sum(
                            1
                            for i in d["items"]
                            if i.get("status") == "Approved"
                        ),
                        "✅ Approved items"
                    )
                ]),
                unsafe_allow_html=True
            )

            if "rule" in log.columns:

                g = (
                    log.groupby("rule")
                    .agg(
                        hits=("rule", "count"),
                        dismissed=("dismissed", "sum")
                    )
                    .reset_index()
                )

                g["unclear_%"] = (
                    100 * g["dismissed"] / g["hits"]
                ).round(0)

                c1, c2 = st.columns(
                    2,
                    gap="large"
                )

                with c1:

                    st.markdown(
                        "#### 🔁 Most repeated mistakes (by rule)"
                    )

                    st.bar_chart(
                        g.set_index("rule")["hits"],
                        color="#6C5CE7"
                    )

                with c2:

                    st.markdown(
                        "#### 🧩 Issues by category"
                    )

                    if "category" in log.columns:

                        st.bar_chart(
                            log.groupby("category").size(),
                            color="#15AABF"
                        )

                st.markdown(
                    "#### 🤔 Rules people keep dismissing "
                    "(the guideline may be unclear)"
                )

                st.dataframe(
                    g.sort_values(
                        "unclear_%",
                        ascending=False
                    ),
                    hide_index=True
                )

            else:

                st.info(
                    "No rule-level insight data is available yet."
                )


# ---------------- tab 5: rulebook ----------------

with T_rulebook:

    st.markdown(
        "#### 📘 Approved rulebook: the source of truth"
    )

    st.caption(
        "Every finding cites a rule ID from here. "
        "If nothing here supports a claim, it is marked "
        "'Unverified: needs human check'."
    )

    st.markdown(
        ui.panel(
            "🎭 Tone",
            ui.E(RB["tone"]["summary"])
        ),
        unsafe_allow_html=True
    )

    c1, c2 = st.columns(
        2,
        gap="large"
    )

    with c1:

        st.markdown("**📖 Terminology**")

        st.dataframe(
            pd.DataFrame([
                {
                    "ID": t["id"],
                    "Avoid": ", ".join(t["bad"]),
                    "Use": t["preferred"]
                }
                for t in RB["terminology"]
            ]),
            hide_index=True
        )

    with c2:

        st.markdown("**🧾 Approved facts**")

        st.dataframe(
            pd.DataFrame([
                {
                    "ID": f["id"],
                    "Statement": f["statement"]
                }
                for f in RB["facts"]
            ]),
            hide_index=True
        )

    st.markdown(
        "**⚠️ Approved evidence for claims:** "
        + (
            ", ".join(RB["approved_claims"])
            or "none"
        )
    )

    with st.expander("View raw rulebook (JSON)"):

        st.json(RB)


# ---------------- footer ----------------

st.markdown(
    '<div class="foot">Built by Team Binary Brains · '
    'AI-assisted development is disclosed in the README</div>',
    unsafe_allow_html=True
)