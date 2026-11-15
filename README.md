# BrandGuard (Team Binary Brains)

AI-assisted brand governance and content moderation. Paste a draft, get explained findings that cite the approved rule or fact, review a suggested rewrite (never auto-applied), and send it through a reviewer approval flow with comments and version history.

## What works
- Built-in rule checks: terminology, tone, unsupported claims, facts vs approved facts, accessibility, basic safety words
- AI moderation (English, Hindi, Hinglish) through OpenRouter. If the AI call fails, the result is shown as UNVERIFIED and is never treated as Safe
- Roles (Creator, Reviewer, Manager, Admin), approve / request changes / reject with comments, revision history
- Insights: repeated mistakes and rules people keep dismissing

## Run locally
    pip install -r requirements.txt
    streamlit run app.py
Add your key in `.streamlit/secrets.toml` (never commit it): `OPENROUTER_API_KEY = "..."`

## Disclosure
- Libraries: Streamlit, pandas (open source)
- External service: OpenRouter (routes to third-party AI models). Draft text is sent there only when the AI check runs
- AI assistance: the code was written with help from AI assistants (Claude, ChatGPT) and reviewed by the author
- The sample brand "BrightCart" and sample posts are invented for the demo

## Planned for Round 3
Image review (logo, palette, contrast), document import (PDF/DOCX), real login and permissions, richer insights.
