
# 🛡️ BrandGuard
### AI-Powered Brand Compliance & Content Safety Platform

BrandGuard is an AI-powered brand compliance platform designed to help organizations review, analyze, and maintain brand consistency across digital content.

It combines rule-based validation with AI-powered moderation to identify potentially harmful content, brand guideline violations, and compliance issues before content gets approved or published.

## 🌐 Live Application

🚀 **Live Demo:** [Launch BrandGuard](https://brandguard-6xhxmmq8zmnb8cdzmjxmej.streamlit.app/)

💻 **GitHub Repository:** [View Source Code](https://github.com/krish028kumar/BrandGuard)

## ✨ Key Features

### 1. AI-Powered Content Moderation
- AI-powered content analysis.
- Identifies potentially harmful or inappropriate content.
- Provides moderation and verification results.
- Distinguishes verified results from incomplete AI checks.

### 2. Brand Compliance Checking
- Validates content against predefined brand guidelines.
- Detects tone-of-voice inconsistencies.
- Checks approved terminology and brand language.
- Identifies violations of approved brand facts.

### 3. Document Upload & Analysis
- Supports PDF document uploads.
- Extracts text for compliance checking.
- Analyzes uploaded content against brand rules.
- Identifies potential compliance issues.

### 4. Automated Review & Correction
- Generates findings based on detected violations.
- Categorizes findings by severity:
  - Critical
  - High
  - Medium
  - Low
- Provides suggested corrections.
- Supports before-and-after content comparison.

### 5. Review & Approval Workflow
Supports multiple application roles:
- Admin
- Manager
- Reviewer
- Creator

Additional capabilities:
- Maintains submission history and revisions.
- Supports reviewer comments.
- Tracks approval status and review progress.

### 6. Feedback Management
- Collects platform ratings and written feedback.
- Allows Admin and Manager to view recent feedback.
- Stores feedback for product improvement.

### 7. Insights & Reporting
- Maintains compliance finding records.
- Tracks review activity.
- Provides insights into submissions and compliance issues.

### 8. Rulebook Management
- Maintains centralized brand guidelines.
- Organizes tone, terminology, and approved facts.
- Uses structured rules for consistent content evaluation.

## 🛠️ Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core programming language |
| Streamlit | Web application interface |
| OpenRouter API | AI-powered content analysis |
| Pandas | Data processing |
| Turso Database | Cloud database storage |
| SQLite / libSQL | Database compatibility |
| HTML & CSS | Interface styling |
| Git & GitHub | Version control |
| Streamlit Community Cloud | Application deployment |

## 🏗️ Project Architecture

```text
BrandGuard/
│
├── app.py
├── ai_check.py
├── uploads.py
├── database.py
├── engine.py
├── ui.py
│
├── requirements.txt
├── .gitignore
└── README.md
```

## ⚙️ Installation & Setup

### Prerequisites
- Python 3.10 or later
- Git
- OpenRouter API credentials
- Turso database credentials

### 1. Clone the repository

```bash
git clone https://github.com/krish028kumar/BrandGuard.git
```

### 2. Navigate to the project

```bash
cd BrandGuard
```

### 3. Create a virtual environment

```bash
python -m venv venv
```

Activate on Windows:

```bash
venv\Scripts\activate
```

Linux / macOS:

```bash
source venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure application secrets

Configure the required API and database credentials using Streamlit secrets.

Example:

```toml
OPENROUTER_API_KEY = "your_api_key"
TURSO_DATABASE_URL = "your_database_url"
TURSO_AUTH_TOKEN = "your_auth_token"
```

Use the exact variable names expected by the application. Never upload actual API keys or authentication tokens to GitHub.

### 6. Run the application locally

```bash
streamlit run app.py
```

## ☁️ Deployment

BrandGuard is deployed using **Streamlit Community Cloud**.

Deployment configuration:
- Source Code: GitHub
- Main Application File: `app.py`
- Hosting: Streamlit Community Cloud
- Database: Turso Cloud

🚀 **Live Application:** https://brandguard-6xhxmmq8zmnb8cdzmjxmej.streamlit.app/

## 🔐 Security Considerations

- Store API keys and database credentials securely.
- Never expose authentication tokens in source code.
- Treat AI-generated moderation results as decision-support information.
- Do not interpret incomplete AI verification as a safe result.
- Apply appropriate access controls to administrative operations and user data.

## 🎯 Project Objective

The primary objective of BrandGuard is to simplify brand compliance and content moderation through automation.

By combining rule-based validation, AI-powered analysis, document processing, and structured approval workflows, BrandGuard aims to reduce manual review effort, improve consistency, and help organizations maintain their brand identity across digital communications.

## 👨‍💻 About the Developer

**Krish Kumar**

Information Science and Engineering Student  
Dayananda Sagar College of Engineering (DSCE), Bengaluru  
2024–2028 Batch

Interested in software engineering, artificial intelligence, problem-solving, and building practical technology solutions.

**GitHub:** [krish028kumar](https://github.com/krish028kumar)

---

**BrandGuard — Making brand compliance smarter, safer, and more consistent.**
