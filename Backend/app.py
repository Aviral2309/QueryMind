import warnings
warnings.filterwarnings("ignore")

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
import traceback
import os
from dotenv import load_dotenv

load_dotenv()

from db_connector import connect_mysql, connect_sqlite, get_schema, is_connected, disconnect
from sql_generator import generate_sql, correct_sql, explain_sql
from sql_validator import validate_sql
from query_executor import execute_query
from history_store import add_entry, get_history, clear_history
from auth import auth_bp, init_oauth
from db_users import init_users_table

app = Flask(__name__)
CORS(app, supports_credentials=True)

app.config["JWT_SECRET_KEY"]          = os.getenv("JWT_SECRET_KEY", "dev-secret-change-this")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = False
app.config["SECRET_KEY"]              = os.getenv("JWT_SECRET_KEY", "dev-secret-change-this")

jwt = JWTManager(app)

app.register_blueprint(auth_bp)
init_oauth(app)
init_users_table()


# ─── Blocked intent keywords ───
BLOCKED_INTENTS = [
    "delete", "drop", "remove", "truncate", "wipe",
    "erase", "destroy", "alter", "update", "insert",
    "modify", "clear all", "reset", "overwrite"
]

def check_intent(question: str) -> bool:
    q = question.lower().strip()
    return any(word in q for word in BLOCKED_INTENTS)


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
        data   = request.get_json()
        result = connect_mysql(
            data.get("host", "localhost"),
            data.get("port", "3306"),
            data.get("username", "root"),
            data.get("password", ""),
            data.get("database", "")
        )
        schema = get_schema()
        return jsonify({
            **result,
            "schema_preview": schema[:500] + "..." if len(schema) > 500 else schema
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────
# Connect SQLite
# ─────────────────────────────────────────────
@app.route("/api/connect/sqlite", methods=["POST"])
@jwt_required()
def connect_sqlite_route():
    try:
        data     = request.get_json()
        filepath = data.get("filepath", "")
        if not filepath:
            return jsonify({"error": "Filepath is required"}), 400
        result = connect_sqlite(filepath)
        schema = get_schema()
        return jsonify({
            **result,
            "schema_preview": schema[:500] + "..." if len(schema) > 500 else schema
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────
# Disconnect
# ─────────────────────────────────────────────
@app.route("/api/disconnect", methods=["POST"])
@jwt_required()
def disconnect_route():
    disconnect()
    return jsonify({"status": "disconnected"})


# ─────────────────────────────────────────────
# Ask
# ─────────────────────────────────────────────
@app.route("/api/ask", methods=["POST"])
@jwt_required()
def ask():
    try:
        if not is_connected():
            return jsonify({"error": "No database connected."}), 400

        data     = request.get_json()
        question = data.get("question", "").strip()

        if not question:
            return jsonify({"error": "Question cannot be empty"}), 400

        if check_intent(question):
            return jsonify({
                "question": question,
                "error":    "⚠️ Destructive intent detected. Only data retrieval questions are allowed.",
                "blocked":  True,
                "success":  False
            }), 400

        schema        = get_schema()
        generated_sql = generate_sql(schema, question)
        validation    = validate_sql(generated_sql)

        if not validation["valid"]:
            add_entry(question, generated_sql, False, error=validation["reason"])
            return jsonify({
                "question": question,
                "sql":      generated_sql,
                "error":    validation["reason"],
                "blocked":  True
            }), 400

        clean_sql   = validation["cleaned_sql"]
        exec_result = execute_query(clean_sql)

        corrected = False
        if not exec_result["success"]:
            corrected_sql        = correct_sql(schema, question, clean_sql, exec_result["error"])
            correction_validation = validate_sql(corrected_sql)
            if correction_validation["valid"]:
                exec_result = execute_query(correction_validation["cleaned_sql"])
                if exec_result["success"]:
                    clean_sql = correction_validation["cleaned_sql"]
                    corrected = True

        explanation = ""
        if exec_result["success"]:
            try:
                explanation = explain_sql(clean_sql, question)
            except:
                explanation = "Could not generate explanation."

        add_entry(
            question=question,
            sql=clean_sql,
            success=exec_result["success"],
            row_count=exec_result.get("row_count", 0),
            error=exec_result.get("error")
        )

        if exec_result["success"]:
            return jsonify({
                "question":    question,
                "sql":         clean_sql,
                "explanation": explanation,
                "columns":     exec_result["columns"],
                "rows":        exec_result["rows"],
                "row_count":   exec_result["row_count"],
                "corrected":   corrected,
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
    return jsonify(get_history())


@app.route("/api/history/clear", methods=["POST"])
@jwt_required()
def clear():
    return jsonify(clear_history())


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