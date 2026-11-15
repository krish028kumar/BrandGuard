import json, os, time, uuid
import pandas as pd
import streamlit as st
from engine import load_rulebook, review, apply_fixes, diff_html, merge_findings
from ai_check import run_ai_check
import ui

st.set_page_config(page_title="BrandGuard", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")
st.markdown(ui.CSS, unsafe_allow_html=True)

RB = load_rulebook()
STORE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "store.json")
SAMPLES = {
    "Messy launch post": "BrightKart is the BEST store in India!!! Our users get 100% guaranteed delivery. Free shipping on orders above Rs 399, and 30-day returns. Click here to shop now, hurry!",
    "Plan price post": "Our new Plus plan is just Rs 399 per month. Amazing deals for customers who love cheap prices.",
    "Image post": "Meet our summer range ![](summer.png) Fastest delivery in the city.",
    "Clean post": "Free shipping on orders above Rs 499. Easy 7-day returns. Shop the spring offer today.",
}
ROLE_ICON = {"Creator": "✍️", "Reviewer": "🔍", "Manager": "📈", "Admin": "🛠️"}

def load():
    try:
        with open(STORE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"items": [], "log": []}

def save(d):
    try:
        with open(STORE, "w", encoding="utf-8") as f:
            json.dump(d, f)
    except Exception:
        pass

def now():
    return time.strftime("%Y-%m-%d %H:%M")

def _setting(name, default=""):
    try:
        value = st.secrets.get(name, default)
        if value:
            return value
    except Exception:
        pass
    return os.environ.get(name, default)


def api_key():
    return _setting("OPENROUTER_API_KEY")


def has_key():
    return bool(api_key())


def model_name():
    return _setting("OPENROUTER_MODEL", "openrouter/free")

def seed():
    d = load()
    if any(i["title"].endswith("(demo)") for i in d["items"]):
        return
    plan = [("Messy launch post", "Pending review"), ("Plan price post", "Changes requested"),
            ("Clean post", "Approved"), ("Image post", "Pending review")]
    for name, status in plan:
        t = SAMPLES[name]
        F = review(t, RB)
        for k, f in enumerate(F):
            d["log"].append({"rule": f["rule"], "category": f["category"],
                             "dismissed": f["rule"] in ("TN1", "TN4") and k % 2 == 0, "time": now()})
        fixed = apply_fixes(t, F)
        com = []
        if status == "Approved":
            com = [{"who": "Demo reviewer", "role": "Reviewer", "time": now(), "action": "Approve", "msg": "Looks good."}]
        elif status == "Changes requested":
            com = [{"who": "Demo reviewer", "role": "Reviewer", "time": now(), "action": "Request changes", "msg": "Please double-check the price."}]
        d["items"].append({"id": uuid.uuid4().hex[:6], "title": name + " (demo)", "author": "Demo creator",
                           "status": status, "comments": com,
                           "versions": [{"v": 1, "text": t, "time": now(), "issues": len(F), "by": "Demo creator"},
                                        {"v": 2, "text": fixed, "time": now(), "issues": len(review(fixed, RB)), "by": "Demo creator"}]})
    save(d)

# ---------------- sidebar ----------------
with st.sidebar:
    st.markdown("## 🛡️ BrandGuard")
    st.caption("Automation suggests. Humans decide.")
    role = st.selectbox("Your role", list(ROLE_ICON))
    who = st.text_input("Display name", "Krish")
    st.markdown(ui.profile_card(who, role, ROLE_ICON[role]), unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    if c1.button("🎬 Demo data"):
        seed()
        st.toast("Demo data loaded (sample reviews, clearly marked 'demo').", icon="🎬")
    if c2.button("🧹 Reset"):
        save({"items": [], "log": []})
        st.toast("All reviews cleared.", icon="🧹")
    st.markdown(ui.privacy_card(), unsafe_allow_html=True)
    st.caption("Sample brand: " + RB["company"])

# ---------------- header ----------------
st.markdown(ui.hero(), unsafe_allow_html=True)
st.markdown(ui.steps(), unsafe_allow_html=True)
T = st.tabs(["✍️ Review content", "📥 Approval queue", "📊 Insights", "📘 Rulebook"])

# ---------------- tab 1: review ----------------
with T[0]:
    left, right = st.columns([3, 2], gap="large")
    with left:
        sample = st.radio("Quick samples", ["✏️ Write my own"] + list(SAMPLES), horizontal=True)
        title = st.text_input("Content title", sample if sample in SAMPLES else "My new post", key="t_" + sample)
        text = st.text_area("Draft content", SAMPLES.get(sample, ""), height=170, key="x_" + sample,
                            placeholder="Paste a post, caption, email or ad copy here…")
        if has_key():
            use_ai = st.checkbox(
                "🤖 Run multilingual AI moderation + brand check (OpenRouter; sends this text to an external service)",
                True
            )
        else:
            use_ai = False
            st.warning(
                "OpenRouter AI moderation is not configured. This run will check only your local rulebook, "
                "so it cannot be marked fully verified. Add OPENROUTER_API_KEY to Streamlit secrets."
            )
        if st.button("🚀 Run review", type="primary"):
            if not text.strip():
                st.warning("Add some text first.")
            else:
                F0 = review(text, RB)
                ai_status = "rules_only"
                ai_error = ""
                with st.spinner("Running rulebook checks and multilingual AI moderation…" if use_ai else "Checking the local rulebook…"):
                    if use_ai:
                        try:
                            ai_findings = run_ai_check(text, RB, api_key(), model_name())
                            F0 = merge_findings(F0, ai_findings)
                            ai_status = "completed"
                        except Exception as e:
                            ai_status = "unverified"
                            ai_error = str(e)
                st.session_state["res"] = (time.time_ns(), text, F0, title, ai_status, ai_error)
    with right:
        st.markdown(ui.panel("🧭 What gets checked",
            "🎭 <b>Tone</b> and pressure wording<br>📖 <b>Terminology</b> and brand name<br>"
            "⚠️ <b>Claims</b> with no approved proof<br>🧾 <b>Facts</b> vs approved prices and policies<br>"
            "♿ <b>Accessibility</b> (alt text, link text)<br><br><small>Every finding cites its rule ID and source.</small>"),
            unsafe_allow_html=True)

    if "res" in st.session_state:
        rid, text0, F, title0, ai_status, ai_error = st.session_state["res"]
        if ai_status == "completed":
            st.markdown(ui.score_card(F), unsafe_allow_html=True)
            st.success("AI moderation completed. Findings are AI-assisted and should be confirmed by a human reviewer.")
            st.caption("A clean result means these checks found no issue; it is not a guarantee of perfect detection.")
        elif ai_status == "unverified":
            st.error("UNVERIFIED — the AI moderation did not complete. This is not a Safe result.")
            st.caption("Reason: " + ui.E(ai_error[:500]))
            st.info("Local rulebook findings are shown below, but general multilingual moderation could not be confirmed.")
        else:
            st.warning("RULE-ONLY CHECK — AI moderation was not run. No overall Safe result is being claimed.")
        applied = {i for i, f in enumerate(F) if f["replacement"] is not None
                   and st.session_state.get("ap%s_%d" % (rid, i), True)
                   and not st.session_state.get("dm%s_%d" % (rid, i), False)}
        fixed = apply_fixes(text0, F, {i for i in range(len(F)) if i not in applied})

        a, b = st.columns(2, gap="large")
        a.markdown(ui.annotate(text0, F), unsafe_allow_html=True)
        b.markdown(ui.panel("✨ Suggested rewrite (meaning kept, nothing auto-applied)", diff_html(text0, fixed)),
                   unsafe_allow_html=True)

        if F:
            st.markdown("#### 🔎 Findings: why each was flagged")
            for i, f in enumerate(F):
                st.markdown(ui.finding_card(f), unsafe_allow_html=True)
                x1, x2, _ = st.columns([1.3, 1.8, 3])
                if f["replacement"] is not None:
                    x1.checkbox("Apply fix", True, key="ap%s_%d" % (rid, i))
                x2.checkbox("Dismiss (rule unclear / n.a.)", key="dm%s_%d" % (rid, i))

        st.markdown("#### 📝 Final text")
        final = st.text_area("Edit freely before sending for approval", fixed, height=120,
                             key="final_%s_%d" % (rid, hash(fixed)))

        if st.button("📤 Submit for approval", type="primary"):
            d = load()
            for i, f in enumerate(F):
                d["log"].append({"rule": f["rule"], "category": f["category"],
                                 "dismissed": bool(st.session_state.get("dm%s_%d" % (rid, i), False)), "time": now()})
            item = next((x for x in d["items"] if x["title"] == title0), None)
            if item is None:
                item = {"id": uuid.uuid4().hex[:6], "title": title0, "author": who, "status": "Pending review",
                        "versions": [], "comments": []}
                d["items"].append(item)
            item["versions"].append({"v": len(item["versions"]) + 1, "text": final, "time": now(),
                                     "issues": len(F), "by": who, "ai_review": ai_status})
            item["status"] = "Pending review"
            save(d)
            if any(f["severity"] == "Critical" for f in F):
                st.warning("🚫 This draft has a safety flag. A human reviewer must look at it before anything is published.")
            st.toast("Submitted as version %d. Open the Approval queue." % len(item["versions"]), icon="📤")
            st.success("Submitted! Switch your role to Reviewer and open the Approval queue tab.")

# ---------------- tab 2: queue ----------------
with T[1]:
    if st.session_state.pop("celebrate", False):
        st.balloons()
        st.toast("Approved! Ready to publish.", icon="🎉")
    d = load()
    if not d["items"]:
        st.markdown(ui.empty("📭", "Nothing to review yet",
                    "Submit a draft from the Review tab, or click 'Demo data' in the sidebar."), unsafe_allow_html=True)
    for it in d["items"]:
        with st.container(border=True):
            st.markdown("**%s** &nbsp; %s &nbsp; <small>v%d · by %s</small>" % (
                ui.E(it["title"]), ui.status_chip(it["status"]), len(it["versions"]), ui.E(it["author"])),
                unsafe_allow_html=True)
            with st.expander("Revision history and comments"):
                for k, v in enumerate(it["versions"]):
                    review_label = v.get("ai_review", "legacy / unknown")
                    st.markdown("**🕘 Version %d** · %s · %s · %d issues · AI: %s" %
                                (v["v"], v["time"], v["by"], v["issues"], ui.E(review_label)))
                    if k > 0:
                        st.markdown(ui.panel("Changes from previous version", diff_html(it["versions"][k - 1]["text"], v["text"])),
                                    unsafe_allow_html=True)
                    else:
                        st.markdown(ui.panel("Original", ui.E(v["text"])), unsafe_allow_html=True)
                for c in it["comments"]:
                    st.markdown("💬 **%s** (%s, %s) · %s: %s" % (ui.E(c["who"]), c["role"], c["time"], c["action"], ui.E(c["msg"])))
            if role in ("Reviewer", "Manager", "Admin"):
                msg = st.text_input("Comment for the creator", key="cm" + it["id"])
                b1, b2, b3 = st.columns(3)
                for col, label, status in ((b1, "✅ Approve", "Approved"), (b2, "✏️ Request changes", "Changes requested"),
                                           (b3, "⛔ Reject", "Rejected")):
                    if col.button(label, key=label + it["id"]):
                        it["status"] = status
                        it["comments"].append({"who": who, "role": role, "time": now(),
                                               "action": label.split(" ", 1)[1], "msg": msg or "-"})
                        save(d)
                        if status == "Approved":
                            st.session_state["celebrate"] = True
                        st.rerun()
            else:
                st.caption("🔒 Only Reviewers, Managers and Admins can decide. Change your role in the sidebar.")

# ---------------- tab 3: insights ----------------
with T[2]:
    d = load()
    log = pd.DataFrame(d["log"])
    if log.empty:
        st.markdown(ui.empty("📊", "No insights yet",
                    "Submit a few reviews, or click 'Demo data' in the sidebar to see repeated mistakes."), unsafe_allow_html=True)
    else:
        st.markdown(ui.metric_cards([
            (sum(len(i["versions"]) for i in d["items"]), "📝 Drafts submitted"),
            (len(log), "🔎 Issues found"),
            (sum(1 for i in d["items"] if i["status"] == "Approved"), "✅ Approved items")]), unsafe_allow_html=True)
        g = log.groupby("rule").agg(hits=("rule", "count"), dismissed=("dismissed", "sum")).reset_index()
        g["unclear_%"] = (100 * g["dismissed"] / g["hits"]).round(0)
        c1, c2 = st.columns(2, gap="large")
        with c1:
            st.markdown("#### 🔁 Most repeated mistakes (by rule)")
            st.bar_chart(g.set_index("rule")["hits"], color="#6C5CE7")
        with c2:
            st.markdown("#### 🧩 Issues by category")
            st.bar_chart(log.groupby("category").size(), color="#15AABF")
        st.markdown("#### 🤔 Rules people keep dismissing (the guideline may be unclear)")
        st.dataframe(g.sort_values("unclear_%", ascending=False), hide_index=True)

# ---------------- tab 4: rulebook ----------------
with T[3]:
    st.markdown("#### 📘 Approved rulebook: the source of truth")
    st.caption("Every finding cites a rule ID from here. If nothing here supports a claim, it is marked 'Unverified: needs human check'.")
    st.markdown(ui.panel("🎭 Tone", ui.E(RB["tone"]["summary"])), unsafe_allow_html=True)
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown("**📖 Terminology**")
        st.dataframe(pd.DataFrame([{"ID": t["id"], "Avoid": ", ".join(t["bad"]), "Use": t["preferred"]} for t in RB["terminology"]]),
                     hide_index=True)
    with c2:
        st.markdown("**🧾 Approved facts**")
        st.dataframe(pd.DataFrame([{"ID": f["id"], "Statement": f["statement"]} for f in RB["facts"]]), hide_index=True)
    st.markdown("**⚠️ Approved evidence for claims:** " + (", ".join(RB["approved_claims"]) or "none"))
    with st.expander("View raw rulebook (JSON)"):
        st.json(RB)

st.markdown('<div class="foot">Built by Team Binary Brains · AI-assisted development is disclosed in the README</div>',
            unsafe_allow_html=True)
