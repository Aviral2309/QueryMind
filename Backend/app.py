import warnings
warnings.filterwarnings("ignore")

import time
import traceback
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager, jwt_required, get_jwt_identity)
from dotenv import load_dotenv

load_dotenv()

from db_connector         import (connect_mysql, connect_sqlite,
                                   connect_uploaded_db, connect_url,
                                   get_schema, get_table_names,
                                   get_engine, is_connected, disconnect)
from sql_generator        import (generate_sql, generate_sql_with_memory,
                                   correct_sql, explain_sql,
                                   suggest_questions, generate_story)
from sql_validator        import validate_sql
from query_executor       import execute_query
from history_store        import (init_history_table, add_entry,
                                   get_history, clear_history,
                                   get_stats, get_daily_stats)
from auth                 import auth_bp, init_oauth
from db_users             import init_users_table, get_user_by_id
from faiss_engine         import (build_schema_index,
                                   retrieve_relevant_schema,
                                   is_index_built, reset_index)
from file_handler         import (save_uploaded_file,
                                   csv_to_sqlite, sql_dump_to_sqlite)
from saved_queries        import (init_saved_queries_table, save_query,
                                   get_saved_queries, delete_saved_query)
from usage_tracker        import (init_usage_table, can_query,
                                   increment_usage, get_today_usage,
                                   get_usage_history, DAILY_LIMIT)
from session_store        import (init_sessions_table, create_session,
                                   update_session_title, add_message,
                                   get_session_messages,
                                   get_conversation_context,
                                   get_user_sessions, delete_session)
from db_saved_connections import (init_connections_table, save_connection,
                                   get_user_connections,
                                   get_connection_by_id,
                                   update_last_used, delete_connection)
from ragas_evaluator      import (init_ragas_table, store_ragas_score,
                                   get_ragas_summary, get_ragas_trend,
                                   get_low_scoring_queries)
from visualizer           import (detect_chart_type,
                                   prepare_chart_data, get_data_summary)
from insight_engine       import generate_insights, rows_to_dataframe
from data_profiler        import profile_database
from dashboard_generator  import generate_auto_dashboard
from forecasting          import forecast_series

app = Flask(__name__)
CORS(app, supports_credentials=True)

app.config["JWT_SECRET_KEY"]           = os.getenv(
    "JWT_SECRET_KEY", "dev-secret")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = False
app.config["SECRET_KEY"]               = os.getenv(
    "JWT_SECRET_KEY", "dev-secret")
app.config["MAX_CONTENT_LENGTH"]       = 50 * 1024 * 1024

jwt = JWTManager(app)
app.register_blueprint(auth_bp)
init_oauth(app)

# Init all DB tables
init_users_table()
init_history_table()
init_saved_queries_table()
init_usage_table()
init_sessions_table()
init_connections_table()
init_ragas_table()

BLOCKED_INTENTS = [
    "delete", "drop", "remove", "truncate", "wipe", "erase",
    "destroy", "alter", "update", "insert", "modify", "overwrite"
]


def check_intent(q):
    return any(w in q.lower() for w in BLOCKED_INTENTS)


def uid():
    return int(get_jwt_identity())


# ─────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "running", "connected": is_connected()
    })


# ─────────────────────────────────────────────
# Connect MySQL
# ─────────────────────────────────────────────
@app.route("/api/connect/mysql", methods=["POST"])
@jwt_required()
def connect_mysql_route():
    try:
        d      = request.get_json()
        result = connect_mysql(
            d.get("host", "localhost"),
            d.get("port", "3306"),
            d.get("username", "root"),
            d.get("password", ""),
            d.get("database", "")
        )
        schema = get_schema()
        n      = build_schema_index(schema)

        nickname = d.get("nickname", "").strip()
        if nickname:
            save_connection(
                uid(), nickname, "mysql",
                host=d.get("host"),
                port=d.get("port"),
                username=d.get("username"),
                password=d.get("password"),
                database_name=d.get("database")
            )

        return jsonify({**result, "tables_indexed": n})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────
# Connect SQLite
# ─────────────────────────────────────────────
@app.route("/api/connect/sqlite", methods=["POST"])
@jwt_required()
def connect_sqlite_route():
    try:
        d        = request.get_json()
        filepath = d.get("filepath", "")
        if not filepath:
            return jsonify({"error": "Filepath required"}), 400
        result = connect_sqlite(filepath)
        schema = get_schema()
        n      = build_schema_index(schema)
        return jsonify({**result, "tables_indexed": n})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────
# Connect via URL
# ─────────────────────────────────────────────
@app.route("/api/connect/url", methods=["POST"])
@jwt_required()
def connect_url_route():
    try:
        d      = request.get_json()
        db_url = d.get("url", "").strip()
        if not db_url:
            return jsonify({"error": "URL required"}), 400
        result = connect_url(db_url)
        schema = get_schema()
        n      = build_schema_index(schema)

        nickname = d.get("nickname", "").strip()
        if nickname:
            save_connection(
                uid(), nickname, "url", filepath=db_url)

        return jsonify({**result, "tables_indexed": n})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────
# Upload file (CSV / SQLite)
# ─────────────────────────────────────────────
@app.route("/api/connect/upload", methods=["POST"])
@jwt_required()
def connect_upload():
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files["file"]
        if not file or file.filename == "":
            return jsonify({"error": "No file selected"}), 400

        filepath, ext, orig_name = save_uploaded_file(file)

        if ext == ".csv":
            db_path, table_name = csv_to_sqlite(filepath)
            result = connect_uploaded_db(db_path)
            result["original_name"] = orig_name
            result["table_name"]    = table_name
            result["converted"]     = True
        elif ext in [".sqlite", ".db"]:
            result = connect_uploaded_db(filepath)
            result["original_name"] = orig_name
        elif ext == ".sql":
            db_path, errors = sql_dump_to_sqlite(filepath)
            result = connect_uploaded_db(db_path)
            result["original_name"] = orig_name
            result["parse_errors"]  = len(errors)
        else:
            return jsonify({
                "error": "Unsupported file. Use .csv, .sqlite, .db, or .sql"
            }), 400

        schema = get_schema()
        n      = build_schema_index(schema)
        return jsonify({**result, "tables_indexed": n})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────
# Reconnect saved connection
# ─────────────────────────────────────────────
@app.route("/api/connect/saved/<int:conn_id>", methods=["POST"])
@jwt_required()
def connect_saved(conn_id):
    try:
        saved = get_connection_by_id(conn_id, uid())
        if not saved:
            return jsonify({"error": "Connection not found"}), 404

        if saved["db_type"] == "mysql":
            result = connect_mysql(
                saved["host"], saved["port"],
                saved["username"], saved["password"],
                saved["database_name"]
            )
        elif saved["db_type"] in ["sqlite", "sqlite_upload"]:
            result = connect_sqlite(saved["filepath"])
        elif saved["db_type"] == "url":
            result = connect_url(saved["filepath"])
        else:
            return jsonify({"error": "Unknown DB type"}), 400

        schema = get_schema()
        n      = build_schema_index(schema)
        update_last_used(conn_id)
        return jsonify({**result, "tables_indexed": n})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────
# Disconnect
# ─────────────────────────────────────────────
@app.route("/api/disconnect", methods=["POST"])
@jwt_required()
def disconnect_route():
    disconnect()
    reset_index()
    return jsonify({"status": "disconnected"})


# ─────────────────────────────────────────────
# Saved connections
# ─────────────────────────────────────────────
@app.route("/api/connections", methods=["GET"])
@jwt_required()
def list_connections():
    return jsonify(get_user_connections(uid()))


@app.route("/api/connections/<int:conn_id>", methods=["DELETE"])
@jwt_required()
def del_connection(conn_id):
    delete_connection(conn_id, uid())
    return jsonify({"deleted": True})


# ─────────────────────────────────────────────
# Sessions
# ─────────────────────────────────────────────
@app.route("/api/sessions", methods=["GET"])
@jwt_required()
def list_sessions():
    sessions = get_user_sessions(uid())
    for s in sessions:
        if s.get("created_at"):
            s["created_at"] = str(s["created_at"])
        if s.get("updated_at"):
            s["updated_at"] = str(s["updated_at"])
    return jsonify(sessions)


@app.route("/api/sessions/new", methods=["POST"])
@jwt_required()
def new_session():
    d          = request.get_json() or {}
    session_id = create_session(
        uid(),
        db_type=d.get("db_type"),
        db_name=d.get("db_name")
    )
    return jsonify({"session_id": session_id})


@app.route("/api/sessions/<session_id>/messages", methods=["GET"])
@jwt_required()
def session_messages(session_id):
    msgs = get_session_messages(session_id, limit=50)
    for m in msgs:
        if m.get("created_at"):
            m["created_at"] = str(m["created_at"])
    return jsonify(msgs)


@app.route("/api/sessions/<session_id>", methods=["DELETE"])
@jwt_required()
def del_session(session_id):
    delete_session(session_id, uid())
    return jsonify({"deleted": True})


# ─────────────────────────────────────────────
# Schema explorer
# ─────────────────────────────────────────────
@app.route("/api/schema/explorer", methods=["GET"])
@jwt_required()
def schema_explorer():
    if not is_connected():
        return jsonify({"error": "Not connected"}), 400
    try:
        from sqlalchemy import inspect
        inspector = inspect(get_engine())
        tables    = []
        for tname in inspector.get_table_names():
            cols = []
            for col in inspector.get_columns(tname):
                cols.append({
                    "name": col["name"],
                    "type": str(col["type"])
                })
            tables.append({"name": tname, "columns": cols})
        return jsonify({"tables": tables})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/schema/sample/<table_name>", methods=["GET"])
@jwt_required()
def schema_sample(table_name):
    if not is_connected():
        return jsonify({"error": "Not connected"}), 400
    result = execute_query(f"SELECT * FROM `{table_name}` LIMIT 5")
    if result["success"]:
        return jsonify({
            "columns": result["columns"],
            "rows":    result["rows"]
        })
    return jsonify({"error": result["error"]}), 500


# ─────────────────────────────────────────────
# Suggestions
# ─────────────────────────────────────────────
@app.route("/api/suggestions", methods=["GET"])
@jwt_required()
def suggestions():
    if not is_connected():
        return jsonify({"error": "Not connected"}), 400
    try:
        schema    = get_schema()
        questions = suggest_questions(schema)
        return jsonify({"suggestions": questions})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────
# Auto Dashboard
# ─────────────────────────────────────────────
@app.route("/api/dashboard", methods=["GET"])
@jwt_required()
def auto_dashboard():
    if not is_connected():
        return jsonify({"error": "Not connected"}), 400
    try:
        engine    = get_engine()
        dashboard = generate_auto_dashboard(engine)
        return jsonify(dashboard)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────
# Data profiling
# ─────────────────────────────────────────────
@app.route("/api/profile/db", methods=["GET"])
@jwt_required()
def db_profile():
    if not is_connected():
        return jsonify({"error": "Not connected"}), 400
    try:
        engine  = get_engine()
        profile = profile_database(engine)
        return jsonify(profile)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────
# ASK — main endpoint
# ─────────────────────────────────────────────
@app.route("/api/ask", methods=["POST"])
@jwt_required()
def ask():
    start_ms = int(time.time() * 1000)
    try:
        if not is_connected():
            return jsonify({"error": "No database connected."}), 400

        d          = request.get_json()
        question   = d.get("question", "").strip()
        session_id = d.get("session_id")

        if not question:
            return jsonify({"error": "Question cannot be empty"}), 400

        # Usage check
        allowed, used, limit = can_query(uid())
        if not allowed:
            return jsonify({
                "error":   f"Daily limit of {limit} queries reached.",
                "limited": True
            }), 429

        if check_intent(question):
            return jsonify({
                "question": question,
                "error":    "Destructive queries are not allowed.",
                "blocked":  True,
                "success":  False
            }), 400

        # Get schema via FAISS or full
        if is_index_built():
            schema = retrieve_relevant_schema(question, top_k=4)
            if not schema:
                schema = get_schema()
        else:
            schema = get_schema()

        # Generate SQL (with memory if session exists)
        if session_id:
            context = get_conversation_context(session_id, last_n=5)
            generated_sql = (
                generate_sql_with_memory(schema, question, context)
                if context else generate_sql(schema, question)
            )
        else:
            generated_sql = generate_sql(schema, question)

        # Validate
        validation = validate_sql(generated_sql)
        if not validation["valid"]:
            add_entry(uid(), question, generated_sql, False,
                      error=validation["reason"],
                      session_id=session_id)
            return jsonify({
                "question": question,
                "sql":      generated_sql,
                "error":    validation["reason"],
                "blocked":  True
            }), 400

        clean_sql   = validation["cleaned_sql"]
        exec_result = execute_query(clean_sql)

        # Self-correction
        corrected = False
        if not exec_result["success"]:
            corrected_sql = correct_sql(
                schema, question, clean_sql, exec_result["error"])
            cv = validate_sql(corrected_sql)
            if cv["valid"]:
                exec_result = execute_query(cv["cleaned_sql"])
                if exec_result["success"]:
                    clean_sql = cv["cleaned_sql"]
                    corrected = True

        explanation  = ""
        chart_data   = {}
        data_summary = {}
        insights     = []
        anomalies    = []
        forecast     = {}

        if exec_result["success"]:
            try:
                explanation = explain_sql(
                    clean_sql, question,
                    exec_result.get("row_count", 0))
            except Exception:
                explanation = ""

            # Chart
            chart_type = detect_chart_type(
                exec_result["columns"], exec_result["rows"])
            if chart_type != "none":
                chart_data = prepare_chart_data(
                    exec_result["columns"],
                    exec_result["rows"],
                    chart_type
                )

            # Data summary
            data_summary = get_data_summary(
                exec_result["columns"], exec_result["rows"])

            # Insight engine + anomaly detection
            try:
                df = rows_to_dataframe(
                    exec_result["columns"], exec_result["rows"])
                result_insights = generate_insights(df, question)
                insights  = result_insights.get("insights", [])
                anomalies = result_insights.get("anomalies", [])
            except Exception:
                pass

            # Forecasting
            try:
                forecast = forecast_series(
                    exec_result["columns"], exec_result["rows"])
            except Exception:
                pass

        response_ms = int(time.time() * 1000) - start_ms

        # Store history
        add_entry(
            uid(), question, clean_sql,
            exec_result["success"],
            exec_result.get("row_count", 0),
            exec_result.get("error"),
            session_id=session_id,
            response_ms=response_ms
        )

        # Increment usage
        increment_usage(uid())

        # Store RAGAS silently
        if exec_result["success"]:
            try:
                store_ragas_score(
                    uid(), session_id, question, clean_sql,
                    explanation, exec_result["success"],
                    exec_result.get("row_count", 0))
            except Exception:
                pass

        # Save to session memory
        if session_id and exec_result["success"]:
            add_message(session_id, "user", question)
            add_message(
                session_id, "assistant", explanation,
                sql_query=clean_sql,
                columns=exec_result["columns"],
                rows=exec_result["rows"],
                chart_data=chart_data,
                row_count=exec_result.get("row_count", 0),
                success=True
            )
            update_session_title(session_id, question[:60])

        if exec_result["success"]:
            return jsonify({
                "question":     question,
                "sql":          clean_sql,
                "explanation":  explanation,
                "columns":      exec_result["columns"],
                "rows":         exec_result["rows"],
                "row_count":    exec_result["row_count"],
                "corrected":    corrected,
                "chart_data":   chart_data,
                "data_summary": data_summary,
                "insights":     insights,
                "anomalies":    anomalies,
                "forecast":     forecast,
                "response_ms":  response_ms,
                "success":      True
            })
        else:
            return jsonify({
                "question":            question,
                "sql":                 clean_sql,
                "error":               exec_result["error"],
                "corrected_attempted": True,
                "success":             False
            }), 500

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────
# History
# ─────────────────────────────────────────────
@app.route("/api/history", methods=["GET"])
@jwt_required()
def history():
    return jsonify(get_history(uid()))


@app.route("/api/history/clear", methods=["POST"])
@jwt_required()
def clear_hist():
    return jsonify(clear_history(uid()))


@app.route("/api/history/stats", methods=["GET"])
@jwt_required()
def history_stats():
    return jsonify(get_stats(uid()))


# ─────────────────────────────────────────────
# Usage
# ─────────────────────────────────────────────
@app.route("/api/usage", methods=["GET"])
@jwt_required()
def usage():
    used    = get_today_usage(uid())
    history = get_usage_history(uid(), days=30)
    for h in history:
        h["usage_date"] = str(h["usage_date"])
    return jsonify({
        "today_used":  used,
        "daily_limit": DAILY_LIMIT,
        "remaining":   max(0, DAILY_LIMIT - used),
        "history":     history
    })


# ─────────────────────────────────────────────
# Profile
# ─────────────────────────────────────────────
@app.route("/api/profile", methods=["GET"])
@jwt_required()
def profile():
    user  = get_user_by_id(uid())
    stats = get_stats(uid())
    used  = get_today_usage(uid())
    if user:
        user["created_at"] = str(user["created_at"])
        user["last_login"] = str(user["last_login"])
        user.pop("password", None)
    return jsonify({
        "user":        user,
        "stats":       stats,
        "today_usage": used,
        "daily_limit": DAILY_LIMIT
    })


# ─────────────────────────────────────────────
# RAGAS (background, not shown in main UI)
# ─────────────────────────────────────────────
@app.route("/api/analytics/summary", methods=["GET"])
@jwt_required()
def analytics_summary():
    stats = get_stats(uid())
    ragas = get_ragas_summary(uid())
    daily = get_daily_stats(uid(), days=14)
    return jsonify({
        "query_stats": stats,
        "ragas":       ragas,
        "daily":       daily
    })


@app.route("/api/analytics/trend", methods=["GET"])
@jwt_required()
def analytics_trend():
    trend = get_ragas_trend(uid(), 14)
    for t in trend:
        t["date"] = str(t["date"])
    return jsonify(trend)


@app.route("/api/analytics/low", methods=["GET"])
@jwt_required()
def analytics_low():
    rows = get_low_scoring_queries(uid())
    for r in rows:
        r["date"] = str(r.get("date", ""))
    return jsonify(rows)


# ─────────────────────────────────────────────
# Saved queries
# ─────────────────────────────────────────────
@app.route("/api/saved/save", methods=["POST"])
@jwt_required()
def save_q():
    d = request.get_json()
    return jsonify(save_query(
        uid(),
        d.get("name", "Untitled"),
        d.get("question", ""),
        d.get("sql", ""),
        d.get("collection", "General")
    ))


@app.route("/api/saved/list", methods=["GET"])
@jwt_required()
def list_saved():
    return jsonify(get_saved_queries(uid()))


@app.route("/api/saved/<int:query_id>", methods=["DELETE"])
@jwt_required()
def del_saved(query_id):
    return jsonify(delete_saved_query(query_id, uid()))


# ─────────────────────────────────────────────
# Schema
# ─────────────────────────────────────────────
@app.route("/api/schema", methods=["GET"])
@jwt_required()
def schema():
    if not is_connected():
        return jsonify({"error": "Not connected"}), 400
    return jsonify({"schema": get_schema()})


if __name__ == "__main__":
    app.run(debug=True, port=5000)