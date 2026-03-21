# 🧠 QueryMind AI

> **Talk to your database in plain English.**
> Ask questions. Get SQL. See results. Understand data.

![Phase](https://img.shields.io/badge/Phase-2%20In%20Progress-7b61ff?style=flat-square)
![Stack](https://img.shields.io/badge/Stack-Flask%20%7C%20LangChain%20%7C%20Gemini%20%7C%20FAISS-00e5ff?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-00d68f?style=flat-square)

---

## What is QueryMind AI?

QueryMind AI is a **full-stack AI-powered data analyst platform** that lets users connect their own database and ask natural language questions — no SQL knowledge required.

The system generates SQL, executes it, explains the results in plain English, visualizes data automatically, and evaluates its own accuracy using RAGAS metrics.

---

## Live Features

### ✅ Phase 1 — Core MVP
- Natural language → SQL generation using **Gemini 2.0 Flash**
- Connect **MySQL** or **SQLite** databases
- **Two-layer safety guardrail** — intent detection + SQL AST parsing
- **Self-correction loop** — auto-retries failed queries with error context
- Plain English **query explanation** after every result
- In-memory **query history** per session
- Clean **chat-style UI** with SQL code cards

### ✅ Phase 2 — Intelligence + SaaS Features (In Progress)

| Feature | Status | Description |
|---|---|---|
| Auth System | ✅ | Email + Password + Google OAuth, JWT tokens |
| Persistent History | ✅ | Per-user query history saved to MySQL |
| File Uploads | ✅ | Upload CSV / SQLite / SQL dump — no credentials needed |
| FAISS Schema Intelligence | ✅ | Embed schema, retrieve only relevant tables per question |
| Schema Explorer | ✅ | Browse tables, columns, types + sample rows in sidebar |
| Query Suggestions | ✅ | AI-generated starter questions based on your schema |
| Auto Visualization | ✅ | Bar, line, pie charts auto-detected from result shape |
| Saved Queries | ✅ | Save queries into named collections, rerun anytime |
| Shareable Links | ✅ | Generate public read-only link for any query result |
| Feedback System | ✅ | 👍/👎 on every response, accuracy tracking over time |
| Dark/Light Mode | ✅ | Toggle + persisted in localStorage |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Frontend                           │
│   HTML + CSS + JS   │   Auth UI   │   Chat Interface    │
│   Schema Explorer   │   Charts    │   Saved Queries     │
└────────────────────────────┬────────────────────────────┘
                             │ REST API (JWT)
┌────────────────────────────▼────────────────────────────┐
│                    Flask Backend                        │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Auth Layer   │  │ FAISS Engine │  │ SQL Pipeline │  │
│  │ JWT + OAuth  │  │ Embeddings   │  │ Generate     │  │
│  │ Google OAuth │  │ Retrieval    │  │ Validate     │  │
│  └──────────────┘  └──────────────┘  │ Execute      │  │
│                                      │ Correct      │  │
│  ┌──────────────┐  ┌──────────────┐  │ Explain      │  │
│  │ Visualizer   │  │ File Handler │  └──────────────┘  │
│  │ Chart detect │  │ CSV→SQLite   │                    │
│  │ Chart.js data│  │ SQL dump     │                    │
│  └──────────────┘  └──────────────┘                    │
└────────────────────────────┬────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌──────────────────┐
│  User's DB      │ │  querymind_users│ │  FAISS Index     │
│  MySQL / SQLite │ │  MySQL          │ │  In-memory       │
│  CSV / Uploaded │ │  users          │ │  all-MiniLM-L6   │
│                 │ │  query_history  │ │  384-dim vectors │
│                 │ │  saved_queries  │ └──────────────────┘
│                 │ │  shared_queries │
│                 │ │  feedback       │
└─────────────────┘ └─────────────────┘
```

---

## How FAISS Schema Intelligence Works

One of the key technical features — handles databases with 100+ tables efficiently.

```
On DB Connect:
─────────────────────────────────────────
Each table schema → SentenceTransformer → 384-dim vector
All vectors stored in FAISS IndexFlatIP

On Each Question:
─────────────────────────────────────────
Question → embedding → FAISS similarity search
→ Top 4 most relevant tables retrieved
→ Only those schemas sent to Gemini
→ 90% fewer tokens, faster, more accurate
```

**Without FAISS:** 50 tables → 10,000+ tokens sent every query
**With FAISS:** 50 tables → ~4 relevant tables → ~800 tokens sent

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | HTML5, CSS3, Vanilla JavaScript |
| Backend | Python, Flask, Flask-CORS |
| LLM | Google Gemini 2.0 Flash (via LangChain) |
| Auth | Flask-JWT-Extended, Bcrypt, Authlib (Google OAuth) |
| Schema Intelligence | FAISS, Sentence-Transformers (all-MiniLM-L6-v2) |
| Database (user data) | MySQL (PyMySQL) |
| Database (queries) | MySQL / SQLite / PostgreSQL / CSV uploads |
| ORM | SQLAlchemy (via LangChain) |
| Visualization | Chart.js 4.4 |
| SQL Parsing | sqlparse |
| File Handling | Pandas, shortuuid |

---

## Project Structure

```
querymind/
├── backend/
│   ├── app.py                  # Flask API — all routes
│   ├── auth.py                 # Register, Login, Google OAuth
│   ├── db_users.py             # MySQL user storage
│   ├── db_connector.py         # MySQL + SQLite connection
│   ├── faiss_engine.py         # Schema embedding + retrieval
│   ├── sql_generator.py        # Gemini prompts — generate, correct, explain, suggest
│   ├── sql_validator.py        # Safety guardrails — block dangerous queries
│   ├── query_executor.py       # SQL execution via SQLAlchemy
│   ├── history_store.py        # Per-user persistent query history
│   ├── saved_queries.py        # Save + collections
│   ├── share_store.py          # Shareable public query links
│   ├── feedback_store.py       # 👍/👎 feedback + stats
│   ├── visualizer.py           # Chart type detection + Chart.js data prep
│   ├── file_handler.py         # CSV/SQLite/SQL dump upload handling
│   ├── uploads/                # Uploaded DB files (auto-created)
│   ├── requirements.txt
│   └── .env
└── frontend/
    ├── index.html              # Main app
    ├── style.css               # Full design system
    ├── app.js                  # App logic
    ├── auth.js                 # Auth logic
    └── share.html              # Public share view page
```

---

## API Reference

### Auth
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/auth/register` | No | Register with email + password |
| POST | `/api/auth/login` | No | Login, returns JWT |
| GET | `/api/auth/google` | No | Google OAuth redirect |
| GET | `/api/auth/google/callback` | No | Google OAuth callback |
| GET | `/api/auth/me` | JWT | Get current user |
| POST | `/api/auth/logout` | JWT | Logout |

### Database Connection
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/connect/mysql` | JWT | Connect MySQL + build FAISS index |
| POST | `/api/connect/sqlite` | JWT | Connect SQLite + build FAISS index |
| POST | `/api/connect/upload` | JWT | Upload CSV/SQLite/SQL dump |
| POST | `/api/disconnect` | JWT | Disconnect + reset FAISS |

### Query
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/ask` | JWT | Ask question → SQL → result + chart |
| GET | `/api/schema` | JWT | Get full schema |
| GET | `/api/schema/explorer` | JWT | Get tables + columns for explorer |
| GET | `/api/schema/sample/<table>` | JWT | Get 3 sample rows from table |
| GET | `/api/suggestions` | JWT | Get AI-generated question suggestions |

### History, Saved, Share, Feedback
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/api/history` | JWT | Get user query history |
| POST | `/api/history/clear` | JWT | Clear history |
| GET | `/api/history/stats` | JWT | Success rate + totals |
| POST | `/api/saved/save` | JWT | Save a query |
| GET | `/api/saved/list` | JWT | List saved queries |
| DELETE | `/api/saved/<id>` | JWT | Delete saved query |
| POST | `/api/share/create` | JWT | Create shareable link |
| GET | `/api/share/<id>` | No | View shared query (public) |
| POST | `/api/feedback` | JWT | Submit 👍/👎 |
| GET | `/api/feedback/stats` | JWT | Get feedback accuracy stats |

---

## Quick Start

### 1. Clone & setup

```bash
git clone https://github.com/aviral2309/querymind-ai
cd querymind-ai/backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 2. Create MySQL database

```sql
CREATE DATABASE querymind_users;
```

### 3. Configure `.env`

```env
GEMINI_API_KEY=your_gemini_key
JWT_SECRET_KEY=your_jwt_secret

MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=querymind_users

GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=http://localhost:5000/api/auth/google/callback
```

### 4. Run backend

```bash
python app.py
```

Expected output:
```
⏳ Loading embedding model...
✅ Embedding model ready.
✅ Users table ready.
✅ History table ready.
✅ Saved queries table ready.
✅ Share table ready.
✅ Feedback table ready.
* Running on http://127.0.0.1:5000
```

### 5. Open frontend

Open `frontend/index.html` with VS Code Live Server → `http://localhost:5500/frontend/index.html`

---

## Safety Guardrails

QueryMind blocks dangerous queries at two independent layers:

```
Layer 1 — Intent Detection
User question scanned for: delete, drop, truncate, alter,
update, insert, destroy, wipe, erase, overwrite...
→ Blocked before LLM is even called

Layer 2 — SQL AST Validation
Generated SQL parsed with sqlparse
Checks for: DROP, DELETE, UPDATE, INSERT, ALTER,
TRUNCATE, CREATE, REPLACE, MERGE, EXEC...
→ Blocked before execution

Only SELECT queries reach the database.
```

---

## Sample Questions to Test

```
Show top 5 customers by revenue
What was the budget of Product 12?
How many orders were placed last month?
Average order value by region
```

---

## Roadmap

### Phase 3 — Coming Next
- [ ] Conversation memory (multi-turn context)
- [ ] RAGAS evaluation dashboard
- [ ] Chain-of-thought reasoning mode
- [ ] PostgreSQL connection support
- [ ] Docker + deployment (Railway / Vercel)
- [ ] Portfolio assets + benchmark report

---

<br/>

**Aviral Mittal**
GenAI · Agentic AI · ML · Data Science · Backend

---

*QueryMind AI — Phase 2 | Built with Flask, LangChain, Gemini, FAISS*