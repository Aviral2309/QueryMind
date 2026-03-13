'''Main Flask app'''

from flask import Flask, request, jsonify
from flask_cors import CORS
import traceback

from db_connector import connect_mysql, connect_sqlite, get_schema, is_connected, disconnect
from sql_generator import generate_sql, correct_sql, explain_sql
from sql_validator import validate_sql
from query_executor import execute_query
from history_store import add_entry, get_history, clear_history

app = Flask(__name__)
CORS(app)  # Allow frontend to call backend

BLOCKED_INTENTS = [
    "delete", "drop", "remove", "truncate", "wipe",
    "erase", "destroy", "alter", "update", "insert",
    "modify", "clear all", "reset", "overwrite"
]

def check_intent(question: str) -> bool:
    """Returns True if question has destructive intent."""
    q = question.lower().strip()
    return any(word in q for word in BLOCKED_INTENTS)

# health check
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "running",
        "connected": is_connected()
    })


# Connect to my sql
@app.route("/api/connect/mysql", methods=["POST"])
def connect_mysql_route():
    try:
        data = request.get_json()
        host = data.get("host", "localhost")
        port = data.get("port", "3306")
        username = data.get("username", "root")
        password = data.get("password", "")
        database = data.get("database", "")

        if not database:
            return jsonify({"error": "Database name is required"}), 400

        result = connect_mysql(host, port, username, password, database)
        schema = get_schema()

        return jsonify({
            **result,
            "schema_preview": schema[:500] + "..." if len(schema) > 500 else schema
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Connect to SQLlite
@app.route("/api/connect/sqlite", methods=["POST"])
def connect_sqlite_route():
    try:
        data = request.get_json()
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


# Disconnect
@app.route("/api/disconnect", methods=["POST"])
def disconnect_route():
    disconnect()
    return jsonify({"status": "disconnected"})


# Ask Questions
@app.route("/api/ask", methods=["POST"])
def ask():
    try:
        if not is_connected():
            return jsonify({"error": "No database connected. Please connect first."}), 400

        data = request.get_json()
        question = data.get("question", "").strip()

        if not question:
            return jsonify({"error": "Question cannot be empty"}), 400

        
        if check_intent(question):
            return jsonify({
                "question": question,
                "error": "⚠️ Your question appears to have destructive intent. Only data retrieval questions are allowed.",
                "blocked": True,
                "success": False
            }), 400
        schema = get_schema()

        # Step 1 — Generate SQL
        generated_sql = generate_sql(schema, question)

        # Step 2 — Validate SQL (guardrails)
        validation = validate_sql(generated_sql)
        if not validation["valid"]:
            add_entry(question, generated_sql, False, error=validation["reason"])
            return jsonify({
                "question": question,
                "sql": generated_sql,
                "error": validation["reason"],
                "blocked": True
            }), 400

        clean_sql = validation["cleaned_sql"]

        # Step 3 — Execute query
        exec_result = execute_query(clean_sql)

        # Step 4 — Self-correction loop if error
        corrected = False
        if not exec_result["success"]:
            corrected_sql = correct_sql(schema, question, clean_sql, exec_result["error"])

            # Validate the corrected SQL too
            correction_validation = validate_sql(corrected_sql)
            if correction_validation["valid"]:
                exec_result = execute_query(correction_validation["cleaned_sql"])
                if exec_result["success"]:
                    clean_sql = correction_validation["cleaned_sql"]
                    corrected = True

        # Step 5 — Generate explanation
        explanation = ""
        if exec_result["success"]:
            try:
                explanation = explain_sql(clean_sql, question)
            except:
                explanation = "Could not generate explanation."

        # Step 6 — Store in history
        add_entry(
            question=question,
            sql=clean_sql,
            success=exec_result["success"],
            row_count=exec_result.get("row_count", 0),
            error=exec_result.get("error")
        )

        # Step 7 — Return response
        if exec_result["success"]:
            return jsonify({
                "question": question,
                "sql": clean_sql,
                "explanation": explanation,
                "columns": exec_result["columns"],
                "rows": exec_result["rows"],
                "row_count": exec_result["row_count"],
                "corrected": corrected,
                "success": True
            })
        else:
            return jsonify({
                "question": question,
                "sql": clean_sql,
                "error": exec_result["error"],
                "corrected_attempted": True,
                "success": False
            }), 500

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


#Query History
@app.route("/api/history", methods=["GET"])
def history():
    return jsonify(get_history())


@app.route("/api/history/clear", methods=["POST"])
def clear():
    return jsonify(clear_history())


#Get Schema
@app.route("/api/schema", methods=["GET"])
def schema():
    if not is_connected():
        return jsonify({"error": "Not connected"}), 400
    return jsonify({"schema": get_schema()})


if __name__ == "__main__":
    app.run(debug=True, port=5000)