
"""Evidence-grounded verification for BrandGuard.

1. Retrieve approved rules and facts relevant to the draft.
2. Give the AI only the relevant approved rulebook sections.
3. Match every finding against the evidence actually retrieved.
4. Label findings as verified, AI-grounded, unsupported or general safety.

Important:
- AI findings are never automatically trusted.
- A source is attached only when it was actually retrieved.
- Unsupported claims are not treated as verified.
- General safety findings do not require a brand-specific rule.
"""

import html
import math
import re
from collections import Counter


# --------------------------------------------------
# RULE AND SOURCE MAPPING
# --------------------------------------------------

RULE_TO_CHUNK = {
    "TN1": "TONE",
    "TN2": "TONE",
    "TN3": "TONE",
    "TN4": "TONE",

    "C1": "CLAIMS",

    "S1": "SAFETY",
    "S2": "SAFETY",

    "A1": "ACCESS",
    "A2": "ACCESS",
    "A3": "ACCESS",
    "IM1": "ACCESS",
    "IM2": "ACCESS",

    "B1": "PALETTE",
}

# Category-level matching is used only for general policies.
# Facts and terminology require their actual approved IDs.
CATEGORY_TO_CHUNK = {
    "tone": "TONE",
    "claim": "CLAIMS",
    "safety": "SAFETY",
    "accessibility": "ACCESS",
}

LABELS = {
    "verified": (
        "✅",
        "Verified against an approved source",
        "#2B8A3E",
        "#D3F9D8",
    ),

    "unsupported_claim": (
        "⚠️",
        "Unsupported claim: no approved evidence on file",
        "#B35C00",
        "#FFF3BF",
    ),

    "ai_grounded": (
        "🤖",
        "AI-assisted, grounded in an approved rule",
        "#1864AB",
        "#D0EBFF",
    ),

    "ai_safety": (
        "🛡️",
        "AI safety judgement (no brand rule needed): a human confirms",
        "#5F3DC4",
        "#E7E3FF",
    ),

    "ai_unsupported": (
        "🤖⚠️",
        "AI suggestion with no approved source: needs a human decision",
        "#C92A2A",
        "#FFE3E3",
    ),
}


# --------------------------------------------------
# TEXT HELPERS
# --------------------------------------------------

def _tokens(value):
    """Extract lowercase words and numbers."""

    return re.findall(
        r"[\w₹%]+",
        str(value or "").lower(),
    )


def _normalise_id(value):
    """Normalise rule IDs for matching."""

    return str(value or "").strip().upper()


def _safe_list(value):
    """Return a list even if the rulebook value is missing."""

    return value if isinstance(value, list) else []


# --------------------------------------------------
# BUILD APPROVED EVIDENCE INDEX
# --------------------------------------------------

def build_index(rb):
    """Convert the approved rulebook into searchable evidence chunks."""

    rb = rb if isinstance(rb, dict) else {}

    tone = rb.get("tone") or {}
    claims_ev = _safe_list(rb.get("approved_claims"))

    chunks = [

        {
            "id": "TONE",
            "kind": "Tone guideline",
            "title": "Brand tone",
            "always": True,
            "text": (
                "%s Avoid hype words (%s) and pressure phrases (%s)."
                % (
                    tone.get("summary", "Use the approved brand tone."),
                    ", ".join(tone.get("hype_words", [])[:6]),
                    ", ".join(tone.get("pressure_phrases", [])[:5]),
                )
            ),
        },

        {
            "id": "CLAIMS",
            "kind": "Claims policy",
            "title": "Superlative and absolute claims",
            "always": True,
            "text": (
                "Claims such as 'best', 'fastest' or 'guaranteed' "
                "need approved evidence. Approved evidence on file: %s."
                % (
                    "; ".join(map(str, claims_ev))
                    if claims_ev
                    else "none"
                )
            ),
        },

        {
            "id": "SAFETY",
            "kind": "Safety policy",
            "title": "Threats, abuse and unsafe content",
            "always": True,
            "text": (
                "Threats, violence, harassment, hate, scams, illegal "
                "content and exposed personal data must never be published."
            ),
        },

        {
            "id": "ACCESS",
            "kind": "Accessibility rule",
            "title": "Alt text and link text",
            "always": False,
            "text": (
                "Images need alt text, links need descriptive text "
                "(not 'click here'), and images need adequate size and contrast."
            ),
        },

        {
            "id": "PALETTE",
            "kind": "Visual guideline",
            "title": "Brand colours",
            "always": False,
            "text": (
                "Images should use the approved brand colour palette: %s."
                % ", ".join(rb.get("palette") or ["see brand kit"])
            ),
        },
    ]

    # Approved terminology
    for item in _safe_list(rb.get("terminology")):

        if not isinstance(item, dict):
            continue

        bad = _safe_list(item.get("bad"))

        chunks.append({
            "id": str(item.get("id", "")),
            "kind": "Terminology",
            "title": "Use '%s'" % item.get("preferred", ""),
            "always": False,
            "bad": bad,
            "text": (
                "Avoid: %s. Use: %s. %s"
                % (
                    ", ".join(map(str, bad)),
                    item.get("preferred", ""),
                    item.get("why", ""),
                )
            ),
        })

    # Approved facts
    for item in _safe_list(rb.get("facts")):

        if not isinstance(item, dict):
            continue

        if not item.get("id"):
            continue

        chunks.append({
            "id": str(item["id"]),
            "kind": "Approved fact",
            "title": item.get("topic", item["id"]),
            "always": False,
            "topic_regex": item.get("topic_regex"),
            "approved": str(item.get("approved", "")),
            "text": str(item.get("statement", "")),
        })

    return chunks


# --------------------------------------------------
# STEP 1: RETRIEVE RELEVANT EVIDENCE
# --------------------------------------------------

def retrieve(text, rb, k=6):
    """Retrieve approved sources relevant to the current draft."""

    chunks = build_index(rb)

    text = str(text or "")
    low = text.lower()

    tokens = set(_tokens(text))

    numbers = set(
        re.findall(
            r"\d+",
            text.replace(",", ""),
        )
    )

    document_frequency = Counter()

    for chunk in chunks:

        chunk_tokens = set(
            _tokens(
                chunk["text"] + " " + chunk["title"]
            )
        )

        for token in chunk_tokens:
            document_frequency[token] += 1

    total_chunks = max(len(chunks), 1)

    picked = []
    core = []

    for chunk in chunks:

        trigger = 0.0
        reasons = []

        # Terminology matching
        if chunk["kind"] == "Terminology":

            for word in chunk.get("bad", []):

                if re.search(
                    r"(?<!\w)" + re.escape(str(word).lower()) + r"(?!\w)",
                    low,
                ):

                    trigger += 10

                    reasons.append(
                        "draft contains '%s'" % word
                    )

        # Approved fact matching
        elif chunk["kind"] == "Approved fact":

            pattern = chunk.get("topic_regex")

            if pattern:

                try:
                    matched = re.search(pattern, text, re.I)
                except re.error:
                    matched = None

                if matched:

                    trigger += 10

                    reasons.append(
                        "draft mentions %s" % chunk["title"]
                    )

            approved = chunk.get("approved", "")

            if approved and approved in numbers:

                trigger += 4

                reasons.append(
                    "draft contains the number %s" % approved
                )

        # Accessibility matching
        elif chunk["id"] == "ACCESS":

            if re.search(
                r"click here|!\[",
                text,
                re.I,
            ):

                trigger += 10
                reasons.append(
                    "draft has a link or image to check"
                )

        # Word overlap scoring
        chunk_tokens = set(
            _tokens(
                chunk["text"] + " " + chunk["title"]
            )
        )

        overlap = [
            token
            for token in chunk_tokens & tokens
            if len(token) > 3
        ]

        score = trigger + sum(
            math.log(
                1 + total_chunks / document_frequency[token]
            )
            for token in overlap
        )

        if overlap and not trigger:

            reasons.append(
                "shared words: "
                + ", ".join(sorted(overlap)[:4])
            )

        result = {
            "id": chunk["id"],
            "kind": chunk["kind"],
            "title": chunk["title"],
            "text": chunk["text"],
            "score": round(score, 1),
            "why": "; ".join(reasons),
        }

        if chunk.get("always"):

            result["why"] = (
                "core policy, always applied"
                + (
                    "; " + result["why"]
                    if result["why"]
                    else ""
                )
            )

            core.append(result)

        elif trigger > 0 or score >= 3.0:

            picked.append(result)

    picked.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return core + picked[:max(0, int(k))]


# --------------------------------------------------
# STEP 2: GIVE THE AI ONLY RETRIEVED EVIDENCE
# --------------------------------------------------

def grounded_rulebook(rb, retrieved):
    """Create a rulebook containing only retrieved approved sections."""

    rb = rb if isinstance(rb, dict) else {}

    retrieved = retrieved or []

    ids = {
        _normalise_id(item.get("id"))
        for item in retrieved
        if isinstance(item, dict)
    }

    grounded = {}

    # Preserve core rulebook sections.
    # Remove optional sections that were not retrieved.
    for key, value in rb.items():

        if key in ("terminology", "facts", "palette"):

            continue

        grounded[key] = value

    # Only include retrieved terminology.
    grounded["terminology"] = [
        item
        for item in _safe_list(rb.get("terminology"))
        if _normalise_id(item.get("id")) in ids
    ]

    # Only include retrieved facts.
    grounded["facts"] = [
        item
        for item in _safe_list(rb.get("facts"))
        if _normalise_id(item.get("id")) in ids
    ]

    # Include palette only if retrieved.
    if "PALETTE" in ids:

        grounded["palette"] = rb.get("palette", [])

    grounded["grounding_note"] = (
        "Only approved sources relevant to this draft are included. "
        "If a brand-specific fact or rule is not covered here, "
        "say it cannot be verified from the approved sources instead "
        "of guessing. Never invent approved evidence."
    )

    return grounded


# --------------------------------------------------
# FIND THE ACTUAL SUPPORTING SOURCE
# --------------------------------------------------

def _find_evidence_chunk(finding, evidence_index, retrieved_ids):
    """Find a source only if it was actually retrieved."""

    rule = _normalise_id(finding.get("rule"))

    # First: explicit rule ID mapping.
    chunk_id = RULE_TO_CHUNK.get(rule, rule)

    if chunk_id in retrieved_ids:

        return evidence_index.get(chunk_id)

    # Second: category-level mapping for core policies.
    category = str(
        finding.get("category", "")
    ).strip().lower()

    category_chunk = CATEGORY_TO_CHUNK.get(category)

    if category_chunk and category_chunk in retrieved_ids:

        return evidence_index.get(category_chunk)

    # Facts and terminology must match their actual IDs.
    return None


# --------------------------------------------------
# STEP 3: VERIFY EVERY FINDING AGAINST RETRIEVED SOURCES
# --------------------------------------------------

def verify_findings(findings, rb, retrieved=None):
    """
    Label every finding using the evidence actually retrieved.

    verified:
        A rule-based finding matched an approved rule.

    unsupported_claim:
        A claim violates the approved claims policy,
        but its individual claim has no approved proof.

    ai_grounded:
        An AI finding is supported by a retrieved approved rule.

    ai_safety:
        An AI safety finding that does not need a brand rule.

    ai_unsupported:
        An AI finding without a matching retrieved source.
    """

    findings = findings or []

    evidence_chunks = build_index(rb)

    evidence_index = {
        _normalise_id(chunk["id"]): chunk
        for chunk in evidence_chunks
    }

    # Do not attach optional evidence that was never retrieved.
    if retrieved is None:

        retrieved = [
            chunk
            for chunk in evidence_chunks
            if chunk.get("always")
        ]

    retrieved_ids = {
        _normalise_id(item.get("id"))
        for item in retrieved
        if isinstance(item, dict)
    }

    output = []

    for finding in findings:

        if not isinstance(finding, dict):
            continue

        result = dict(finding)

        source = str(
            finding.get("source", "")
        )

        is_ai = source.strip().lower().startswith("ai")

        category = str(
            finding.get("category", "")
        ).strip().lower()

        # Safety findings use general safety judgement.
        if is_ai and category == "safety":

            code = "ai_safety"
            chunk_id = ""
            evidence = (
                "General safety judgement by the AI. "
                "It is not tied to a brand rule, so a human must confirm it."
            )

        else:

            chunk = _find_evidence_chunk(
                finding,
                evidence_index,
                retrieved_ids,
            )

            # A claim can be flagged by the CLAIMS policy,
            # but the policy itself does not prove the marketing claim.
            if category == "claim":

                claims_chunk = evidence_index.get("CLAIMS")

                if (
                    claims_chunk
                    and "CLAIMS" in retrieved_ids
                ):

                    code = "unsupported_claim"
                    chunk_id = "CLAIMS"
                    evidence = claims_chunk["text"]

                else:

                    code = "ai_unsupported"
                    chunk_id = ""
                    evidence = (
                        "The approved claims policy was not retrieved. "
                        "A human must check this claim."
                    )

                    result["confidence"] = (
                        "Unsupported: needs human check"
                    )

            elif not is_ai:

                # Rule-based finding must have a matching approved source.
                if chunk:

                    code = "verified"
                    chunk_id = chunk["id"]
                    evidence = chunk["text"]

                else:

                    code = "ai_unsupported"
                    chunk_id = ""
                    evidence = (
                        "The rule that raised this finding was not "
                        "matched to a retrieved approved source."
                    )

                    result["confidence"] = (
                        "Unverified: needs human check"
                    )

            elif chunk:

                # AI finding with an actual retrieved source.
                code = "ai_grounded"
                chunk_id = chunk["id"]
                evidence = chunk["text"]

            else:

                # Never invent an evidence source.
                code = "ai_unsupported"
                chunk_id = ""
                evidence = (
                    "No retrieved approved rule or fact supports "
                    "this AI finding. Treat it as a suggestion "
                    "and ask a human to decide."
                )

                result["confidence"] = (
                    "Unsupported: needs human check"
                )

                # Reduce unsupported high-severity suggestions.
                if result.get("severity") in ("Critical", "High"):

                    result["severity"] = "Medium"

        result.update({
            "verification": code,
            "evidence_id": chunk_id,
            "evidence": evidence,
        })

        output.append(result)

    return output


# --------------------------------------------------
# SUMMARY COUNTS
# --------------------------------------------------

def summarise(findings):
    """Count findings by verification status."""

    counts = Counter(
        finding.get("verification", "")
        for finding in (findings or [])
    )

    return {
        key: counts.get(key, 0)
        for key in LABELS
    }


# --------------------------------------------------
# DISPLAY VERIFICATION BADGE
# --------------------------------------------------

def badge_html(finding):
    """Generate safe HTML explaining a finding's evidence status."""

    code = finding.get("verification")

    if code not in LABELS:
        return ""

    icon, label, foreground, background = LABELS[code]

    evidence_id = finding.get("evidence_id", "")

    source_html = (
        " · source <b>%s</b>"
        % html.escape(str(evidence_id))
        if evidence_id
        else ""
    )

    evidence_text = html.escape(
        str(finding.get("evidence", ""))
    )

    return (
        '<div style="background:%s;color:%s;'
        'border-radius:10px;padding:7px 12px;'
        'margin:-4px 0 10px;font-size:.82rem">'
        '%s <b>%s</b>%s<br>'
        '<span style="opacity:.9">%s</span>'
        '</div>'
        % (
            background,
            foreground,
            icon,
            html.escape(label),
            source_html,
            evidence_text,
        )
    )


# --------------------------------------------------
# EVIDENCE DISPLAY PANEL
# --------------------------------------------------

def render_panel(st, ev):
    """Show retrieved evidence and verification counts."""

    if not ev:
        return

    summary = ev.get("summary", {})

    pills = "".join(
        (
            '<span style="background:%s;color:%s;'
            'border-radius:999px;padding:4px 12px;'
            'font-size:.8rem;font-weight:700;'
            'margin-right:6px">%s %d %s</span>'
        )
        % (
            LABELS[key][3],
            LABELS[key][2],
            LABELS[key][0],
            summary.get(key, 0),
            html.escape(short),
        )
        for key, short in (
            ("verified", "verified"),
            ("ai_grounded", "AI + source"),
            ("unsupported_claim", "unsupported claims"),
            ("ai_safety", "AI safety"),
            ("ai_unsupported", "AI, no source"),
        )
    )

    st.markdown(
        '<div style="margin:6px 0 8px">%s</div>' % pills,
        unsafe_allow_html=True,
    )

    retrieved = ev.get("retrieved", [])

    with st.expander(
        "📚 Evidence retrieved before the check (%d approved sources)"
        % len(retrieved)
    ):

        st.caption(
            "BrandGuard retrieved these approved rules and facts "
            "before the check. AI findings are matched against "
            "the retrieved sources. Unsupported findings are "
            "not treated as verified."
        )

        rows = [
            {
                "Source": item.get("id", ""),
                "Type": item.get("kind", ""),
                "Approved text": item.get("text", ""),
                "Why retrieved": item.get("why", ""),
            }
            for item in retrieved
        ]

        if rows:

            st.dataframe(
                rows,
                hide_index=True,
                use_container_width=True,
            )

        else:

            st.info(
                "No approved evidence was retrieved."
            )
