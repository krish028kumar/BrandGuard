"""BrandGuard review engine: deterministic rule checks with cited sources."""
import re, json, os, difflib, html

BASE = os.path.dirname(os.path.abspath(__file__))

def load_rulebook():
    with open(os.path.join(BASE, "rulebook.json"), encoding="utf-8") as f:
        return json.load(f)

def _matchcase(src, rep):
    if src.isupper() and len(src) > 1:
        return rep.upper()
    if src[:1].isupper():
        return rep[:1].upper() + rep[1:]
    return rep

def review(text, rb):
    F = []
    def add(rule, cat, sev, s, e, why, source, sugg, rep, conf="High"):
        F.append(dict(rule=rule, category=cat, severity=sev, start=s, end=e,
                      text=text[s:e], why=why, source=source,
                      suggestion=sugg, replacement=rep, confidence=conf))


    # 0. Safety (threats, abuse): checked first, always on
    sf = rb.get("safety", {})
    used_s = []
    for p in sf.get("threat_patterns", []):
        for m in re.finditer(p, text, re.I):
            if any(m.start() < b and a < m.end() for a, b in used_s):
                continue
            used_s.append((m.start(), m.end()))
            add("S1", "Safety", "Critical", m.start(), m.end(),
                "Threatening or violent language. This must never be published.",
                "Safety rules", "Remove it and escalate to a human reviewer", None, "High")
    for w in sf.get("abuse_words", []):
        for m in re.finditer(r"\b" + re.escape(w) + r"\b", text, re.I):
            add("S2", "Safety", "High", m.start(), m.end(),
                "Insulting or abusive language is not allowed in brand content.",
                "Safety rules", "Replace with respectful wording", None, "High")

    # 1. Terminology
    for t in rb["terminology"]:
        flags = 0 if t.get("case_sensitive") else re.I
        for b in t["bad"]:
            for m in re.finditer(r"(?<!\w)" + re.escape(b) + r"(?!\w)", text, flags):
                rep = t["preferred"] if t.get("case_sensitive") else _matchcase(m.group(0), t["preferred"])
                add(t["id"], "Terminology", "Medium", m.start(), m.end(), t["why"],
                    "Brand guidelines: Terminology", "Use '%s'" % t["preferred"], rep)

    # 2. Tone
    tone = rb["tone"]
    for w in tone["hype_words"]:
        for m in re.finditer(r"\b" + re.escape(w) + r"\b", text, re.I):
            add("TN1", "Tone", "Low", m.start(), m.end(),
                "Hype words feel pushy. The brand voice is calm and specific.",
                "Brand guidelines: Tone", "Replace with a specific benefit", None, "Medium")
    for w in tone["pressure_phrases"]:
        for m in re.finditer(r"\b" + re.escape(w) + r"\b", text, re.I):
            add("TN2", "Tone", "Medium", m.start(), m.end(),
                "Pressure tactics are not allowed in BrightCart content.",
                "Brand guidelines: Tone", "Remove the urgency wording", None, "High")
    for m in re.finditer(r"!{2,}", text):
        add("TN3", "Tone", "Low", m.start(), m.end(),
            "Use at most one exclamation mark.", "Brand guidelines: Tone", "Use a single '!'", "!")
    for m in re.finditer(r"\b[A-Z]{4,}\b", text):
        if m.group(0) not in tone["allowed_caps"]:
            add("TN4", "Tone", "Low", m.start(), m.end(),
                "ALL CAPS reads as shouting and is harder to read.",
                "Brand guidelines: Tone / Accessibility", "Use normal capitalisation",
                m.group(0).capitalize())

    # 3. Unsupported claims
    supported = any(e.lower() in text.lower() for e in rb["approved_claims"])
    if not supported:
        used = []
        for c in rb["claims"]:
            for m in re.finditer(c["pattern"], text, re.I):
                if any(m.start() < b and a < m.end() for a, b in used):
                    continue
                used.append((m.start(), m.end()))
                add("C1", "Claim", "High", m.start(), m.end(),
                    "Absolute or superlative claim, and no approved evidence is on file.",
                    "Approved claims list", "Remove it, or attach approved proof", c.get("soft"),
                    "Unverified: needs human check")

    # 4. Facts vs approved facts
    nums = [(m.start(), m.end(), m.group(0).replace(",", "")) for m in re.finditer(r"\d+(?:,\d{3})*", text)]
    for fct in rb["facts"]:
        for tm in re.finditer(fct["topic_regex"], text, re.I):
            best = None
            for s, e, v in nums:
                d = min(abs(s - tm.end()), abs(tm.start() - e))
                if d <= 28 and (best is None or d < best[0]):
                    best = (d, s, e, v)
            if best and best[3] != fct["approved"]:
                add(fct["id"], "Fact", "High", best[1], best[2],
                    "Approved fact: %s. This content says %s." % (fct["statement"], best[3]),
                    "Approved facts %s" % fct["id"], "Change to %s" % fct["approved"],
                    fct["approved"])

    # 5. Accessibility
    for m in re.finditer(r"click here", text, re.I):
        add("A1", "Accessibility", "Medium", m.start(), m.end(),
            "'Click here' is meaningless to screen-reader users.",
            "Accessibility rules", "Use descriptive link text", _matchcase(m.group(0), "view details"))
    for m in re.finditer(r"!\[\s*\]\([^)]*\)", text):
        add("A2", "Accessibility", "High", m.start(), m.end(),
            "Image has no alt text, so screen-reader users get no description.",
            "Accessibility rules", "Add a short description inside [ ]", None)

    F.sort(key=lambda x: x["start"])
    return F

def apply_fixes(text, findings, skip=()):
    out, pos, last_end = [], 0, 0
    for i, f in enumerate(findings):
        if i in skip or f["replacement"] is None or f["start"] < last_end:
            continue
        out.append(text[pos:f["start"]])
        out.append(f["replacement"])
        pos = last_end = f["end"]
    out.append(text[pos:])
    return re.sub(r"[ ]{2,}", " ", "".join(out))

def diff_html(a, b):
    sm = difflib.SequenceMatcher(None, a.split(), b.split())
    wa, wb, parts = a.split(), b.split(), []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            parts.append(html.escape(" ".join(wa[i1:i2])))
        else:
            if i2 > i1:
                parts.append("<del style='background:#ffd6d6'>%s</del>" % html.escape(" ".join(wa[i1:i2])))
            if j2 > j1:
                parts.append("<ins style='background:#d3f9d8;text-decoration:none'>%s</ins>" % html.escape(" ".join(wb[j1:j2])))
    return " ".join(parts)


def merge_findings(base, extra):
    """Add extra (e.g. AI) findings that do not overlap existing ones."""
    out = list(base)
    for f in extra:
        if not any(f["start"] < g["end"] and g["start"] < f["end"] for g in out):
            out.append(f)
    out.sort(key=lambda x: x["start"])
    return out
