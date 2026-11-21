
"""BrandGuard review engine: deterministic rule checks with cited sources."""

import re
import json
import os
import difflib
import html


BASE = os.path.dirname(os.path.abspath(__file__))


# --------------------------------------------------
# LOAD APPROVED RULEBOOK
# --------------------------------------------------

def load_rulebook():
    path = os.path.join(BASE, "rulebook.json")

    with open(path, encoding="utf-8") as f:
        return json.load(f)


# --------------------------------------------------
# SAFE HELPERS
# --------------------------------------------------

def _matchcase(src, rep):
    if src.isupper() and len(src) > 1:
        return rep.upper()

    if src[:1].isupper():
        return rep[:1].upper() + rep[1:]

    return rep


def _safe_list(value):
    return value if isinstance(value, list) else []


def _safe_finditer(pattern, text, flags=0):
    """Return regex matches safely without crashing on invalid patterns."""

    if not pattern:
        return []

    try:
        return list(re.finditer(str(pattern), text, flags))
    except (re.error, TypeError, ValueError):
        return []


def _sentence_for_match(text, start, end):
    """Get the sentence containing a particular finding."""

    left = max(
        text.rfind(".", 0, start),
        text.rfind("!", 0, start),
        text.rfind("?", 0, start),
        text.rfind("\n", 0, start),
    )

    right_candidates = [
        p for p in (
            text.find(".", end),
            text.find("!", end),
            text.find("?", end),
            text.find("\n", end),
        )
        if p != -1
    ]

    right = min(right_candidates) if right_candidates else len(text)

    return text[left + 1:right + 1]


def _approved_claim_matches(match_text, sentence, approved_claims):
    """
    Check whether this particular detected claim is covered by
    an approved claim statement present in the same sentence.

    An unrelated approved claim elsewhere in the draft cannot
    validate this finding.
    """

    sentence_normalised = " ".join(sentence.lower().split())

    for approved in approved_claims:

        if not isinstance(approved, str):
            continue

        approved_normalised = " ".join(
            approved.lower().split()
        )

        if not approved_normalised:
            continue

        if (
            approved_normalised in sentence_normalised
            and match_text.lower() in approved_normalised
        ):
            return True

    return False


# --------------------------------------------------
# MAIN DETERMINISTIC REVIEW
# --------------------------------------------------

def review(text, rb):

    text = str(text or "")
    rb = rb if isinstance(rb, dict) else {}

    findings = []

    def add(rule, cat, sev, s, e, why, source,
            sugg, rep, conf="High"):

        findings.append({
            "rule": rule,
            "category": cat,
            "severity": sev,
            "start": s,
            "end": e,
            "text": text[s:e],
            "why": why,
            "source": source,
            "suggestion": sugg,
            "replacement": rep,
            "confidence": conf,
        })

    # --------------------------------------------------
    # 0. SAFETY
    # --------------------------------------------------

    safety = rb.get("safety") or {}

    used_s = []

    for pattern in _safe_list(safety.get("threat_patterns")):

        for m in _safe_finditer(pattern, text, re.I):

            if any(
                m.start() < b and a < m.end()
                for a, b in used_s
            ):
                continue

            used_s.append((m.start(), m.end()))

            add(
                "S1",
                "Safety",
                "Critical",
                m.start(),
                m.end(),
                "Threatening or violent language. "
                "This must never be published.",
                "Safety rules",
                "Remove it and escalate to a human reviewer",
                None,
                "High",
            )

    for word in _safe_list(safety.get("abuse_words")):

        pattern = r"\b" + re.escape(str(word)) + r"\b"

        for m in _safe_finditer(pattern, text, re.I):

            if any(
                m.start() < b and a < m.end()
                for a, b in used_s
            ):
                continue

            used_s.append((m.start(), m.end()))

            add(
                "S2",
                "Safety",
                "High",
                m.start(),
                m.end(),
                "Insulting or abusive language is not allowed "
                "in brand content.",
                "Safety rules",
                "Replace with respectful wording",
                None,
                "High",
            )

    # --------------------------------------------------
    # 1. TERMINOLOGY
    # --------------------------------------------------

    for item in _safe_list(rb.get("terminology")):

        if not isinstance(item, dict):
            continue

        rule_id = item.get("id", "")
        preferred = str(item.get("preferred", ""))
        why = item.get("why", "Use approved brand terminology.")

        flags = 0 if item.get("case_sensitive") else re.I

        for bad_word in _safe_list(item.get("bad")):

            bad_word = str(bad_word)

            if not bad_word:
                continue

            pattern = (
                r"(?<!\w)"
                + re.escape(bad_word)
                + r"(?!\w)"
            )

            for m in _safe_finditer(pattern, text, flags):

                replacement = (
                    preferred
                    if item.get("case_sensitive")
                    else _matchcase(m.group(0), preferred)
                )

                add(
                    rule_id,
                    "Terminology",
                    "Medium",
                    m.start(),
                    m.end(),
                    why,
                    "Brand guidelines: Terminology",
                    "Use '%s'" % preferred,
                    replacement,
                )

    # --------------------------------------------------
    # 2. TONE
    # --------------------------------------------------

    tone = rb.get("tone") or {}

    for word in _safe_list(tone.get("hype_words")):

        pattern = r"\b" + re.escape(str(word)) + r"\b"

        for m in _safe_finditer(pattern, text, re.I):

            add(
                "TN1",
                "Tone",
                "Low",
                m.start(),
                m.end(),
                "Hype words feel pushy. The brand voice "
                "is calm and specific.",
                "Brand guidelines: Tone",
                "Replace with a specific benefit",
                None,
                "Medium",
            )

    for phrase in _safe_list(tone.get("pressure_phrases")):

        pattern = r"\b" + re.escape(str(phrase)) + r"\b"

        for m in _safe_finditer(pattern, text, re.I):

            add(
                "TN2",
                "Tone",
                "Medium",
                m.start(),
                m.end(),
                "Pressure tactics are not allowed "
                "in BrightCart content.",
                "Brand guidelines: Tone",
                "Remove the urgency wording",
                None,
                "High",
            )

    for m in _safe_finditer(r"!{2,}", text):

        add(
            "TN3",
            "Tone",
            "Low",
            m.start(),
            m.end(),
            "Use at most one exclamation mark.",
            "Brand guidelines: Tone",
            "Use a single '!'",
            "!",
        )

    allowed_caps = [
        str(word)
        for word in _safe_list(tone.get("allowed_caps"))
    ]

    for m in _safe_finditer(r"\b[A-Z]{4,}\b", text):

        if m.group(0) not in allowed_caps:

            add(
                "TN4",
                "Tone",
                "Low",
                m.start(),
                m.end(),
                "ALL CAPS reads as shouting and is harder to read.",
                "Brand guidelines: Tone / Accessibility",
                "Use normal capitalisation",
                m.group(0).capitalize(),
            )

    # --------------------------------------------------
    # 3. CLAIM VERIFICATION
    # --------------------------------------------------

    approved_claims = _safe_list(
        rb.get("approved_claims")
    )

    used_claims = []

    for claim_rule in _safe_list(rb.get("claims")):

        if not isinstance(claim_rule, dict):
            continue

        pattern = claim_rule.get("pattern")

        for m in _safe_finditer(pattern, text, re.I):

            # Prevent duplicate overlapping claim findings.
            if any(
                m.start() < b and a < m.end()
                for a, b in used_claims
            ):
                continue

            used_claims.append((m.start(), m.end()))

            sentence = _sentence_for_match(
                text,
                m.start(),
                m.end(),
            )

            # Verify this particular claim, not the entire document.
            supported = _approved_claim_matches(
                m.group(0),
                sentence,
                approved_claims,
            )

            if supported:
                continue

            add(
                "C1",
                "Claim",
                "High",
                m.start(),
                m.end(),
                "Absolute or superlative claim. "
                "No matching approved claim statement "
                "was found for this specific claim.",
                "Approved claims list",
                "Remove it, or attach approved proof",
                claim_rule.get("soft"),
                "Unverified: needs human check",
            )

    # --------------------------------------------------
    # 4. FACT VERIFICATION
    # --------------------------------------------------

    numbers = [
        (
            m.start(),
            m.end(),
            m.group(0).replace(",", "")
        )
        for m in _safe_finditer(
            r"\d+(?:,\d{3})*",
            text
        )
    ]

    for fact in _safe_list(rb.get("facts")):

        if not isinstance(fact, dict):
            continue

        topic_pattern = fact.get("topic_regex")

        approved = str(fact.get("approved", ""))

        if not topic_pattern or not approved:
            continue

        for topic_match in _safe_finditer(
            topic_pattern,
            text,
            re.I,
        ):

            best = None

            for start, end, value in numbers:

                distance = min(
                    abs(start - topic_match.end()),
                    abs(topic_match.start() - end),
                )

                if distance <= 28:

                    if best is None or distance < best[0]:

                        best = (
                            distance,
                            start,
                            end,
                            value,
                        )

            if best and best[3] != approved:

                add(
                    fact.get("id", ""),
                    "Fact",
                    "High",
                    best[1],
                    best[2],
                    "Approved fact: %s. "
                    "This content says %s."
                    % (
                        fact.get("statement", ""),
                        best[3],
                    ),
                    "Approved facts %s" % fact.get("id", ""),
                    "Change to %s" % approved,
                    approved,
                )

    # --------------------------------------------------
    # 5. ACCESSIBILITY
    # --------------------------------------------------

    for m in _safe_finditer(
        r"click here",
        text,
        re.I,
    ):

        add(
            "A1",
            "Accessibility",
            "Medium",
            m.start(),
            m.end(),
            "'Click here' is meaningless to screen-reader users.",
            "Accessibility rules",
            "Use descriptive link text",
            _matchcase(m.group(0), "view details"),
        )

    for m in _safe_finditer(
        r"!\[\s*\]\([^)]*\)",
        text,
    ):

        add(
            "A2",
            "Accessibility",
            "High",
            m.start(),
            m.end(),
            "Image has no alt text, so screen-reader users "
            "get no description.",
            "Accessibility rules",
            "Add a short description inside [ ]",
            None,
        )

    # --------------------------------------------------
    # SORT FINDINGS
    # --------------------------------------------------

    findings.sort(
        key=lambda item: (
            item["start"],
            item["end"],
        )
    )

    return findings


# --------------------------------------------------
# AUTOMATIC FIXES
# --------------------------------------------------

def apply_fixes(text, findings, skip=()):

    text = str(text or "")

    output = []
    pos = 0
    last_end = 0

    for i, finding in enumerate(findings):

        if i in skip:
            continue

        replacement = finding.get("replacement")

        if replacement is None:
            continue

        start = finding.get("start", -1)
        end = finding.get("end", -1)

        if (
            start < last_end
            or start < 0
            or end < start
            or end > len(text)
        ):
            continue

        output.append(text[pos:start])
        output.append(str(replacement))

        pos = end
        last_end = end

    output.append(text[pos:])

    return re.sub(
        r"[ ]{2,}",
        " ",
        "".join(output),
    )


# --------------------------------------------------
# HTML DIFF
# --------------------------------------------------

def diff_html(a, b):

    sm = difflib.SequenceMatcher(
        None,
        a.split(),
        b.split(),
    )

    wa = a.split()
    wb = b.split()

    parts = []

    for op, i1, i2, j1, j2 in sm.get_opcodes():

        if op == "equal":

            parts.append(
                html.escape(" ".join(wa[i1:i2]))
            )

        else:

            if i2 > i1:

                parts.append(
                    "<del style='background:#ffd6d6'>%s</del>"
                    % html.escape(" ".join(wa[i1:i2]))
                )

            if j2 > j1:

                parts.append(
                    "<ins style='background:#d3f9d8;"
                    "text-decoration:none'>%s</ins>"
                    % html.escape(" ".join(wb[j1:j2]))
                )

    return " ".join(parts)


# --------------------------------------------------
# MERGE FINDINGS
# --------------------------------------------------

def merge_findings(base, extra):
    """Add extra AI findings without overlapping existing findings."""

    output = list(base)

    for finding in extra:

        start = finding.get("start", -1)
        end = finding.get("end", -1)

        if start < 0 or end <= start:
            continue

        overlaps = any(
            start < existing.get("end", 0)
            and existing.get("start", 0) < end
            for existing in output
        )

        if not overlaps:
            output.append(finding)

    output.sort(
        key=lambda item: item.get("start", 0)
    )

    return output
