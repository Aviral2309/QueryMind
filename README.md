# 🧠 QueryMind AI — Intelligent Data Analyst Platform

QueryMind AI is a full-stack AI-powered data analytics platform that allows users to connect databases and perform data analysis using natural language. It goes beyond simple query generation by providing automated insights, anomaly detection, and dashboard creation — functioning like a real AI data analyst.

---

# 🚀 Features

## 🔹 Core Capabilities

* Natural Language → SQL generation using LLM (Gemini)
* FAISS-based schema retrieval for efficient context selection
* SQL validation and execution with safety guardrails
* Self-correcting query pipeline (retry on failure)
* Multi-database support:

  * MySQL
  * SQLite
  * CSV uploads (auto-converted)

---

## 🧠 Intelligence Layer (New)

### ✅ Insight Engine

* Generates business insights from query results
* Detects trends, top contributors, and summaries
* Produces human-readable explanations

### ⚠️ Anomaly Detection

* Uses statistical methods (Z-score)
* Automatically flags unusual values and spikes

### 📊 Data Profiling

* Column-level analysis on DB connect:

  * Missing values %
  * Unique counts
  * Mean, min, max, std
* Helps users understand data before querying

### 📈 Forecasting (Optional)

* Time-series prediction using simple models
* Supports trend-based future estimation

---

## 📊 Auto Dashboard Generation (🔥 Key Feature)

* Automatically creates dashboards when database is connected
* Detects:

  * Date columns
  * Numeric columns
  * Categorical columns
* Generates:

  * Line charts (time trends)
  * Bar charts (category analysis)
  * Pie charts (distribution)
* Displays KPIs and insights

---

## 💾 Data & User Features

* JWT Authentication + Google OAuth
* Persistent query history (per user)
* Session-based chat memory
* Saved queries & collections
* Shareable query links
* Saved database connections

---

## 📈 Visualization

* Automatic chart generation using Chart.js
* Interactive tables:

  * Sorting
  * Filtering
  * Export (CSV)

---

# 🏗️ Tech Stack

### Backend

* Python (Flask)
* SQLAlchemy
* PyMySQL
* FAISS (vector search)
* Sentence Transformers

### Frontend

* HTML, CSS, JavaScript
* Chart.js

### AI / LLM

* Google Gemini (via LangChain)

### Database

* MySQL (users, history, metadata)
* SQLite (uploaded datasets)

---

# ⚙️ System Architecture

```
User Query
    ↓
Query Classifier (optional)
    ↓
FAISS Schema Retrieval
    ↓
LLM → SQL Generation
    ↓
SQL Validator + Executor
    ↓
Result DataFrame
    ↓
Insight Engine + Anomaly Detection
    ↓
Visualization + Response
```

---

# 📂 Project Structure

```
querymind/
├── backend/
│   ├── app.py
│   ├── auth.py
│   ├── db_connector.py
│   ├── faiss_engine.py
│   ├── sql_generator.py
│   ├── sql_validator.py
│   ├── query_executor.py
│   ├── insight_engine.py          
│   ├── data_profiler.py           
│   ├── dashboard_generator.py     
│   ├── forecasting.py             
│   ├── history_store.py
│   ├── session_store.py
│   ├── saved_queries.py
│   ├── visualizer.py
│   └── uploads/
│
├── frontend/
│   ├── index.html
│   ├── app.js
│   ├── style.css
│   ├── dashboard_auto.html        
│   ├── dashboard_auto.js          
│   ├── dashboard.html
│   └── share.html
```

---

# 🔌 API Endpoints (Important)

### Core

* `POST /api/ask` → Ask natural language query
* `POST /api/connect/mysql` → Connect DB
* `POST /api/upload` → Upload CSV/SQLite

### New Features

* `GET /api/dashboard` → Auto-generated dashboard
* `GET /api/profile` → Data profiling

---

# ▶️ How It Works

1. User connects database or uploads CSV
2. System scans schema and builds FAISS index
3. Auto dashboard is generated instantly
4. User asks question in plain English
5. System:

   * generates SQL
   * executes query
   * analyzes results
6. Outputs:

   * table + charts
   * insights
   * anomaly alerts

---

# 💼 Use Cases

* Business analytics dashboards
* Data exploration without SQL knowledge
* Financial trend analysis
* Sales & customer insights
* Rapid prototyping for analytics teams

---

# 🏆 Key Highlights

* Combines **GenAI + Data Science + Backend Engineering**
* Reduces LLM token usage by ~90% using FAISS
* Provides **end-to-end data analysis pipeline**
* Works like a **mini ThoughtSpot / Power BI with AI**

---

# 🚀 Future Improvements

* Better forecasting models (ARIMA, Prophet)
* Advanced anomaly detection
* Role-based access control
* Cloud deployment (Docker + AWS/GCP)
* Real-time streaming data support

---

# 👨‍💻 Author

Aviral Mittal
Electrical Engineering | Data Science Enthusiast

---

# ⭐ Final Note

This project demonstrates the integration of:

* AI (LLMs)
* Data Science (statistics, analysis)
* Backend Engineering (APIs, DB systems)

👉 Making it a complete **AI Data Analyst System**
