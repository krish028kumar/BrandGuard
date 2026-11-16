
# 🛡️ BrandGuard
### AI-Powered Brand Compliance & Content Safety Platform

BrandGuard is an AI-powered brand compliance and content safety platform designed to help organizations review, analyze, and maintain consistency across digital content.

It combines rule-based validation with AI-powered moderation to identify potentially harmful content, brand guideline violations, and compliance issues before content is approved or published.

The platform provides a centralized review environment where users can submit content, receive automated findings, apply suggested corrections, and manage structured review and approval workflows.

---

## 🚀 Live Application

<p align="center">
  <a href="https://brandguard-6xhxmmq8zmnb8cdzmjxmej.streamlit.app/">
    <img src="https://img.shields.io/badge/OPEN%20BRANDGUARD-LAUNCH%20LIVE%20APPLICATION-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white" alt="Launch BrandGuard">
  </a>
</p>

<p align="center">
  <a href="https://brandguard-6xhxmmq8zmnb8cdzmjxmej.streamlit.app/">
    <strong>🌐 Access the Live Application</strong>
  </a>
  &nbsp; | &nbsp;
  <a href="https://github.com/krish028kumar/BrandGuard">
    <strong>💻 GitHub Repository</strong>
  </a>
</p>

---

## ✨ Key Features

### 1. AI-Powered Content Moderation

- Analyzes submitted content using AI.
- Identifies potentially harmful or inappropriate content.
- Provides moderation and verification results.
- Distinguishes verified results from incomplete or unverified AI checks.
- Prevents failed AI verification from being automatically classified as safe.

### 2. Brand Compliance Checking

- Validates content against predefined brand guidelines.
- Detects tone-of-voice inconsistencies.
- Checks approved terminology and brand language.
- Identifies violations of approved brand facts.
- Helps maintain consistent brand communication.

### 3. Document Upload & Analysis

- Supports document uploads, including PDF files.
- Extracts text from uploaded documents for compliance checking.
- Analyzes extracted content against predefined brand rules.
- Identifies potential compliance issues in documents.

### 4. Automated Review & Correction

- Generates findings based on detected violations.
- Categorizes findings according to severity:
  - Critical
  - High
  - Medium
  - Low
- Provides suggested corrections.
- Supports before-and-after content comparison.
- Helps streamline the content review process.

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
- Provides a structured content review workflow.

### 6. Feedback Management

- Allows users to submit platform feedback.
- Supports ratings and written comments.
- Enables Admin and Manager to view recent feedback.
- Maintains feedback records for internal product improvement.

### 7. Insights & Reporting

- Maintains records of compliance findings.
- Tracks review activity.
- Provides visibility into submissions and compliance-related insights.
- Helps monitor recurring content issues.

### 8. Rulebook Management

- Maintains centralized brand guidelines.
- Organizes tone, terminology, and approved facts.
- Uses structured rules for consistent content evaluation.
- Supports standardized brand compliance checks.

---

## 🛠️ Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core programming language |
| Streamlit | Interactive web application |
| OpenRouter API | AI-powered content analysis |
| Pandas | Data processing |
| Turso Database | Cloud database storage |
| SQLite / libSQL | Database compatibility |
| HTML | UI components |
| CSS | Interface styling |
| Git | Version control |
| GitHub | Source code management |
| Streamlit Community Cloud | Application deployment |

---

## 🏗️ Project Architecture

```text
BrandGuard/
│
├── app.py              # Main Streamlit application
│
├── ai_check.py         # AI-powered content verification
│
├── uploads.py          # Document upload and text extraction
│
├── database.py         # Database operations
│
├── engine.py           # Rulebook validation and review engine
│
├── ui.py               # Shared UI components and styling
│
├── requirements.txt    # Project dependencies
│
├── .gitignore          # Git ignored files
│
└── README.md           # Project documentation
```

### Application Workflow

```text
          User Submission
                 |
                 v
       Content / Document Upload
                 |
                 v
          Text Extraction
                 |
                 v
       +---------------------+
       |   Review Engine     |
       +---------------------+
                 |
          +------+------+
          |             |
          v             v
    Rule-Based       AI-Powered
    Validation       Moderation
          |             |
          +------+------+
                 |
                 v
        Findings & Severity
                 |
                 v
       Suggested Corrections
                 |
                 v
       Review & Approval
                 |
                 v
        Database Storage
                 |
                 v
       Insights & Reporting
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

### Step 2: Navigate to the project directory

```bash
cd BrandGuard
```

### Step 3: Create a virtual environment

```bash
python -m venv venv
```

Activate the environment:

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

Example configuration:

```toml
OPENROUTER_API_KEY = "your_api_key"
TURSO_DATABASE_URL = "your_database_url"
TURSO_AUTH_TOKEN = "your_auth_token"
```

Use the exact variable names expected by the application code.

**Important:** Never commit actual API keys, authentication tokens, or database credentials to GitHub.

### Step 6: Run the application locally

```bash
streamlit run app.py
```

The application will run locally for development and testing.

To access the publicly deployed application, visit:

**[Launch BrandGuard – Live Application](https://brandguard-6xhxmmq8zmnb8cdzmjxmej.streamlit.app/)**

---

## ☁️ Deployment

BrandGuard is deployed using **Streamlit Community Cloud**.

### Deployment Process

1. Push the project source code to GitHub.
2. Connect the GitHub repository to Streamlit Community Cloud.
3. Select `app.py` as the main application file.
4. Configure the required API and database secrets.
5. Deploy the application.

### Production Application

<p align="center">
  <a href="https://brandguard-6xhxmmq8zmnb8cdzmjxmej.streamlit.app/">
    <img src="https://img.shields.io/badge/Streamlit-Live%20Deployment-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white" alt="Streamlit Live Deployment">
  </a>
</p>

<p align="center">
  <a href="https://brandguard-6xhxmmq8zmnb8cdzmjxmej.streamlit.app/">
    <strong>Open BrandGuard</strong>
  </a>
</p>

---

## 🔐 Security Considerations

- Store API keys and database credentials securely.
- Never expose authentication tokens in source code.
- Treat AI-generated moderation results as decision-support information.
- An incomplete AI verification must not be interpreted as a safe result.
- Apply appropriate access controls to administrative operations and user data.
- Keep sensitive configuration files out of version control.

---

## 🎯 Project Objective

The primary objective of BrandGuard is to simplify brand compliance and content moderation through automation.

By combining rule-based validation, AI-powered analysis, document processing, and structured approval workflows, BrandGuard aims to:

- Reduce manual content review effort.
- Improve brand consistency across digital communications.
- Identify potentially harmful and non-compliant content.
- Standardize content review and approval processes.
- Provide actionable findings and correction suggestions.

BrandGuard brings content safety, brand governance, and automated review capabilities together in one platform.

---

## 👨‍💻 About the Developer

### Krish Kumar

**Information Science and Engineering (ISE)**  
Dayananda Sagar College of Engineering (DSCE)  
Bengaluru, Karnataka, India

**Academic Batch:** 2024–2028

Interested in software engineering, artificial intelligence, problem-solving, and building practical technology solutions.

Currently focused on strengthening skills in Data Structures and Algorithms, software development, and AI-powered applications.

**GitHub Profile:** [krish028kumar](https://github.com/krish028kumar)

---

<p align="center">
  <strong>🛡️ BrandGuard</strong>
  <br>
  Making brand compliance smarter, safer, and more consistent.
  <br><br>
  <a href="https://brandguard-6xhxmmq8zmnb8cdzmjxmej.streamlit.app/">
    <strong>🚀 Explore the Live Application</strong>
  </a>
</p>
