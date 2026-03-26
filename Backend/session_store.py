import pymysql
import pymysql.cursors
import os
import json
import shortuuid
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


def get_conn():
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", 3306)),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DATABASE", "querymind_users"),
        cursorclass=pymysql.cursors.DictCursor
    )


def init_sessions_table():
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id          INT AUTO_INCREMENT PRIMARY KEY,
                    session_id  VARCHAR(20) NOT NULL UNIQUE,
                    user_id     INT NOT NULL,
                    title       VARCHAR(255) DEFAULT 'New Chat',
                    db_type     VARCHAR(50),
                    db_name     VARCHAR(255),
                    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
                        ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                        ON DELETE CASCADE
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id          INT AUTO_INCREMENT PRIMARY KEY,
                    session_id  VARCHAR(20) NOT NULL,
                    role        VARCHAR(10) NOT NULL,
                    content     TEXT NOT NULL,
                    sql_query   TEXT,
                    columns_json TEXT,
                    rows_json   LONGTEXT,
                    chart_data  LONGTEXT,
                    row_count   INT DEFAULT 0,
                    success     BOOLEAN DEFAULT TRUE,
                    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id)
                        REFERENCES chat_sessions(session_id)
                        ON DELETE CASCADE
                );
            """)
        conn.commit()
        print("✅ Sessions tables ready.")
    finally:
        conn.close()


def create_session(user_id, db_type=None, db_name=None):
    conn = get_conn()
    session_id = shortuuid.uuid()[:12]
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO chat_sessions
                    (session_id, user_id, db_type, db_name)
                VALUES (%s, %s, %s, %s)
            """, (session_id, user_id, db_type, db_name))
        conn.commit()
        return session_id
    finally:
        conn.close()


def update_session_title(session_id, title):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE chat_sessions SET title = %s
                WHERE session_id = %s
            """, (title[:80], session_id))
        conn.commit()
    finally:
        conn.close()


def add_message(session_id, role, content, sql_query=None,
                columns=None, rows=None, chart_data=None,
                row_count=0, success=True):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO chat_messages
                    (session_id, role, content, sql_query,
                     columns_json, rows_json, chart_data,
                     row_count, success)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                session_id, role, content, sql_query,
                json.dumps(columns) if columns else None,
                json.dumps(rows)    if rows    else None,
                json.dumps(chart_data) if chart_data else None,
                row_count, success
            ))
        conn.commit()
    finally:
        conn.close()


def get_session_messages(session_id, limit=10):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT role, content, sql_query,
                       columns_json, rows_json, chart_data,
                       row_count, success, created_at
                FROM chat_messages
                WHERE session_id = %s
                ORDER BY created_at DESC
                LIMIT %s
            """, (session_id, limit))
            rows = cursor.fetchall()
            # Parse JSON fields
            for row in rows:
                row["columns"]    = json.loads(row["columns_json"])    if row["columns_json"]  else []
                row["rows"]       = json.loads(row["rows_json"])       if row["rows_json"]     else []
                row["chart_data"] = json.loads(row["chart_data"])      if row["chart_data"]    else {}
            return list(reversed(rows))
    finally:
        conn.close()


def get_conversation_context(session_id, last_n=5):
    """Returns last N messages as LangChain-compatible format."""
    messages = get_session_messages(session_id, limit=last_n * 2)
    context  = []
    for msg in messages[-last_n:]:
        context.append({
            "role":    msg["role"],
            "content": msg["content"]
        })
    return context


def get_user_sessions(user_id):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT s.session_id, s.title, s.db_type, s.db_name,
                       s.created_at, s.updated_at,
                       COUNT(m.id) as message_count
                FROM chat_sessions s
                LEFT JOIN chat_messages m
                    ON s.session_id = m.session_id
                WHERE s.user_id = %s
                GROUP BY s.session_id
                ORDER BY s.updated_at DESC
                LIMIT 30
            """, (user_id,))
            return cursor.fetchall()
    finally:
        conn.close()


def delete_session(session_id, user_id):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                DELETE FROM chat_sessions
                WHERE session_id = %s AND user_id = %s
            """, (session_id, user_id))
        conn.commit()
    finally:
        conn.close()