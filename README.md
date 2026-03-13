# 🧠 QueryMind AI — Phase 1

> Ask questions about your database in plain English. Get SQL, results, and explanations instantly.

---

## What it does

- Connect to **MySQL** or **SQLite** database
- Type a question in natural language
- AI generates SQL, executes it, and returns results
- Blocks destructive queries (DROP, DELETE, UPDATE, etc.)
- Auto-corrects failed SQL queries
- Explains every query in plain English
- Tracks query history per session

---

## Tech Stack

| Layer | Tech |
|---|---|
| Frontend | Plain HTML, CSS, JavaScript |
| Backend | Flask, Flask-CORS |
| LLM | Gemini 2.0 Flash (via LangChain) |
| Database | MySQL / SQLite (via SQLAlchemy) |
| Validation | sqlparse |

---

## Project Structure

```
querymind/
├── backend/
│   ├── app.py              # Flask API + all routes
│   ├── db_connector.py     # MySQL & SQLite connection
│   ├── sql_generator.py    # LLM prompt + SQL generation
│   ├── sql_validator.py    # Guardrails — blocks dangerous queries
│   ├── query_executor.py   # Runs SQL, returns results
│   ├── history_store.py    # In-memory query history
│   ├── requirements.txt
│   └── .env                # GEMINI_API_KEY
└── frontend/
    ├── index.html
    ├── style.css
    └── app.js
```

---

## Quick Start

### 1. Install dependencies
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Set API key
```env
# backend/.env
GEMINI_API_KEY=your_key_here
```

### 3. Run backend
```bash
python app.py
```

### 4. Open frontend
Open `frontend/index.html` in your browser — no server needed.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/connect/mysql` | Connect to MySQL |
| POST | `/api/connect/sqlite` | Connect to SQLite |
| POST | `/api/ask` | Ask a natural language question |
| GET | `/api/history` | Get query history |
| POST | `/api/history/clear` | Clear history |
| GET | `/api/schema` | View DB schema |
| GET | `/api/health` | Health check |

---

## Safety Guardrails

Blocks all non-SELECT queries at two levels:

- **Intent detection** — catches destructive keywords in the question itself
- **SQL validation** — parses generated SQL and blocks any dangerous statements

---

## Sample Questions

```
What was the budget of Product 12?
Show top 5 customers by revenue
How many orders were placed in January?
What is the average order value by region?
List all products in the Electronics category
```

---

## Phases

- ✅ **Phase 1** — Core MVP (this)
- 🔜 **Phase 2** — FAISS schema intelligence, file uploads, multi-DB, visualizations
- 🔜 **Phase 3** — Conversation memory, RAGAS evaluation, deployment

---

<br/>

**Aviral Mittal**
GenAI · Agentic AI · ML · Data Science · Backend
