<<<<<<< HEAD
# BrandGuard (Team Binary Brains, Round 2)

Pre-publication brand check. Paste a draft, get findings that cite the approved rule or fact, see a suggested rewrite (never auto-applied), and send it through a reviewer approval flow with comments and version history.

## What works now
- Rule checks: terminology, tone, unsupported claims ("Unverified: needs human check"), facts vs approved facts, basic accessibility (alt text, link text)
- Explained findings with rule ID, source and confidence
- Suggested rewrite with before/after diff; user accepts, edits or dismisses each fix
- Roles (Creator, Reviewer, Manager, Admin), approve / request changes / reject with comments, revision history
- Insights: repeated mistakes and rules people keep dismissing
- Optional AI second opinion (Claude API), only if a key is set; off by default

## Run locally
    pip install -r requirements.txt
    streamlit run app.py

## Disclosure
- Libraries: Streamlit, pandas, anthropic (open source / API client)
- External service: Claude API by Anthropic (optional, sends draft text only when the user clicks the button)
- AI assistance: the code was written with help from an AI assistant (Claude) and reviewed by the author
- Sample brand "BrightCart" and sample posts are invented for the demo

## Not built yet (planned for Round 3)
Image review (logo, palette, contrast), document import (PDF/DOCX), richer insights.
=======
# BrandGuard
AI-powered BrandGuard platform for detecting harmful, threatening, abusive, and unsafe brand-related content using AI and moderation rules.
>>>>>>> 86d677343cd82d24739dfe6d0f617a002bc2000c
