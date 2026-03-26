import pymysql
import pymysql.cursors
import os
from datetime import date
from dotenv import load_dotenv

load_dotenv()

DAILY_LIMIT = 20


def get_conn():
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", 3306)),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DATABASE", "querymind_users"),
        cursorclass=pymysql.cursors.DictCursor
    )


def init_usage_table():
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_usage (
                    id          INT AUTO_INCREMENT PRIMARY KEY,
                    user_id     INT NOT NULL,
                    usage_date  DATE NOT NULL,
                    query_count INT DEFAULT 0,
                    UNIQUE KEY unique_user_date (user_id, usage_date),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                        ON DELETE CASCADE
                );
            """)
        conn.commit()
        print("✅ Usage table ready.")
    finally:
        conn.close()


def get_today_usage(user_id):
    conn = get_conn()
    today = date.today().isoformat()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT query_count FROM daily_usage
                WHERE user_id = %s AND usage_date = %s
            """, (user_id, today))
            row = cursor.fetchone()
            return row["query_count"] if row else 0
    finally:
        conn.close()


def increment_usage(user_id):
    conn = get_conn()
    today = date.today().isoformat()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO daily_usage (user_id, usage_date, query_count)
                VALUES (%s, %s, 1)
                ON DUPLICATE KEY UPDATE query_count = query_count + 1
            """, (user_id, today))
        conn.commit()
    finally:
        conn.close()


def can_query(user_id):
    used = get_today_usage(user_id)
    return used < DAILY_LIMIT, used, DAILY_LIMIT


def get_usage_history(user_id, days=30):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT usage_date, query_count
                FROM daily_usage
                WHERE user_id = %s
                  AND usage_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                ORDER BY usage_date ASC
            """, (user_id, days))
            return cursor.fetchall()
    finally:
        conn.close()