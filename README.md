
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
  <a href="https://brandguard-6xhxmmq8zmnb8cdzmjxmej.streamlit.app/"><strong>🌐 Live Application</strong></a>
  &nbsp; | &nbsp;
  <a href="https://github.com/krish028kumar/BrandGuard"><strong>💻 GitHub Repository</strong></a>
</p>

---

## ✨ Key Features

### 1. AI-Powered Content Moderation
- Analyzes submitted content using an AI-powered verification system.
- Identifies potentially harmful or inappropriate content.
- Provides moderation and verification results.
- Distinguishes verified results from incomplete or unsuccessful AI checks.
- Prevents failed AI verification from being automatically classified as safe or approved.

### 2. Brand Compliance Checking
- Validates content against predefined brand guidelines.
- Detects tone-of-voice inconsistencies.
- Checks approved terminology and brand language.
- Identifies potential violations of approved brand facts.
- Provides findings to help maintain consistent brand communication.

### 3. Document Upload and Analysis
- Supports document uploads, including PDF files.
- Extracts text from supported documents.
- Evaluates extracted content against predefined brand rules.
- Identifies potential compliance issues in uploaded documents.

### 4. Image Analysis
- Provides an image-analysis workflow through the image analysis module.
- Supports visual content assessment where implemented in the application.
- Helps extend brand compliance review beyond text-only submissions.

### 5. Automated Review and Correction
- Generates findings based on detected violations.
- Categorizes findings by severity:
  - Critical
  - High
  - Medium
  - Low
- Provides suggested corrections.
- Supports before-and-after content comparison.
- Helps streamline the content review process.

### 6. Evidence and Verification
- Includes an evidence-processing component for supporting content verification.
- Uses available brand rules and supporting information during review.
- Helps make compliance findings more explainable.
- AI-generated findings remain subject to verification and human review.

### 7. Review and Approval Workflow

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

### 8. Feedback Management
- Allows users to submit platform feedback.
- Supports ratings and written comments.
- Enables authorized roles to view feedback.
- Maintains feedback records for product improvement.

### 9. Insights and Reporting
- Maintains records of compliance findings.
- Tracks review activity.
- Provides visibility into submissions and compliance-related insights.
- Helps monitor recurring content issues.

### 10. Rulebook Management
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
| Google Gemini API | AI-powered content analysis, where configured |
| OpenRouter API | AI API integration, where configured |
| Pandas | Data processing |
| Turso Database | Cloud database storage |
| SQLite / libSQL | Database connectivity |
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
├── engine.py           # Rulebook validation and review engine
│
├── uploads.py          # Document upload and text extraction
│
├── image_analysis.py   # Image analysis functionality
│
├── evidence.py         # Evidence processing and verification
│
├── database.py         # Database operations
│
├── ui.py               # Shared UI components and styling
│
├── requirements.txt    # Project dependencies
│
├── .streamlit/         # Streamlit configuration and secrets setup
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
        Content / Document / Image
                    |
                    v
          Input Processing
                    |
                    v
          Review Engine
                    |
           +--------+--------+
           |                 |
           v                 v
      Rule-Based         AI-Powered
      Validation         Verification
           |                 |
           +--------+--------+
                    |
                    v
          Findings and Severity
                    |
                    v
          Suggested Corrections
                    |
                    v
          Review and Approval
                    |
                    v
            Database Storage
                    |
                    v
           Insights and Reporting
```

---

## ⚙️ Installation and Setup

### Prerequisites
- Python 3.10 or later
- Git
- Required AI API credentials
- Turso database credentials, if using the cloud database configuration

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

Configure the API and database credentials through Streamlit secrets.

The variable names must match those read by the application's configuration and AI modules.

Example:

```toml
GEMINI_API_KEY = "your_gemini_api_key"
TURSO_DATABASE_URL = "your_database_url"
TURSO_AUTH_TOKEN = "your_auth_token"
```

If your active deployment uses OpenRouter, configure the exact OpenRouter secret name expected by `ai_check.py` instead.

**Important:** Never commit API keys, authentication tokens, or database credentials to GitHub.

### Step 6: Run the application locally

```bash
streamlit run app.py
```

The application will be available locally through the Streamlit development server.

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
  <a href="https://brandguard-6xhxmmq8zmnb8cdzmjxmej.streamlit.app/"><strong>🚀 Open BrandGuard</strong></a>
</p>

---

## 🔐 Security Considerations

- Store API keys and database credentials securely.
- Never expose authentication tokens in source code.
- Use role-based access controls for administrative operations.
- Treat AI-generated moderation results as decision-support information.
- An incomplete AI verification must not be interpreted as a safe or approved result.
- Keep sensitive configuration files out of version control.

---

## 🎯 Project Objective

The primary objective of BrandGuard is to simplify brand compliance and content moderation through automation.

By combining rule-based validation, AI-powered analysis, document processing, image analysis, and structured approval workflows, BrandGuard aims to:

- Reduce manual content review effort.
- Improve brand consistency across digital communications.
- Identify potentially harmful and non-compliant content.
- Standardize content review and approval processes.
- Provide actionable findings and correction suggestions.
- Support more consistent and explainable content verification.

BrandGuard brings content safety, brand governance, and automated review capabilities together in one platform.

---

## 🚀 Future Scope

Planned areas for further development include:

- More comprehensive computer-vision-based logo and visual guideline verification.
- Improved evidence retrieval and source-level traceability.
- Advanced compliance analytics and recurring violation insights.
- More comprehensive rulebook version management.
- Enhanced reviewer collaboration and governance capabilities.
- Expanded accessibility and visual consistency checks.

---

## 👨‍💻 About the Developer

### Krish Kumar

**Information Science and Engineering (ISE)**  
Dayananda Sagar College of Engineering (DSCE)  
Bengaluru, Karnataka, India

**Academic Batch:** 2024–2028

Interested in software engineering, artificial intelligence, problem-solving, and building practical technology solutions.

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
