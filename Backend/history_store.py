import pymysql
import pymysql.cursors
import os
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


def init_history_table():
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            # Create with all columns
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS query_history (
                    id          INT AUTO_INCREMENT PRIMARY KEY,
                    user_id     INT NOT NULL,
                    session_id  VARCHAR(20) DEFAULT NULL,
                    question    TEXT NOT NULL,
                    sql_query   TEXT,
                    success     BOOLEAN DEFAULT FALSE,
                    row_count   INT DEFAULT 0,
                    error       TEXT,
                    response_ms INT DEFAULT 0,
                    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id)
                        REFERENCES users(id) ON DELETE CASCADE
                );
            """)

            # Add columns if upgrading from Phase 2
            try:
                cursor.execute("""
                    ALTER TABLE query_history
                    ADD COLUMN session_id VARCHAR(20) DEFAULT NULL
                """)
            except Exception:
                pass

            try:
                cursor.execute("""
                    ALTER TABLE query_history
                    ADD COLUMN response_ms INT DEFAULT 0
                """)
            except Exception:
                pass

        conn.commit()
        print("✅ History table ready.")
    finally:
        conn.close()


def add_entry(user_id, question, sql, success,
              row_count=0, error=None,
              session_id=None, response_ms=0):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO query_history
                    (user_id, session_id, question, sql_query,
                     success, row_count, error, response_ms)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (user_id, session_id, question, sql,
                  success, row_count, error, response_ms))
        conn.commit()
    finally:
        conn.close()


def get_history(user_id, limit=50):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, session_id, question,
                       sql_query as sql, success,
                       row_count, error, response_ms,
                       DATE_FORMAT(created_at,
                           '%Y-%m-%d %H:%i:%s') as timestamp
                FROM query_history
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
            """, (user_id, limit))
            return cursor.fetchall()
    finally:
        conn.close()


def clear_history(user_id):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM query_history WHERE user_id = %s",
                (user_id,))
        conn.commit()
        return {"cleared": True}
    finally:
        conn.close()


def get_stats(user_id):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(success) as successful,
                    COUNT(*) - SUM(success) as failed,
                    ROUND(SUM(success)/COUNT(*)*100,1) as success_rate,
                    ROUND(AVG(response_ms),0) as avg_response_ms,
                    SUM(row_count) as total_rows_returned
                FROM query_history WHERE user_id = %s
            """, (user_id,))
            return cursor.fetchone()
    finally:
        conn.close()


def get_daily_stats(user_id, days=30):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    DATE(created_at) as date,
                    COUNT(*) as total,
                    SUM(success) as successful,
                    ROUND(AVG(response_ms),0) as avg_ms
                FROM query_history
                WHERE user_id = %s
                  AND created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
                GROUP BY DATE(created_at)
                ORDER BY date ASC
            """, (user_id, days))
            rows = cursor.fetchall()
            for r in rows:
                r["date"] = str(r["date"])
            return rows
    finally:
        conn.close()


def get_failed_queries(user_id, limit=10):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT question, sql_query, error, created_at
                FROM query_history
                WHERE user_id = %s AND success = FALSE
                ORDER BY created_at DESC LIMIT %s
            """, (user_id, limit))
            return cursor.fetchall()
    finally:
        conn.close()