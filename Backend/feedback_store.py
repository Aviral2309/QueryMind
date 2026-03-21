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


def init_feedback_table():
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id          INT AUTO_INCREMENT PRIMARY KEY,
                    user_id     INT NOT NULL,
                    question    TEXT NOT NULL,
                    sql_query   TEXT,
                    rating      TINYINT NOT NULL,  -- 1 = thumbs up, 0 = thumbs down
                    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );
            """)
        conn.commit()
        print("✅ Feedback table ready.")
    finally:
        conn.close()


def add_feedback(user_id, question, sql, rating):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO feedback (user_id, question, sql_query, rating)
                VALUES (%s, %s, %s, %s)
            """, (user_id, question, sql, rating))
        conn.commit()
        return {"saved": True}
    finally:
        conn.close()


def get_feedback_stats(user_id):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(rating) as positive,
                    COUNT(*) - SUM(rating) as negative,
                    ROUND(SUM(rating) / COUNT(*) * 100, 1) as positive_rate
                FROM feedback WHERE user_id = %s
            """, (user_id,))
            return cursor.fetchone()
    finally:
        conn.close()


def get_recent_feedback(user_id, limit=20):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT question, sql_query, rating,
                       DATE_FORMAT(created_at, '%Y-%m-%d %H:%i') as date
                FROM feedback WHERE user_id = %s
                ORDER BY created_at DESC LIMIT %s
            """, (user_id, limit))
            return cursor.fetchall()
    finally:
        conn.close()