
# 🛡️ BrandGuard

### AI-Powered Brand Compliance & Content Safety Platform

BrandGuard is an AI-powered brand compliance platform designed to help organizations review, analyze, and maintain brand consistency across digital content.

It combines rule-based validation with AI-powered moderation to identify potentially harmful content, brand guideline violations, and compliance issues before content gets approved or published.

The platform provides a centralized review workflow where users can submit content, receive automated findings, apply corrections, and manage approval decisions.

## 🌐 Live Application

**Live Demo:** [Launch BrandGuard](https://brandguard-6xhxmmq8zmnb8cdzmjxmej.streamlit.app/)

**GitHub Repository:** [View Source Code](https://github.com/krish028kumar/BrandGuard)

---

## ✨ Key Features

### 1. AI-Powered Content Moderation

- Analyzes submitted content using AI.
- Identifies potentially harmful or inappropriate content.
- Provides moderation and verification results.
- Distinguishes verified results from incomplete or unverified AI checks.
- Does not automatically classify failed AI verification as safe.

### 2. Brand Compliance Checking

- Validates content against predefined brand guidelines.
- Detects tone-of-voice inconsistencies.
- Checks terminology and approved brand language.
- Identifies violations of approved brand facts.

### 3. Document Upload & Analysis

- Supports document uploads, including PDF files.
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

Supports different application roles:

- Admin
- Manager
- Reviewer
- Creator

Additional capabilities:

- Maintains submission history and revisions.
- Supports reviewer comments.
- Tracks approval status and review progress.

### 6. Feedback Management

- Allows users to submit platform feedback.
- Supports ratings and written comments.
- Enables Admin and Manager to view recent feedback.
- Stores feedback for internal product improvement.

### 7. Insights & Reporting

- Maintains records of compliance findings.
- Tracks review activity.
- Provides visibility into submissions and compliance-related insights.

### 8. Rulebook Management

- Maintains centralized brand guidelines.
- Organizes tone, terminology, and approved facts.
- Uses structured rules for consistent content evaluation.

---

## 🛠️ Technology Stack

| Technology                | Purpose                     |
| ------------------------- | --------------------------- |
| Python                    | Core programming language   |
| Streamlit                 | Web application interface   |
| OpenRouter API            | AI-powered content analysis |
| Pandas                    | Data processing             |
| Turso Database            | Cloud database storage      |
| SQLite / libSQL            | Database compatibility      |
| HTML & CSS                 | Interface styling           |
| Git & GitHub               | Version control             |
| Streamlit Community Cloud | Application deployment      |

---

## 🏗️ Project Architecture

```text
BrandGuard/
│
├── app.py              # Main Streamlit application
├── ai_check.py         # AI-powered content verification
├── uploads.py          # Document upload and text extraction
├── database.py         # Database operations
├── engine.py           # Rulebook validation and review engine
├── ui.py               # Shared UI components and styling
│
├── requirements.txt    # Project dependencies
├── .gitignore          # Git ignored files
└── README.md           # Project documentation
```

---

## ⚙️ Installation & Setup

### Prerequisites

- Python 3.10 or later
- Git
- OpenRouter API credentials
- Turso database credentials

### Step 1: Clone the repository

```bash
git clone https://github.com/krish028kumar/BrandGuard.git
```

### Step 2: Navigate to the project

```bash
cd BrandGuard
```

### Step 3: Create a virtual environment

```bash
python -m venv venv
```

Activate it:

**Windows:**

```bash
venv\Scripts\activate
```

**Linux / macOS:**

```bash
source venv/bin/activate
```

### Step 4: Install dependencies

```bash
pip install -r requirements.txt
```

### Step 5: Configure application secrets

Configure the required API and database credentials using Streamlit secrets.

Example:

```toml
OPENROUTER_API_KEY = "your_api_key"
TURSO_DATABASE_URL = "your_database_url"
TURSO_AUTH_TOKEN = "your_auth_token"
```

Use the exact variable names expected by the application code. Never upload actual API keys, authentication tokens, or database credentials to GitHub.

### Step 6: Run the application locally

```bash
streamlit run app.py
```

The application will run locally for development and testing.

**For the publicly accessible deployed version, visit:**

[🚀 Launch BrandGuard](https://brandguard-6xhxmmq8zmnb8cdzmjxmej.streamlit.app/)

---

## ☁️ Deployment

BrandGuard is deployed using Streamlit Community Cloud.

Deployment process:

1. Push the project repository to GitHub.
2. Connect the GitHub repository to Streamlit Community Cloud.
3. Select `app.py` as the main application file.
4. Configure the required API and database secrets.
5. Deploy the application.

**Live Application:** [Launch BrandGuard](https://brandguard-6xhxmmq8zmnb8cdzmjxmej.streamlit.app/)

---

## 🔐 Security Considerations

- Store API keys and database credentials securely.
- Do not expose authentication tokens in source code.
- Treat AI-generated moderation results as decision-support information.
- An incomplete AI verification must not be interpreted as a safe result.
- Apply appropriate access controls to administrative operations and user data.

---

## 🎯 Project Objective

The primary objective of BrandGuard is to simplify brand compliance and content moderation through automation.

By combining rule-based validation, AI-powered analysis, document processing, and structured approval workflows, BrandGuard aims to reduce manual review effort, improve consistency, and help organizations maintain their brand identity across digital communications.

---

## 👨‍💻 About the Developer

**Krish Kumar**

Information Science and Engineering Student  
**Dayananda Sagar College of Engineering (DSCE), Bengaluru**  
2024–2028 Batch

Interested in software engineering, artificial intelligence, problem-solving, and building practical technology solutions.

Currently focused on strengthening skills in Data Structures and Algorithms, software development, and AI-powered applications.

**GitHub:** [krish028kumar](https://github.com/krish028kumar)

---

*BrandGuard — Making brand compliance smarter, safer, and more consistent.*
