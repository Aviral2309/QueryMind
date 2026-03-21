import warnings
warnings.filterwarnings("ignore")

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
import traceback, os, json
from dotenv import load_dotenv

load_dotenv()

from db_connector    import (connect_mysql, connect_sqlite, connect_uploaded_db,
                              get_schema, get_table_names, is_connected, disconnect)
from sql_generator   import generate_sql, correct_sql, explain_sql, suggest_questions, detect_chart_type
from sql_validator   import validate_sql
from query_executor  import execute_query
from history_store   import init_history_table, add_entry, get_history, clear_history, get_stats
from auth            import auth_bp, init_oauth
from db_users        import init_users_table
from faiss_engine    import build_schema_index, retrieve_relevant_schema, is_index_built, reset_index
from file_handler    import save_uploaded_file, csv_to_sqlite, sql_dump_to_sqlite
from saved_queries   import (init_saved_queries_table, save_query,
                              get_saved_queries, delete_saved_query, get_collections)
from share_store     import init_share_table, create_share, get_share
from feedback_store  import init_feedback_table, add_feedback, get_feedback_stats, get_recent_feedback
from visualizer      import detect_chart_type as rule_detect_chart, prepare_chart_data

app = Flask(__name__)
CORS(app, supports_credentials=True)

app.config["JWT_SECRET_KEY"]           = os.getenv("JWT_SECRET_KEY", "dev-secret")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = False
app.config["SECRET_KEY"]               = os.getenv("JWT_SECRET_KEY", "dev-secret")
app.config["MAX_CONTENT_LENGTH"]       = 50 * 1024 * 1024  # 50MB upload limit

jwt = JWTManager(app)
app.register_blueprint(auth_bp)
init_oauth(app)

# Init all DB tables
init_users_table()
init_history_table()
init_saved_queries_table()
init_share_table()
init_feedback_table()

BLOCKED_INTENTS = [
    "delete", "drop", "remove", "truncate", "wipe", "erase",
    "destroy", "alter", "update", "insert", "modify", "overwrite"
]

def check_intent(q): return any(w in q.lower() for w in BLOCKED_INTENTS)
def uid(): return int(get_jwt_identity())


# ─────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "running", "connected": is_connected()})


# ─────────────────────────────────────────────
# Connect MySQL
# ─────────────────────────────────────────────
@app.route("/api/connect/mysql", methods=["POST"])
@jwt_required()
def connect_mysql_route():
    try:
        d = request.get_json()
        result = connect_mysql(
            d.get("host", "localhost"), d.get("port", "3306"),
            d.get("username", "root"), d.get("password", ""),
            d.get("database", "")
        )
        schema = get_schema()
        n = build_schema_index(schema)
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
# Upload file (CSV / SQLite / SQL dump)
# ─────────────────────────────────────────────
@app.route("/api/connect/upload", methods=["POST"])
@jwt_required()
def connect_upload():
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        file             = request.files["file"]
        filepath, ext, original_name = save_uploaded_file(file)

        if ext == ".csv":
            db_path, table_name = csv_to_sqlite(filepath)
            result = connect_uploaded_db(db_path)
            result["table_name"]    = table_name
            result["original_name"] = original_name
            result["converted"]     = True

        elif ext in [".sqlite", ".db"]:
            result = connect_uploaded_db(filepath)
            result["original_name"] = original_name

        elif ext == ".sql":
            db_path, errors = sql_dump_to_sqlite(filepath)
            result = connect_uploaded_db(db_path)
            result["original_name"] = original_name
            result["parse_errors"]  = len(errors)

        else:
            return jsonify({"error": "Unsupported file type. Use .csv, .sqlite, .db, or .sql"}), 400

        schema = get_schema()
        n      = build_schema_index(schema)
        return jsonify({**result, "tables_indexed": n})

    except Exception as e:
        traceback.print_exc()
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
# Schema explorer
# ─────────────────────────────────────────────
@app.route("/api/schema/explorer", methods=["GET"])
@jwt_required()
def schema_explorer():
    if not is_connected():
        return jsonify({"error": "Not connected"}), 400
    try:
        from db_connector import get_db
        from sqlalchemy import text, inspect
        db       = get_db()
        inspector = inspect(db._engine)
        tables   = []
        for table_name in inspector.get_table_names():
            columns = []
            for col in inspector.get_columns(table_name):
                columns.append({
                    "name": col["name"],
                    "type": str(col["type"])
                })
            tables.append({"name": table_name, "columns": columns})
        return jsonify({"tables": tables})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/schema/sample/<table_name>", methods=["GET"])
@jwt_required()
def schema_sample(table_name):
    if not is_connected():
        return jsonify({"error": "Not connected"}), 400
    try:
        result = execute_query(f"SELECT * FROM `{table_name}` LIMIT 3")
        if result["success"]:
            return jsonify({"columns": result["columns"], "rows": result["rows"]})
        return jsonify({"error": result["error"]}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────
# Query suggestions
# ─────────────────────────────────────────────
@app.route("/api/suggestions", methods=["GET"])
@jwt_required()
def suggestions():
    if not is_connected():
        return jsonify({"error": "Not connected"}), 400
    try:
        schema      = get_schema()
        questions   = suggest_questions(schema)
        return jsonify({"suggestions": questions})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────
# Ask — main endpoint
# ─────────────────────────────────────────────
@app.route("/api/ask", methods=["POST"])
@jwt_required()
def ask():
    try:
        if not is_connected():
            return jsonify({"error": "No database connected."}), 400

        d        = request.get_json()
        question = d.get("question", "").strip()
        if not question:
            return jsonify({"error": "Question cannot be empty"}), 400

        if check_intent(question):
            return jsonify({
                "question": question,
                "error":    "⚠️ Destructive intent detected. Only SELECT queries allowed.",
                "blocked":  True, "success": False
            }), 400

        # Use FAISS if available else full schema
        if is_index_built():
            schema = retrieve_relevant_schema(question, top_k=4)
            if not schema:
                schema = get_schema()
        else:
            schema = get_schema()

        generated_sql = generate_sql(schema, question)
        validation    = validate_sql(generated_sql)

        if not validation["valid"]:
            add_entry(uid(), question, generated_sql, False, error=validation["reason"])
            return jsonify({
                "question": question, "sql": generated_sql,
                "error": validation["reason"], "blocked": True
            }), 400

        clean_sql   = validation["cleaned_sql"]
        exec_result = execute_query(clean_sql)

        corrected = False
        if not exec_result["success"]:
            corrected_sql = correct_sql(schema, question, clean_sql, exec_result["error"])
            cv = validate_sql(corrected_sql)
            if cv["valid"]:
                exec_result = execute_query(cv["cleaned_sql"])
                if exec_result["success"]:
                    clean_sql = cv["cleaned_sql"]
                    corrected = True

        explanation = ""
        chart_data  = {}

        if exec_result["success"]:
            try:
                explanation = explain_sql(clean_sql, question)
            except:
                explanation = ""

            # Auto visualization
            chart_type = rule_detect_chart(exec_result["columns"], exec_result["rows"])
            if chart_type != "none":
                chart_data = prepare_chart_data(
                    exec_result["columns"], exec_result["rows"], chart_type
                )

        add_entry(uid(), question, clean_sql,
                  exec_result["success"],
                  exec_result.get("row_count", 0),
                  exec_result.get("error"))

        if exec_result["success"]:
            return jsonify({
                "question":    question,
                "sql":         clean_sql,
                "explanation": explanation,
                "columns":     exec_result["columns"],
                "rows":        exec_result["rows"],
                "row_count":   exec_result["row_count"],
                "corrected":   corrected,
                "chart_data":  chart_data,
                "success":     True
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
def clear():
    return jsonify(clear_history(uid()))


@app.route("/api/history/stats", methods=["GET"])
@jwt_required()
def history_stats():
    return jsonify(get_stats(uid()))


# ─────────────────────────────────────────────
# Saved queries
# ─────────────────────────────────────────────
@app.route("/api/saved/save", methods=["POST"])
@jwt_required()
def save_query_route():
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
def delete_saved(query_id):
    return jsonify(delete_saved_query(query_id, uid()))


@app.route("/api/saved/collections", methods=["GET"])
@jwt_required()
def collections():
    return jsonify(get_collections(uid()))


# ─────────────────────────────────────────────
# Share
# ─────────────────────────────────────────────
@app.route("/api/share/create", methods=["POST"])
@jwt_required()
def share_create():
    d        = request.get_json()
    share_id = create_share(
        uid(),
        d.get("question", ""),
        d.get("sql", ""),
        d.get("columns", []),
        d.get("rows", []),
        d.get("row_count", 0)
    )
    return jsonify({
        "share_id":  share_id,
        "share_url": f"http://localhost:5500/frontend/share.html?id={share_id}"
    })


@app.route("/api/share/<share_id>", methods=["GET"])
def share_get(share_id):
    data = get_share(share_id)
    if not data:
        return jsonify({"error": "Share not found"}), 404
    return jsonify(data)


# ─────────────────────────────────────────────
# Feedback
# ─────────────────────────────────────────────
@app.route("/api/feedback", methods=["POST"])
@jwt_required()
def feedback():
    d = request.get_json()
    return jsonify(add_feedback(
        uid(),
        d.get("question", ""),
        d.get("sql", ""),
        d.get("rating", 1)
    ))


@app.route("/api/feedback/stats", methods=["GET"])
@jwt_required()
def feedback_stats():
    return jsonify(get_feedback_stats(uid()))


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