import json, os, time, uuid
import pandas as pd
import streamlit as st
from engine import load_rulebook, review, apply_fixes, diff_html, merge_findings
from ai_check import run_ai_check
import uploads
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

# Streamlit Community Cloud uses temporary container storage. Keep this demo's
# workflow data in the active browser session instead of relying on store.json.
SESSION_STORE_KEY = "brandguard_store"

def load():
    if SESSION_STORE_KEY not in st.session_state:
        st.session_state[SESSION_STORE_KEY] = {"items": [], "log": []}
    data = st.session_state[SESSION_STORE_KEY]
    data.setdefault("items", [])
    data.setdefault("log", [])
    return data

def save(d):
    # Streamlit session state survives reruns for the active browser session.
    st.session_state[SESSION_STORE_KEY] = d

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

def vision_model_name():
    # Image review needs a model that accepts images. Set OPENROUTER_VISION_MODEL in Streamlit secrets.
    return _setting("OPENROUTER_VISION_MODEL", "") or model_name()

def seed():
    """Add any missing demo examples without duplicating existing demo records."""
    d = load()
    existing = {i.get("title") for i in d["items"]}
    plan = [("Messy launch post", "Pending review"), ("Plan price post", "Changes requested"),
            ("Clean post", "Approved"), ("Image post", "Pending review")]
    added = 0
    for name, status in plan:
        demo_title = name + " (demo)"
        if demo_title in existing:
            continue
        t = SAMPLES[name]
        findings = review(t, RB)
        for k, finding in enumerate(findings):
            d["log"].append({"rule": finding["rule"], "category": finding["category"],
                             "dismissed": finding["rule"] in ("TN1", "TN4") and k % 2 == 0,
                             "time": now()})
        fixed = apply_fixes(t, findings)
        comments = []
        if status == "Approved":
            comments = [{"who": "Demo reviewer", "role": "Reviewer", "time": now(),
                         "action": "Approve", "msg": "Looks good."}]
        elif status == "Changes requested":
            comments = [{"who": "Demo reviewer", "role": "Reviewer", "time": now(),
                         "action": "Request changes", "msg": "Please double-check the price."}]
        d["items"].append({
            "id": uuid.uuid4().hex[:6], "title": demo_title, "author": "Demo creator",
            "status": status, "comments": comments,
            "versions": [
                {"v": 1, "text": t, "time": now(), "issues": len(findings), "by": "Demo creator"},
                {"v": 2, "text": fixed, "time": now(), "issues": len(review(fixed, RB)), "by": "Demo creator"}
            ]
        })
        existing.add(demo_title)
        added += 1
    save(d)
    return added

# ---------------- sidebar ----------------
with st.sidebar:
    st.markdown("## 🛡️ BrandGuard")
    st.caption("Automation suggests. Humans decide.")
    role = st.selectbox("Your role (demo mode)", list(ROLE_ICON), key="active_role")
    who = st.text_input("Display name", "Krish", key="display_name")
    st.markdown(ui.profile_card(who, role, ROLE_ICON[role]), unsafe_allow_html=True)
    if st.button("🎬 Demo data", use_container_width=True):
        added = seed()
        if added:
            st.success(f"Loaded {added} demo submission(s).")
        else:
            st.info("Demo examples are already loaded. No duplicates were added.")
        st.rerun()
    if role == "Admin":
        st.markdown("**🛠️ Admin controls**")
        if not st.session_state.get("reset_pending", False):
            if st.button("🧹 Reset all data", use_container_width=True):
                st.session_state["reset_pending"] = True
                st.rerun()
        else:
            st.warning("This clears submissions, comments and insights in this browser session.")
            confirm_col, cancel_col = st.columns(2)
            if confirm_col.button("Confirm reset", type="primary"):
                save({"items": [], "log": []})
                st.session_state.pop("res", None)
                st.session_state.pop("img_res", None)
                st.session_state.pop("celebrate", None)
                st.session_state["reset_pending"] = False
                st.rerun()
            if cancel_col.button("Cancel"):
                st.session_state["reset_pending"] = False
                st.rerun()
    else:
        st.caption("Reset is available to Admin only. Switch the role above to test it.")
    st.markdown(ui.privacy_card(), unsafe_allow_html=True)
    st.caption("Sample brand: " + RB["company"])
    st.caption("Demo roles are for judging only; they are not authenticated accounts.")

# ---------------- header ----------------
st.markdown(ui.hero(), unsafe_allow_html=True)
st.markdown(ui.steps(), unsafe_allow_html=True)
T_review, T_image, T_queue, T_insights, T_rulebook = st.tabs(
    ["✍️ Review content", "🖼️ Image review", "📥 Approval queue", "📊 Insights", "📘 Rulebook"])

# ---------------- tab 1: review ----------------
with T_review:
    left, right = st.columns([3, 2], gap="large")
    with left:
        sample = st.radio("Quick samples", ["✏️ Write my own"] + list(SAMPLES), horizontal=True)
        title = st.text_input("Content title", sample if sample in SAMPLES else "My new post", key="t_" + sample)

        tkey = "x_" + sample
        up_doc = st.file_uploader("📎 Or upload a document (.txt, .docx, .pdf) and review its text",
                                  type=["txt", "docx", "pdf"], key="doc_up")
        if up_doc is not None:
            sig = (up_doc.name, up_doc.size)
            if st.session_state.get("doc_sig") != sig:
                st.session_state["doc_sig"] = sig
                try:
                    doc_text, doc_note = uploads.extract_text(up_doc.name, up_doc.getvalue())
                    st.session_state[tkey] = doc_text
                    st.session_state["doc_msg"] = ("ok", "Loaded %d characters from %s. %s" % (len(doc_text), up_doc.name, doc_note))
                except Exception as e:
                    st.session_state["doc_msg"] = ("err", "Could not read %s: %s" % (up_doc.name, e))
            kind, msg_doc = st.session_state.get("doc_msg", ("", ""))
            if kind == "ok":
                st.success(msg_doc)
            elif kind == "err":
                st.error(msg_doc)
        else:
            st.session_state.pop("doc_sig", None)
            st.session_state.pop("doc_msg", None)

        if tkey in st.session_state:
            text = st.text_area("Draft content", height=170, key=tkey,
                                placeholder="Paste a post, caption, email or ad copy here…")
        else:
            text = st.text_area("Draft content", SAMPLES.get(sample, ""), height=170, key=tkey,
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
            "♿ <b>Accessibility</b> (alt text, link text)<br>📎 <b>Documents</b> (.txt, .docx, .pdf) and "
            "🖼️ <b>images</b> (see the Image review tab)<br><br><small>Every finding cites its rule ID and source.</small>"),
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

        if role == "Creator":
            submit_clicked = st.button("📤 Submit for approval", type="primary")
        else:
            st.info("Only the Creator role can submit drafts. Switch to Creator to test submission.")
            submit_clicked = False

        if submit_clicked:
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

# ---------------- tab 2: image review ----------------
with T_image:
    st.markdown("#### 🖼️ Image review")
    st.caption("Upload a post image or banner. BrandGuard runs quick local checks (alt text, size, contrast, brand colours) and, "
               "when configured, an AI vision review that reads the text inside the image (English, Hindi, Hinglish) and looks for unsafe content.")
    img = st.file_uploader("Upload an image (.png, .jpg, .jpeg, .webp)", type=["png", "jpg", "jpeg", "webp"], key="img_up")
    alt = st.text_input("Alt text: describe the image for screen-reader users", key="img_alt")
    if img is not None:
        st.image(img.getvalue(), caption=img.name, width=360)
        if st.button("🔎 Run image review", type="primary"):
            data = img.getvalue()
            local, vf, extracted, vstatus, verr = [], [], "", "not_configured", ""
            try:
                local = uploads.local_image_checks(data, alt, RB)
                with st.spinner("Reviewing the image…"):
                    if has_key():
                        try:
                            extracted, vf = uploads.vision_review(data, RB, api_key(), vision_model_name(), alt)
                            vstatus = "completed"
                        except Exception as e:
                            vstatus, verr = "unverified", str(e)
                tf = review(extracted, RB) if extracted.strip() else []
                st.session_state["img_res"] = {"rid": time.time_ns(), "name": img.name, "alt": alt, "local": local,
                                               "vf": vf, "vstatus": vstatus, "verr": verr, "extracted": extracted, "tf": tf}
            except Exception as e:
                st.error("Could not read this image: %s" % e)
    else:
        st.info("Upload an image to start. No image is stored; it is only used for this review.")

    r = st.session_state.get("img_res")
    if r:
        allF = r["local"] + r["vf"] + r["tf"]
        st.markdown("---")
        st.markdown("**Result for:** %s" % ui.E(r["name"]))
        if r["vstatus"] == "completed":
            st.markdown(ui.score_card(allF), unsafe_allow_html=True)
            st.success("AI image review completed. Findings are AI-assisted and should be confirmed by a human reviewer.")
        elif r["vstatus"] == "unverified":
            st.error("UNVERIFIED — the AI image review did not complete. This is not a Safe result.")
            st.caption("Reason: " + ui.E(r["verr"][:500]))
            st.info("Local image checks are shown below, but unsafe visual content and text inside the image could not be confirmed.")
        else:
            st.warning("LOCAL-ONLY CHECK — AI image review was not run (no OPENROUTER_API_KEY). No overall Safe result is being claimed.")
        if r["extracted"].strip():
            st.markdown(ui.annotate(r["extracted"], r["tf"]).replace(
                "Your draft, highlighted (hover a highlight)", "Text found inside the image"), unsafe_allow_html=True)
        if r["local"] or r["vf"]:
            st.markdown("#### 🔎 Image findings")
            for f in r["local"] + r["vf"]:
                st.markdown(ui.finding_card(f), unsafe_allow_html=True)
        elif r["vstatus"] == "completed":
            st.success("No image issues found by the checks that ran.")
        if r["tf"]:
            st.markdown("#### 🔤 Findings in the text inside the image")
            for f in r["tf"]:
                st.markdown(ui.finding_card(f), unsafe_allow_html=True)
        if role == "Creator":
            if st.button("📤 Submit image review for approval", type="primary", key="img_submit"):
                d = load()
                for f in allF:
                    d["log"].append({"rule": f["rule"], "category": f["category"], "dismissed": False, "time": now()})
                t_img = "Image: " + r["name"]
                item = next((x for x in d["items"] if x["title"] == t_img), None)
                if item is None:
                    item = {"id": uuid.uuid4().hex[:6], "title": t_img, "author": who, "status": "Pending review",
                            "versions": [], "comments": []}
                    d["items"].append(item)
                item["versions"].append({
                    "v": len(item["versions"]) + 1, "time": now(), "issues": len(allF), "by": who,
                    "ai_review": "completed" if r["vstatus"] == "completed" else r["vstatus"],
                    "text": "[IMAGE] %s | Alt text: %s | Text found in image: %s" % (r["name"], r["alt"] or "(none)", r["extracted"] or "(none)")})
                item["status"] = "Pending review"
                save(d)
                st.toast("Submitted. Open the Approval queue.", icon="📤")
                st.success("Submitted! Switch your role to Reviewer and open the Approval queue tab. (The image itself is not stored.)")
        else:
            st.info("Only the Creator role can submit. Switch to Creator to test submission.")

# ---------------- tab 3: queue ----------------
with T_queue:
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
                if role == "Reviewer":
                    decisions = (("✅ Approve", "Approved"), ("✏️ Request changes", "Changes requested"))
                    st.caption("Reviewer permissions: approve or request changes.")
                else:
                    decisions = (("✅ Approve", "Approved"), ("✏️ Request changes", "Changes requested"),
                                 ("⛔ Reject", "Rejected"))
                    if role == "Manager":
                        st.caption("Manager permissions: oversee submissions and approve, request changes or reject.")
                    else:
                        st.caption("Admin permissions: full review decisions and session administration.")
                cols = st.columns(len(decisions))
                for col, (label, status) in zip(cols, decisions):
                    if col.button(label, key=label + it["id"]):
                        it["status"] = status
                        it["comments"].append({"who": who, "role": role, "time": now(),
                                               "action": label.split(" ", 1)[1], "msg": msg or "-"})
                        save(d)
                        if status == "Approved":
                            st.session_state["celebrate"] = True
                        st.rerun()
            else:
                st.caption("🔒 Creator access is view-only in the approval queue. Switch to Reviewer to make decisions.")

# ---------------- tab 4: insights ----------------
with T_insights:
    if role not in ("Manager", "Admin"):
        st.info("Insights are available to Manager and Admin roles. Switch roles in the sidebar to view them.")
    else:
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

# ---------------- tab 5: rulebook ----------------
with T_rulebook:
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
