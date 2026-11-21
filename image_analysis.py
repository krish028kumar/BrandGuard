"""Improvement 1: comprehensive image analysis for BrandGuard.

Combines, for one uploaded image:
  - OCR (Tesseract) and AI vision to read the text inside the image (English, Hindi, Hinglish)
  - local checks: alt text, size, contrast, brand colours (with % of approved colour coverage)
  - alt text vs text shown in the image
  - logo usage: AI vision against the written logo rules (labelled AI-assisted; a human confirms)
  - the rulebook text checks, run on the text found inside the image
Fail-closed: if the AI vision step fails, status is 'unverified'; with no API key it is 'local_only'. Never 'safe'.
"""
import io
import os
import re

import uploads
from engine import review

DEFAULT_VISUAL_RULES = [
    "The logo must not be stretched, rotated, recoloured, cropped or placed on a busy background.",
    "Keep clear space around the logo and keep it clearly legible.",
    "Use the approved brand colour palette; avoid off-brand colour schemes.",
    "Text over images must be readable (strong contrast) and free of unapproved claims.",
    "Images must not contain unsafe, hateful, sexual, violent or misleading content.",
]
SEV_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}


def _f(rule, cat, sev, text, why, suggestion, source="Image analysis", conf="High"):
    return dict(rule=rule, category=cat, severity=sev, start=0, end=0, text=text, why=why, source=source,
                suggestion=suggestion, replacement=None, confidence=conf)


# ------------------------------------------------------------------ OCR
def run_ocr(data):
    """Return (text, note). Never raises: a missing OCR engine becomes a note, not a crash."""
    try:
        import pytesseract
        from PIL import Image, ImageOps
    except Exception:
        return "", "OCR library not installed."
    try:
        img = Image.open(io.BytesIO(data)).convert("L")
        if img.width < 1000:
            img = img.resize((img.width * 2, img.height * 2))
        img = ImageOps.autocontrast(img)
        for lang in ("eng+hin", "eng"):
            try:
                text = pytesseract.image_to_string(img, lang=lang)
                return re.sub(r"\n{3,}", "\n\n", text).strip(), "OCR language: %s" % lang
            except pytesseract.TesseractNotFoundError:
                return "", "Tesseract is not installed on this server (add packages.txt)."
            except Exception:
                continue
        return "", "OCR could not read this image."
    except Exception as exc:
        return "", "OCR failed: %s" % exc


# ------------------------------------------------------------------ colours
def brand_colour_coverage(data, palette_hex):
    """Share of pixels (0-100) close to an approved brand colour."""
    import numpy as np
    from PIL import Image
    arr = np.asarray(Image.open(io.BytesIO(data)).convert("RGB").resize((120, 120)), dtype=float).reshape(-1, 3)
    pal = np.array([uploads._hex_to_rgb(c) for c in palette_hex], dtype=float)
    d = np.sqrt(((arr[:, None, :] - pal[None, :, :]) ** 2).sum(axis=2)).min(axis=1)
    return round(float((d < 70).mean()) * 100)


# ------------------------------------------------------------------ alt text vs image text
def _words(s):
    return {w for w in re.findall(r"[\w']+", (s or "").lower()) if len(w) >= 4}


def alt_text_gap(alt_text, image_text):
    iw, aw = _words(image_text), _words(alt_text)
    if len(iw) < 3 or not (alt_text or "").strip():
        return None
    return len(iw & aw) / len(iw)


# ------------------------------------------------------------------ main entry point
def analyze_image(data, alt_text="", rulebook=None, use_ai=True):
    rb = rulebook or {}
    try:
        local = uploads.local_image_checks(data, alt_text, rb)
    except Exception as exc:
        raise ValueError("Could not read this image: %s" % exc) from exc

    palette = rb.get("palette") or uploads.DEFAULT_PALETTE
    try:
        coverage = brand_colour_coverage(data, palette)
    except Exception:
        coverage = None
    if coverage is not None:
        for x in local:
            if x["rule"] == "B1":
                x["why"] += " Only %d%% of the image uses approved brand colours." % coverage

    ocr_text, ocr_note = run_ocr(data)

    rb_ai = dict(rb)
    rb_ai["visual_rules"] = rb.get("visual_rules") or DEFAULT_VISUAL_RULES
    status, error, vision_text, vision_findings = "local_only", "", "", []
    if use_ai:
        try:
            vision_text, vision_findings = uploads.vision_review(data, rb_ai, alt_text=alt_text)
            status = "completed"
        except ValueError as exc:  # no API key configured
            status, error = "local_only", str(exc)
        except Exception as exc:
            status, error = "unverified", str(exc)

    if vision_text.strip():
        text_in_image, text_source = vision_text.strip(), "AI vision"
    elif ocr_text.strip():
        text_in_image, text_source = ocr_text.strip(), "OCR"
    else:
        text_in_image, text_source = "", "none"

    extra = []
    gap = alt_text_gap(alt_text, text_in_image)
    if gap is not None and gap < 0.25:
        extra.append(_f("A4", "Accessibility", "Medium", "[alt text misses the image text]",
                        "The image contains text, but the alt text does not repeat it, so screen-reader users would miss it.",
                        "Include the key text shown in the image in the alt text."))

    # Logo usage is judged by AI vision against the written logo rules in rb_ai["visual_rules"].
    # Pixel matching against a logo file was tested and rejected: too unreliable to trust.
    logo_info = {"checked": status == "completed", "method": "AI vision against written logo rules (human confirms)"}

    text_findings = []
    if text_in_image:
        for x in review(text_in_image, rb):
            y = dict(x)
            y["source"] = "Text inside the image (%s) · %s" % (text_source, x["source"])
            text_findings.append(y)

    findings = local + vision_findings + extra + text_findings
    try:
        import evidence
        findings = evidence.verify_findings(findings, rb)
    except Exception:
        pass
    findings.sort(key=lambda x: SEV_ORDER.get(x.get("severity"), 9))

    for x in findings:  # fields the app's existing finding display already understands
        x["message"] = "%s · %s: %s. %s" % (x["severity"], x["category"], x["text"], x["why"])
        x["description"] = x["message"]
        x["recommendation"] = x["suggestion"]
        ev = "Source: %s · Confidence: %s" % (x["source"], x["confidence"])
        if x.get("verification"):
            ev += " · %s" % x["verification"].replace("_", " ")
        x["evidence"] = ev

    return {"status": status, "error": error, "findings": findings, "extracted_text": text_in_image,
            "text_source": text_source, "ocr_note": ocr_note, "colour_coverage": coverage,
            "logo": logo_info, "alt_text_gap": gap}