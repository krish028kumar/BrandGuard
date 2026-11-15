
"""
UI helpers for BrandGuard.

Contains:
- Shared CSS
- HTML components
- Score calculations
- Finding cards
- Highlighted draft rendering
- Approval status badges
- Workflow success and notification components

No Streamlit import.
"""

import html


# ---------------- constants ----------------

SEV = {
    "Critical": "#C92A2A",
    "High": "#FF6B6B",
    "Medium": "#F59F00",
    "Low": "#339AF0"
}

ICON = {
    "Safety": "🚫",
    "Terminology": "📖",
    "Tone": "🎭",
    "Claim": "⚠️",
    "Fact": "🧾",
    "Accessibility": "♿"
}

W = {
    "Critical": 60,
    "High": 10,
    "Medium": 6,
    "Low": 3
}

DEFAULT_SEVERITY = "Low"


# ---------------- safe HTML helpers ----------------

def E(value):
    """Escape untrusted values before inserting them into HTML."""
    return html.escape(
        str(value if value is not None else ""),
        quote=True
    )


def _severity(value):
    """Return a supported severity."""
    value = str(value or DEFAULT_SEVERITY)
    return value if value in SEV else DEFAULT_SEVERITY


def _category(value):
    """Return a supported category."""
    value = str(value or "Safety")
    return value if value in ICON else "Safety"


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ---------------- CSS ----------------

CSS = """
<style>

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, .stApp, button, input, textarea {
    font-family: 'Inter', sans-serif;
}

/* Main application */

.stApp {
    background: linear-gradient(
        160deg,
        #F6F4FF 0%,
        #EEF6FF 55%,
        #F3FFFB 100%
    );
}

.block-container {
    padding-top: 1.2rem;
    max-width: 1200px;
}

[data-testid="stSidebar"] {
    background: #FFFFFF;
    border-right: 1px solid #ECE9FF;
}

/* ---------------- NO BLUR / NO FADE ---------------- */

.stApp,
[data-testid="stApp"],
[data-testid="stAppViewContainer"],
[data-testid="stAppViewBlockContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"],
[data-testid="stVerticalBlock"],
[data-testid="stHorizontalBlock"] {
    filter: none !important;
    -webkit-filter: none !important;
    opacity: 1 !important;
}

/* Remove backdrop blur and visual overlays */

[data-testid="stAppViewContainer"]::before,
[data-testid="stAppViewContainer"]::after,
[data-testid="stMain"]::before,
[data-testid="stMain"]::after {
    backdrop-filter: none !important;
    -webkit-backdrop-filter: none !important;
}

/* Keep Streamlit content readable during interactions */

[data-testid="stAppViewContainer"] [data-testid="stAppViewBlockContainer"] {
    filter: none !important;
    opacity: 1 !important;
}

/* ---------------- animations ---------------- */

@keyframes float {
    0%, 100% {
        transform: translateY(0);
    }
    50% {
        transform: translateY(-8px);
    }
}

/* ---------------- hero ---------------- */

.hero {
    position: relative;
    overflow: hidden;
    border-radius: 24px;
    padding: 28px 34px;
    color: #fff;
    background: linear-gradient(
        120deg,
        #6C5CE7 0%,
        #4C6EF5 55%,
        #15AABF 100%
    );
    box-shadow: 0 18px 40px rgba(76,110,245,.20);
}

.hero-in {
    display: flex;
    justify-content: space-between;
    align-items: center;
    position: relative;
    z-index: 2;
}

.hero .logo {
    font-size: 2.2rem;
    font-weight: 800;
    letter-spacing: -.5px;
}

.hero .tag {
    opacity: .95;
    margin: .3rem 0 1rem;
    font-size: 1.05rem;
}

.pills span {
    display: inline-block;
    background: rgba(255,255,255,.18);
    border: 1px solid rgba(255,255,255,.4);
    padding: 5px 13px;
    border-radius: 999px;
    margin: 0 8px 6px 0;
    font-size: .82rem;
    font-weight: 600;
}

.mascot {
    font-size: 4.4rem;
    animation: float 3s ease-in-out infinite;
    filter: drop-shadow(0 8px 12px rgba(0,0,0,.20));
}

.orb {
    position: absolute;
    border-radius: 50%;
    opacity: .18;
    background: #fff;
}

.o1 {
    width: 230px;
    height: 230px;
    right: -60px;
    top: -90px;
}

.o2 {
    width: 120px;
    height: 120px;
    left: 42%;
    bottom: -60px;
}

/* ---------------- steps ---------------- */

.steps {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin: 16px 0 10px;
}

.step {
    background: #fff;
    border-radius: 16px;
    padding: 12px 14px;
    box-shadow: 0 6px 18px rgba(30,27,75,.07);
    display: flex;
    gap: 10px;
    align-items: center;
}

.step b {
    display: block;
    color: #1E1B4B;
    font-size: .88rem;
}

.step small {
    color: #6B6890;
}

.step .n {
    font-size: 1.6rem;
}

/* ---------------- tabs ---------------- */

.stTabs [data-baseweb="tab-list"] {
    gap: 6px;
    background: #fff;
    padding: 6px;
    border-radius: 14px;
    box-shadow: 0 6px 18px rgba(30,27,75,.06);
}

.stTabs [data-baseweb="tab"] {
    border-radius: 10px;
    padding: 8px 16px;
    font-weight: 700;
}

.stTabs [aria-selected="true"] {
    background: linear-gradient(
        120deg,
        #6C5CE7,
        #4C6EF5
    );
}

.stTabs [aria-selected="true"] p {
    color: #fff !important;
}

.stTabs [data-baseweb="tab-highlight"],
.stTabs [data-baseweb="tab-border"] {
    display: none;
}

/* ---------------- buttons ---------------- */

.stButton > button {
    border-radius: 12px !important;
    font-weight: 700 !important;
    border: 1px solid #D9D4FF !important;
    transition:
        background-color .12s ease,
        border-color .12s ease,
        box-shadow .12s ease,
        color .12s ease !important;
    transform: none !important;
    filter: none !important;
    opacity: 1 !important;
    cursor: pointer !important;
}

.stButton > button:hover:not(:disabled) {
    border-color: #6C5CE7 !important;
    box-shadow: 0 3px 10px rgba(108,92,231,.18) !important;
    transform: none !important;
    filter: none !important;
    opacity: 1 !important;
}

.stButton > button:active:not(:disabled) {
    background-color: #E7E5FF !important;
    border-color: #4C3FB5 !important;
    box-shadow: inset 0 2px 4px rgba(30,27,75,.15) !important;
    transform: none !important;
}

.stButton > button:focus,
.stButton > button:focus-visible {
    outline: 3px solid rgba(108,92,231,.35) !important;
    outline-offset: 2px !important;
    filter: none !important;
}

.stButton > button[kind="primary"],
.stButton > button[data-testid="stBaseButton-primary"] {
    background: linear-gradient(
        120deg,
        #6C5CE7,
        #4C6EF5
    ) !important;
    color: #fff !important;
    border: none !important;
}

.stButton > button[kind="primary"]:hover:not(:disabled),
.stButton > button[data-testid="stBaseButton-primary"]:hover:not(:disabled) {
    background: linear-gradient(
        120deg,
        #5948D6,
        #3559E8
    ) !important;
    box-shadow: 0 4px 12px rgba(76,110,245,.28) !important;
}

.stButton > button:disabled {
    opacity: .55 !important;
    cursor: not-allowed !important;
    transform: none !important;
    box-shadow: none !important;
}

/* Inputs */

.stTextArea textarea,
.stTextInput input {
    border-radius: 12px !important;
}

/* ---------------- workflow feedback ---------------- */

.workflow-success,
.workflow-revision,
.workflow-submitted {
    display: flex;
    align-items: center;
    gap: 14px;
    border-radius: 18px;
    padding: 17px 20px;
    margin: 12px 0;
}

.workflow-success {
    background: linear-gradient(120deg, #E6FCF5, #D3F9D8);
    border: 1px solid #8CE99A;
    color: #087F5B;
}

.workflow-revision {
    background: linear-gradient(120deg, #FFF4E6, #FFF0DB);
    border: 1px solid #FFC078;
    border-left: 6px solid #F08C00;
    color: #A65300;
}

.workflow-submitted {
    background: linear-gradient(120deg, #F3F0FF, #E7E5FF);
    border: 1px solid #B197FC;
    color: #5F3DC4;
}

.workflow-success .feedback-icon,
.workflow-revision .feedback-icon,
.workflow-submitted .feedback-icon {
    font-size: 2.2rem;
    flex-shrink: 0;
}

.workflow-success .feedback-title,
.workflow-revision .feedback-title,
.workflow-submitted .feedback-title {
    font-size: 1.05rem;
    font-weight: 800;
}

.workflow-success .feedback-message,
.workflow-revision .feedback-message,
.workflow-submitted .feedback-message {
    font-size: .88rem;
    margin-top: 3px;
}

.workflow-success .feedback-message {
    color: #087F5B;
}

.workflow-revision .feedback-message {
    color: #A65300;
}

.workflow-submitted .feedback-message {
    color: #5F3DC4;
}

/* ---------------- score card ---------------- */

.score {
    display: flex;
    gap: 24px;
    align-items: center;
    background: #fff;
    border-radius: 22px;
    padding: 18px 24px;
    box-shadow: 0 10px 28px rgba(30,27,75,.09);
    margin: 6px 0 14px;
}

.ring {
    position: relative;
    width: 116px;
    height: 116px;
    border-radius: 50%;
    flex: none;
    display: grid;
    place-items: center;
    background: conic-gradient(
        var(--c) calc(var(--p) * 1%),
        #E9E6FB 0
    );
}

.ring::before {
    content: "";
    position: absolute;
    inset: 11px;
    border-radius: 50%;
    background: #fff;
}

.ring span {
    position: relative;
    font-weight: 800;
    font-size: 1.95rem;
    color: #1E1B4B;
}

.ring small {
    position: absolute;
    bottom: 20px;
    font-size: .62rem;
    color: #8A86B0;
    font-weight: 600;
    letter-spacing: .5px;
}

.face {
    font-size: 2.8rem;
    display: inline-block;
    margin-right: 8px;
    vertical-align: middle;
}

.verdict b {
    font-size: 1.35rem;
    color: #1E1B4B;
    vertical-align: middle;
}

.verdict p {
    margin: 2px 0 10px;
    color: #6B6890;
}

/* ---------------- chips ---------------- */

.chip {
    display: inline-block;
    padding: 4px 11px;
    border-radius: 999px;
    font-size: .78rem;
    font-weight: 700;
    margin: 0 6px 4px 0;
}

.chip.critical {
    background: #C92A2A;
    color: #fff;
}

.chip.high {
    background: #FFE3E3;
    color: #C92A2A;
}

.chip.medium {
    background: #FFF3BF;
    color: #B35C00;
}

.chip.low {
    background: #D0EBFF;
    color: #1864AB;
}

.chip.ok {
    background: #D3F9D8;
    color: #2B8A3E;
}

.chip.st-pending {
    background: #E7E3FF;
    color: #5F3DC4;
}

.chip.st-approved {
    background: #D3F9D8;
    color: #2B8A3E;
}

.chip.st-changes {
    background: #FFF3BF;
    color: #B35C00;
}

.chip.st-rejected {
    background: #FFE3E3;
    color: #C92A2A;
}

/* ---------------- panels ---------------- */

.panel {
    background: #fff;
    border-radius: 18px;
    padding: 16px 18px;
    box-shadow: 0 8px 22px rgba(30,27,75,.07);
    color: #1E1B4B;
}

.panel h4 {
    margin: 0 0 8px;
    font-size: .95rem;
    color: #4C3FB5;
}

/* ---------------- highlighted text ---------------- */

.annot {
    line-height: 1.95;
    white-space: pre-wrap;
    color: #1E1B4B;
}

mark.hl {
    padding: 2px 7px;
    border-radius: 8px;
    font-weight: 700;
    cursor: help;
}

mark.hl-critical {
    background: #C92A2A;
    color: #fff;
    box-shadow: inset 0 -2px 0 #7D1313;
}

mark.hl-high {
    background: #FFE3E3;
    color: #C92A2A;
    box-shadow: inset 0 -2px 0 #FF6B6B;
}

mark.hl-medium {
    background: #FFF3BF;
    color: #B35C00;
    box-shadow: inset 0 -2px 0 #F59F00;
}

mark.hl-low {
    background: #D0EBFF;
    color: #1864AB;
    box-shadow: inset 0 -2px 0 #339AF0;
}

/* ---------------- finding cards ---------------- */

.fcard {
    background: #fff;
    border-radius: 16px;
    padding: 14px 16px;
    border-left: 6px solid var(--s);
    box-shadow: 0 6px 18px rgba(30,27,75,.07);
    color: #1E1B4B;
}

.fhead {
    display: flex;
    gap: 8px;
    align-items: center;
    flex-wrap: wrap;
    margin-bottom: 6px;
}

.fhead .ic {
    font-size: 1.3rem;
}

.pill {
    background: #F1EEFF;
    color: #5F3DC4;
    border-radius: 8px;
    padding: 2px 9px;
    font-size: .74rem;
    font-weight: 700;
}

.fquote {
    font-weight: 800;
    margin: 2px 0 4px;
}

.fwhy {
    color: #3B3866;
}

.fmeta {
    color: #7A77A3;
    font-size: .8rem;
    margin-top: 6px;
}

.fsug {
    margin-top: 6px;
    background: #F3FFFB;
    border: 1px dashed #20C997;
    border-radius: 10px;
    padding: 6px 10px;
    font-size: .86rem;
}

/* ---------------- metric cards ---------------- */

.mgrid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    margin-bottom: 14px;
}

.mcard {
    background: #fff;
    border-radius: 18px;
    padding: 16px 18px;
    box-shadow: 0 8px 22px rgba(30,27,75,.07);
}

.mcard .v {
    font-size: 2rem;
    font-weight: 800;
    color: #4C3FB5;
}

.mcard .l {
    color: #6B6890;
    font-weight: 600;
    font-size: .85rem;
}

/* ---------------- empty state ---------------- */

.empty {
    text-align: center;
    padding: 34px;
    background: #fff;
    border-radius: 20px;
    box-shadow: 0 8px 22px rgba(30,27,75,.07);
}

.empty .big {
    font-size: 3.4rem;
    display: inline-block;
}

/* ---------------- profile card ---------------- */

.pcard {
    border-radius: 16px;
    padding: 14px;
    background: linear-gradient(135deg, #6C5CE7, #4C6EF5);
    color: #fff;
    margin: 8px 0 12px;
}

.pcard .av {
    font-size: 2rem;
}

.pcard small {
    opacity: .85;
}

/* ---------------- privacy card ---------------- */

.privacy {
    background: #F3FFFB;
    border: 1px solid #B2F2E4;
    border-radius: 14px;
    padding: 12px;
    font-size: .8rem;
    color: #0B7A68;
    margin-top: 10px;
}

/* ---------------- diff ---------------- */

.diffbox {
    line-height: 1.95;
    color: #1E1B4B;
}

/* ---------------- footer ---------------- */

.foot {
    text-align: center;
    color: #8A86B0;
    font-size: .8rem;
    margin: 26px 0 6px;
}

/* ---------------- responsive layout ---------------- */

@media (max-width: 760px) {
    .hero {
        padding: 22px;
    }

    .hero .logo {
        font-size: 1.6rem;
    }

    .mascot {
        font-size: 2.8rem;
    }

    .steps {
        grid-template-columns: repeat(2, 1fr);
    }

    .mgrid {
        grid-template-columns: 1fr;
    }

    .score {
        flex-wrap: wrap;
    }

    .workflow-success,
    .workflow-revision,
    .workflow-submitted {
        padding: 14px;
    }
}

</style>
"""


# ---------------- score calculation ----------------

def score_of(F):
    """Calculate the brand score."""
    if not isinstance(F, (list, tuple)):
        return 0

    penalty = sum(
        W[_severity(f.get("severity"))]
        for f in F
        if isinstance(f, dict)
    )

    score = max(0, 100 - penalty)

    if any(
        isinstance(f, dict)
        and _severity(f.get("severity")) == "Critical"
        for f in F
    ):
        return min(score, 8)

    if any(
        isinstance(f, dict)
        and _category(f.get("category")) == "Safety"
        for f in F
    ):
        return min(score, 40)

    return score


# ---------------- score mood ----------------

def mood(s):
    if s >= 90:
        return "😄", "Looking great", "Ready for a quick human check."

    if s >= 70:
        return "🙂", "Almost there", "A few fixes will make it on-brand."

    if s >= 45:
        return "😟", "Needs work", "Several issues could hurt credibility."

    return "😰", "High risk", "Please do not publish before fixing these."


# ---------------- score color ----------------

def color_of(s):
    if s >= 80:
        return "#12B886"

    if s >= 50:
        return "#F59F00"

    return "#FF6B6B"


# ---------------- hero section ----------------

def hero():
    return (
        '<div class="hero">'
        '<div class="orb o1"></div>'
        '<div class="orb o2"></div>'
        '<div class="hero-in">'
        '<div>'
        '<div class="logo">🛡️ BrandGuard</div>'
        '<div class="tag">'
        'Catch off-brand content before the world does.'
        '</div>'
        '<div class="pills">'
        '<span>🔍 Explainable findings</span>'
        '<span>🧑‍⚖️ Humans decide</span>'
        '<span>🔒 Private by design</span>'
        '<span>📚 Cites your rulebook</span>'
        '</div>'
        '</div>'
        '<div class="mascot">🤖</div>'
        '</div>'
        '</div>'
    )


# ---------------- process steps ----------------

def steps():
    items = [
        ("📘", "1. Rulebook", "Approved rules and facts"),
        ("✍️", "2. Draft", "Paste your content"),
        ("🔍", "3. Review", "Explained findings and fixes"),
        ("✅", "4. Approve", "A human signs off")
    ]

    content = "".join(
        (
            '<div class="step">'
            '<span class="n">%s</span>'
            '<div><b>%s</b><small>%s</small></div>'
            '</div>'
        ) % (E(icon), E(title), E(description))
        for icon, title, description in items
    )

    return '<div class="steps">' + content + '</div>'


# ---------------- score card ----------------

def score_card(F):
    if not isinstance(F, (list, tuple)):
        F = []

    s = score_of(F)
    face, head, sub = mood(s)

    if any(
        isinstance(f, dict)
        and _severity(f.get("severity")) == "Critical"
        for f in F
    ):
        face = "🚫"
        head = "Blocked: unsafe content"
        sub = "A human reviewer must look at this. Do not publish."

    counts = {
        severity: sum(
            1
            for finding in F
            if (
                isinstance(finding, dict)
                and _severity(finding.get("severity")) == severity
            )
        )
        for severity in ("Critical", "High", "Medium", "Low")
    }

    chips = "".join(
        '<span class="chip %s">%s %d</span>'
        % (severity.lower(), E(severity), count)
        for severity, count in counts.items()
        if count
    )

    if not chips:
        chips = '<span class="chip ok">✔ No issues found</span>'

    return (
        '<div class="score">'
        '<div class="ring" style="--p:%d;--c:%s">'
        '<span>%d</span>'
        '<small>BRAND SCORE</small>'
        '</div>'
        '<div class="verdict">'
        '<span class="face">%s</span>'
        '<b>%s</b>'
        '<p>%s</p>'
        '%s'
        '</div>'
        '</div>'
        % (s, color_of(s), s, face, E(head), E(sub), chips)
    )


# ---------------- highlighted draft ----------------

def annotate(text, F):
    """Highlight findings using their character positions."""
    text = str(text or "")

    if not isinstance(F, (list, tuple)):
        F = []

    valid = []

    for finding in F:
        if not isinstance(finding, dict):
            continue

        start = _safe_int(finding.get("start"), -1)
        end = _safe_int(finding.get("end"), -1)

        if start < 0 or end <= start or end > len(text):
            continue

        valid.append((start, end, finding))

    valid.sort(key=lambda item: (item[0], item[1]))

    out = []
    pos = 0

    for start, end, finding in valid:
        if start < pos:
            continue

        out.append(E(text[pos:start]))

        severity = _severity(finding.get("severity"))
        rule = E(finding.get("rule", "Rule"))
        why = E(finding.get("why", ""))
        quote = E(text[start:end])

        out.append(
            '<mark class="hl hl-%s" title="%s">%s</mark>'
            % (
                severity.lower(),
                E("%s: %s" % (rule, why)),
                quote
            )
        )

        pos = end

    out.append(E(text[pos:]))

    return (
        '<div class="panel">'
        '<h4>🖍️ Your draft, highlighted (hover a highlight)</h4>'
        '<div class="annot">'
        + "".join(out)
        + '</div>'
        '</div>'
    )


# ---------------- finding card ----------------

def finding_card(f):
    if not isinstance(f, dict):
        f = {}

    severity = _severity(f.get("severity"))
    category = _category(f.get("category"))

    rule = E(f.get("rule", "Unknown rule"))
    quote = E(f.get("text", ""))
    why = E(f.get("why", ""))
    source = E(f.get("source", "Rulebook / AI review"))
    confidence = E(f.get("confidence", "Not specified"))
    suggestion = E(f.get("suggestion", "Human verification required."))

    icon = ICON.get(category, "🔎")
    severity_color = SEV.get(severity, SEV["Low"])

    return (
        '<div class="fcard" style="--s:%s">'
        '<div class="fhead">'
        '<span class="ic">%s</span>'
        '<b>%s</b>'
        '<span class="pill">%s</span>'
        '<span class="chip %s">%s</span>'
        '</div>'
        '<div class="fquote">“%s”</div>'
        '<div class="fwhy">%s</div>'
        '<div class="fmeta">📚 %s &nbsp;·&nbsp; 🎯 %s</div>'
        '<div class="fsug">💡 %s</div>'
        '</div>'
        % (
            severity_color,
            icon,
            category,
            rule,
            severity.lower(),
            severity,
            quote,
            why,
            source,
            confidence,
            suggestion
        )
    )


# ---------------- generic panel ----------------

def panel(title, inner):
    return (
        '<div class="panel">'
        '<h4>%s</h4>'
        '<div class="diffbox">%s</div>'
        '</div>'
        % (E(title), inner)
    )


# ---------------- metric cards ----------------

def metric_cards(items):
    cards = []

    for value, label in items:
        cards.append(
            (
                '<div class="mcard">'
                '<div class="v">%s</div>'
                '<div class="l">%s</div>'
                '</div>'
            ) % (E(value), E(label))
        )

    return '<div class="mgrid">' + "".join(cards) + '</div>'


# ---------------- approval status badge ----------------

def status_chip(status):
    status = str(status or "Pending review")

    cls = {
        "Approved": "st-approved",
        "Rejected": "st-rejected",
        "Changes requested": "st-changes",
        "Pending review": "st-pending"
    }.get(status, "st-pending")

    icon = {
        "Approved": "✅",
        "Rejected": "⛔",
        "Changes requested": "✏️",
        "Pending review": "⏳"
    }.get(status, "⏳")

    return (
        '<span class="chip %s">%s %s</span>'
        % (cls, icon, E(status))
    )


# ---------------- workflow feedback components ----------------

def submission_success(message="Your submission has been sent for review."):
    """Creator submission confirmation."""
    return (
        '<div class="workflow-submitted">'
        '<span class="feedback-icon">🎉</span>'
        '<div>'
        '<div class="feedback-title">🎉 Submission sent successfully!</div>'
        '<div class="feedback-message">%s</div>'
        '</div>'
        '</div>'
        % E(message)
    )


def approval_success(message="The content has been approved successfully."):
    """Reviewer approval confirmation."""
    return (
        '<div class="workflow-success">'
        '<span class="feedback-icon">🎊</span>'
        '<div>'
        '<div class="feedback-title">Approved successfully!</div>'
        '<div class="feedback-message">%s</div>'
        '</div>'
        '</div>'
        % E(message)
    )


def revision_requested(message="The creator can now review the feedback and make changes."):
    """Reviewer Request Changes confirmation."""
    return (
        '<div class="workflow-revision">'
        '<span class="feedback-icon">📝</span>'
        '<div>'
        '<div class="feedback-title">Changes requested</div>'
        '<div class="feedback-message">%s</div>'
        '</div>'
        '</div>'
        % E(message)
    )


# ---------------- user profile card ----------------

def profile_card(name, role, icon):
    return (
        '<div class="pcard">'
        '<span class="av">%s</span> '
        '<b>%s</b>'
        '<br>'
        '<small>Signed in as %s</small>'
        '</div>'
        % (E(icon), E(name), E(role))
    )


# ---------------- privacy card ----------------

def privacy_card():
    return (
        '<div class="privacy">'
        '🔒 <b>AI &amp; privacy</b><br>'
        'Checks run locally using your approved rulebook. '
        'When AI moderation is enabled, the submitted text or image '
        'is sent to the configured external AI provider '
        '(OpenAI or OpenRouter) for analysis. '
        'Only enable AI moderation when you are permitted to share '
        'the content with that provider.'
        '</div>'
    )


# ---------------- empty state ----------------

def empty(emoji, title, sub):
    return (
        '<div class="empty">'
        '<div class="big">%s</div>'
        '<h3>%s</h3>'
        '<p>%s</p>'
        '</div>'
        % (E(emoji), E(title), E(sub))
    )
