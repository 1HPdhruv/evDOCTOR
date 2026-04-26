# evDOCTOR — AI-Powered EV Fault Diagnosis

A full-stack web application that diagnoses Electric Vehicle faults using an ensemble ML model. Users describe symptoms in plain English and receive instant, accurate diagnoses with confidence scores and step-by-step troubleshooting guides.

## Architecture

| Layer | Tech | Hosting |
|-------|------|---------|
| Frontend | React + Vite | Netlify |
| Backend | FastAPI (Python) | Render |
| Database | SQLite (SQLAlchemy ORM) | Bundled with backend |
| ML Model | Scikit-Learn Ensemble (LR + SGD + NB) | Trained at startup |

## Features

- **Ensemble ML Model** — 3 classifiers (Logistic Regression, SGD, Naive Bayes) with weighted averaging
- **Wrong Input Detection** — Keyword validation + confidence threshold rejects gibberish/unrelated text
- **Temperature-Scaled Confidence** — Realistic, calibrated confidence scores
- **127+ Fault Codes** across 16 EV subsystems
- **Feedback System** — Users can rate diagnosis accuracy
- **Search History** — Recent diagnoses displayed in a table
- **Premium Dark UI** — Glassmorphism, animations, responsive design

## Project Structure

```
evDOCTOR/
├── backend/
│   ├── main.py          # FastAPI app & API endpoints
│   ├── database.py      # SQLAlchemy engine & session setup
│   ├── models.py        # ORM models (FaultCode, SearchHistory, Feedback)
│   ├── schemas.py       # Pydantic request/response validation
│   ├── ml_engine.py     # Ensemble ML engine with OOD detection
│   ├── init_db.py       # CSV → SQLite database seeder
│   └── requirements.txt # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── App.jsx      # Main React component
│   │   ├── App.css      # Premium styling
│   │   └── index.css    # Base styles
│   ├── netlify.toml     # Netlify deployment config
│   └── .env             # API URL environment variable
├── EV_DTC_Dataset.csv   # Master fault code dataset
├── Procfile             # Render deployment config
└── README.md
```

## Run Locally

### Backend
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python init_db.py
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`, Backend at `http://localhost:8000`.

## Deploy

### Backend → Render
1. Create a **Web Service** on Render
2. Set **Root Directory** to `backend`
3. Set **Build Command**: `pip install -r requirements.txt`
4. Set **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Set env var `FRONTEND_URL` to your Netlify URL

### Frontend → Netlify
1. Connect your GitHub repo to Netlify
2. Set **Base Directory** to `frontend`
3. Set **Build Command**: `npm run build`
4. Set **Publish Directory**: `frontend/dist`
5. Set env var `VITE_API_URL` to `https://your-render-backend.onrender.com/api`

## DBMS Concepts Used

The database layer (`models.py`, `database.py`) demonstrates:
- Primary Keys, Foreign Keys, Unique Constraints
- CHECK Constraints, NOT NULL, Default Values
- Indexes (single + composite), Relationships (1:N)
- Cascade Delete, ON DELETE SET NULL
- Session management, Connection pooling
- Foreign key enforcement in SQLite via PRAGMA

## Made by

[Dhruv](https://github.com/1HPdhruv)
