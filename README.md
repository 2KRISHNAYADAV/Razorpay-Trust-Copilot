# 🛡️ Razorpay Trust Copilot (RTC)

<div align="center">

![Razorpay Trust Copilot](https://img.shields.io/badge/Razorpay-Trust%20Copilot-2563EB?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0id2hpdGUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHBhdGggZD0iTTEyIDJMMiA3bDEwIDUgMTAtNS0xMC01ek0yIDE3bDEwIDUgMTAtNS0xMC01LTEwIDV6TTIgMTJsMTAgNSAxMC01LTEwLTUtMTAgNXoiLz48L3N2Zz4=)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![XGBoost](https://img.shields.io/badge/XGBoost-ML%20Model-FF6600?style=for-the-badge)
![Gemini AI](https://img.shields.io/badge/Gemini-AI%20Powered-4285F4?style=for-the-badge&logo=google&logoColor=white)

**An AI-powered merchant fraud-risk scoring and explainability platform** built for Razorpay's internal Trust & Safety team. Combines XGBoost ML scoring, SHAP explainability, and Gemini-powered natural language reasoning into a single analyst-facing console.

[🚀 Live Demo](#deployment) • [📖 API Docs](#api-reference) • [🧠 ML Model](#ml-model) • [⚙️ Setup](#getting-started)

</div>

---

## 📌 Overview

Razorpay Trust Copilot (RTC) is an end-to-end **Merchant Risk Intelligence System** that:

- **Scores merchants** using a trained XGBoost model with 16 risk features
- **Explains decisions** in plain English via Google Gemini AI
- **Tiers cases** automatically (`auto_clear`, `agent_review`, `escalate`)
- **Provides SHAP-based feature attribution** for every prediction
- **Powers an Ops Console** — a beautiful analyst dashboard for case management
- **Includes an EDA Dashboard** — interactive charts for data exploration

---

## 🏗️ Architecture

```
razorpay-trust-copilot/
├── backend/                  # FastAPI backend
│   ├── main.py               # API routes & app entrypoint
│   ├── scoring.py            # XGBoost + SHAP scoring engine
│   ├── agent.py              # Gemini AI explanation & assistant
│   ├── store.py              # In-memory case store
│   ├── auth.py               # Session auth & rate limiting
│   ├── schemas.py            # Pydantic request/response models
│   └── requirements.txt      # Python dependencies
├── frontend/                 # Vanilla JS + HTML frontend
│   ├── index.html            # Ops Console (main analyst dashboard)
│   ├── portal.html           # Merchant self-serve portal
│   ├── eda.html              # EDA / Analytics Dashboard
│   ├── styles.css            # Shared design system
│   ├── app.js                # Ops Console logic
│   └── eda.js                # EDA charts & filters
├── model/
│   └── risk_model.json       # Trained XGBoost model (JSON)
├── data/
│   ├── scored_cases.json     # Pre-scored case database
│   └── flagged_cases.csv     # Flagged case exports
├── notebook/
│   └── merchant_risk_copilot.ipynb  # Training & EDA notebook
├── render.yaml               # Render.com deployment config
└── vercel.json               # Vercel frontend config
```

---

## ✨ Features

### 🔍 Ops Console (Analyst Dashboard)
- **Real-time case table** — filterable by risk tier, searchable by merchant ID
- **Risk tier badges** — `AUTO CLEAR` / `AGENT REVIEW` / `ESCALATE` with color coding
- **Detail panel** — full SHAP attribution, plain-language explanation, resolve workflow
- **Trust Assistant** — ask Gemini AI questions about any case (rate-limited, 20 q/case)
- **CSV export** — one-click export of filtered/resolved cases
- **Live toast notifications** — real-time UI feedback

### 📊 EDA Dashboard
- Interactive Chart.js visualizations (score distributions, tier breakdowns, MCC heatmaps)
- Stats summary row (total cases, avg score, escalation rate)
- Filterable by MCC category and risk tier

### 🌐 Merchant Portal
- Self-service case lookup with OTP-style verification flow
- Rate-limited access — prevents enumeration attacks
- Mobile-responsive design

### 🤖 AI Backend
| Component | Technology |
|-----------|-----------|
| Risk Scoring | XGBoost (trained on 16 numeric features) |
| Explainability | SHAP TreeExplainer |
| NL Explanation | Google Gemini 1.5 Flash |
| Case Assistant | Gemini function-calling agent |
| API Framework | FastAPI + Pydantic v2 |
| Auth | Session tokens + rate limiting |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- A Google Gemini API key → [Get one free](https://aistudio.google.com/app/apikey)

### 1. Clone the Repository
```bash
git clone https://github.com/2KRISHNAYADAV/RTC.git
cd RTC
```

### 2. Set Up the Backend
```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure Environment
Create a `.env` file (or set environment variable):
```bash
# Windows PowerShell
$env:GEMINI_API_KEY = "your-gemini-api-key-here"

# macOS/Linux
export GEMINI_API_KEY="your-gemini-api-key-here"
```

### 4. Run the Server
```bash
# From the repo root
uvicorn backend.main:app --reload --port 8000
```

### 5. Open the Frontend
Navigate to: [http://localhost:8000](http://localhost:8000)

- **Ops Console**: `http://localhost:8000/index.html`
- **EDA Dashboard**: `http://localhost:8000/eda.html`
- **Merchant Portal**: `http://localhost:8000/portal.html`
- **API Docs**: `http://localhost:8000/docs`

---

## 📡 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Liveness check |
| `GET` | `/cases` | List all scored cases (filter: `tier`, sort: `risk_score`) |
| `GET` | `/cases/resolved` | List analyst-resolved cases |
| `GET` | `/cases/{case_id}` | Get single case with AI explanation |
| `POST` | `/score` | Live-score a merchant (16 features) |
| `POST` | `/cases/{case_id}/resolve` | Record analyst verdict |
| `POST` | `/cases/{case_id}/assistant` | Ask Trust Assistant about a case |
| `POST` | `/auth/case/request-code` | Request OTP for merchant portal |
| `POST` | `/auth/case/verify` | Verify OTP and get session |
| `POST` | `/auth/logout` | Invalidate session |

### Score Request Example
```json
POST /score
{
  "transaction_volume_30d": 150000,
  "avg_txn_amount": 2500,
  "chargeback_rate": 0.08,
  "refund_rate": 0.12,
  "failed_txn_rate": 0.05,
  "new_card_ratio": 0.45,
  "intl_txn_ratio": 0.30,
  "high_value_txn_ratio": 0.15,
  "velocity_score": 0.72,
  "dispute_rate": 0.06,
  "account_age_days": 45,
  "kyc_score": 0.60,
  "business_category_risk": 0.85,
  "device_fingerprint_score": 0.40,
  "night_txn_ratio": 0.35,
  "mcc_category": "digital_goods"
}
```

---

## 🧠 ML Model

The XGBoost model is trained on 16 engineered features:

| Feature | Description |
|---------|-------------|
| `transaction_volume_30d` | Total transaction amount in last 30 days |
| `avg_txn_amount` | Average transaction amount |
| `chargeback_rate` | Ratio of chargebacks to total transactions |
| `refund_rate` | Ratio of refunds |
| `failed_txn_rate` | Failed transaction ratio |
| `new_card_ratio` | Ratio of new/unseen card numbers |
| `intl_txn_ratio` | International transaction ratio |
| `high_value_txn_ratio` | High-value transaction ratio |
| `velocity_score` | Transaction velocity anomaly score |
| `dispute_rate` | Dispute filing ratio |
| `account_age_days` | Days since merchant onboarding |
| `kyc_score` | KYC verification completeness score |
| `business_category_risk` | MCC-based inherent risk score |
| `device_fingerprint_score` | Device trust score |
| `night_txn_ratio` | Off-hours transaction ratio |
| `mcc_category` | Merchant Category Code group |

**Output tiers:**
- `auto_clear` — risk score < 0.35
- `agent_review` — risk score 0.35–0.65
- `escalate` — risk score > 0.65

---

## ☁️ Deployment

### Render (Backend + Frontend)
The project includes `render.yaml` for one-click Render.com deployment:

1. Fork/push this repo to your GitHub account
2. Connect repo to [Render.com](https://render.com)
3. Add `GEMINI_API_KEY` as an environment variable in the Render dashboard
4. Deploy!

### Vercel (Frontend Only)
```bash
vercel deploy
```
The `vercel.json` routes all API calls to the Render backend.

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python, FastAPI, Uvicorn |
| **ML** | XGBoost, SHAP, NumPy, Pandas |
| **AI** | Google Gemini 1.5 Flash (`google-generativeai`) |
| **Frontend** | Vanilla HTML/CSS/JS, Chart.js |
| **Auth** | Cookie-based sessions, in-memory rate limiting |
| **Deployment** | Render (backend), Vercel (frontend) |

---

## 📁 Data & Notebook

The [`notebook/merchant_risk_copilot.ipynb`](notebook/merchant_risk_copilot.ipynb) contains:
- Full EDA on merchant transaction patterns
- Feature engineering pipeline
- XGBoost model training & hyperparameter tuning
- SHAP global/local explainability analysis
- Threshold calibration for tier assignment

---

## 🔐 Security Notes

- All analyst API routes require a valid session cookie
- Merchant portal uses OTP-style challenge to prevent case enumeration
- Rate limiting: 5 requests/min and 20 total questions per case on the AI assistant
- CORS is open for hackathon purposes — lock down `allow_origins` in production

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

---

## 📄 License

This project is built as part of a Razorpay Buildathon. All rights reserved.

---

<div align="center">

Built with ❤️ by **Krishna Yadav** (@2KRISHNAYADAV)

⭐ Star this repo if you found it useful!

</div>
