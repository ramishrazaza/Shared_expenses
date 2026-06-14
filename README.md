# ShareLedger: Shared Expenses & CSV Anomaly Resolution App

ShareLedger is a production-ready shared expenses application designed to solve the challenges flatmates face when managing group bills, dynamic membership histories, multi-currency expenses, and messy spreadsheet logs.

This application is built for the Spreetail Software Engineering Internship coding assignment.

---

## 🚀 Key Features

* **JWT Authentication**: Secure user registration and login portal.
* **Dynamic Membership History**: Tracks flatmates joining and leaving over time (e.g., Meera leaving in March, Sam joining in April) and ensures split calculations align with active dates.
* **Multi-Currency Splits**: Ingests USD and INR expenses, applying currency conversion rates.
* **Equal, Percentage, & Share Ratios**: Supports all split types appearing in the CSV.
* **Simplified Debts (Aisha's Request)**: Greedy flow-simplification algorithm minimizing the number of settlement payments.
* **Verifiable Balance Audit Trail (Rohan's Request)**: Detailed chronological transaction breakdown showing exactly where every balance penny comes from.
* **Interactive CSV Import Engine (Meera's Request)**: Dry-run uploads, flagging **21 anomalies** under 12 categories. Users can review, Resolve (modify fields), or Ignore (skip/delete duplicates) rows before saving.
* **Immutable Audit Trail**: View log history of corrections and membership changes.

---

## 🛠️ Technology Stack

* **Backend**: Django, Django REST Framework (DRF), SimpleJWT
* **Frontend**: React (Vite), Tailwind CSS, Axios, Lucide Icons
* **Database**: SQLite (Local Dev), Neon PostgreSQL (Production)
* **Deployment**: Render (Backend), Vercel (Frontend), Neon PostgreSQL (Database)

---

## 📦 Project Structure

```text
shared-expenses-app/
├── backend/                     # Django app & configuration
│   ├── config/                  # Settings, URLs, and WSGI
│   └── expenses/                # Core split and CSV import services
│       ├── services/            # balance_service.py, import_service.py
│       ├── management/          # seed_data.py
│       └── tests.py             # Unit tests (math validation)
├── frontend/                    # Vite React SPA
│   ├── src/
│   │   ├── pages/               # Login, Dashboard, Groups, ImportCSV, ImportReport, AuditLog
│   │   ├── components/          # Navbar
│   │   └── services/            # api.js (Axios)
│   └── tailwind.config.js
├── SCOPE.md                     # Anomaly log and DB schema definitions
├── DECISIONS.md                 # Technical decisions log
├── AI_USAGE.md                  # Assistant usage & debugging log
└── DEPLOYMENT.md                # Render/Vercel/Neon deployment guide
```

---

## ⚡ Setup & Run Instructions

### Prerequisites
* Python 3.10+
* Node.js 18+
* npm

### 1. Backend Setup
1. Open a terminal and navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Initialize and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # macOS/Linux:
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run database migrations:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```
5. Seed database with flatmates and membership history:
   ```bash
   python manage.py seed_data
   ```
6. Start the local server:
   ```bash
   python manage.py runserver
   ```
   *Backend API will run at: `http://127.0.0.1:8000/api/`*

### 2. Frontend Setup
1. Open a new terminal and navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install package dependencies:
   ```bash
   npm install
   ```
3. Start the Vite React development server:
   ```bash
   npm run dev
   ```
   *Frontend application will run at: `http://localhost:5173/`*

---

## 🧪 Running Backend Unit Tests

To run the unit tests verifying split remainder adjustments, percentage calculation, share ratios, flow simplification, and CSV dry-run scanning:
```bash
cd backend
python manage.py test expenses
```

---

## 🤖 AI Collaboration Details

* **AI Tool Used**: Antigravity (powered by Gemini 3.5 Flash)
* **Developer Role**: Engineer of Record. Directed the AI, designed the architecture, audited codebase correctness, corrected AI hallucinations (such as incorrect Django ForeignKey parameters, path issues, and missing date format rules), and verified split precision.
