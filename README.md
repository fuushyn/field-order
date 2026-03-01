# Field Order

Web app for distributor sales reps to create and submit orders on behalf of retailers during field visits.

**Stack**: React + Vite + Tailwind CSS | FastAPI + SQLite | JWT auth

## Quick Start

```bash
# Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python seed.py
uvicorn main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — login with `rep1` / `password`.

## Flow

Select retailer → Browse products → Add to cart → Review → Submit order → View in Order History

## Seed Data

- 1 sales rep, 3 retailers, 16 products across 5 categories
- Run `python seed.py` to reset the database

## API

Backend runs on http://localhost:8000 — docs at http://localhost:8000/docs
