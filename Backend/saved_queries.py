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


def init_saved_queries_table():
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS saved_queries (
                    id          INT AUTO_INCREMENT PRIMARY KEY,
                    user_id     INT NOT NULL,
                    name        VARCHAR(255) NOT NULL,
                    collection  VARCHAR(100) DEFAULT 'General',
                    question    TEXT NOT NULL,
                    sql_query   TEXT NOT NULL,
                    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );
            """)
        conn.commit()
        print("✅ Saved queries table ready.")
    finally:
        conn.close()


def save_query(user_id, name, question, sql, collection="General"):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO saved_queries (user_id, name, collection, question, sql_query)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, name, collection, question, sql))
        conn.commit()
        return {"saved": True, "id": cursor.lastrowid}
    finally:
        conn.close()


def get_saved_queries(user_id):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, name, collection, question, sql_query,
                       DATE_FORMAT(created_at, '%Y-%m-%d') as date
                FROM saved_queries
                WHERE user_id = %s
                ORDER BY collection, created_at DESC
            """, (user_id,))
            return cursor.fetchall()
    finally:
        conn.close()


def delete_saved_query(query_id, user_id):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM saved_queries WHERE id = %s AND user_id = %s",
                (query_id, user_id)
            )
        conn.commit()
        return {"deleted": True}
    finally:
        conn.close()


def get_collections(user_id):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT collection FROM saved_queries
                WHERE user_id = %s ORDER BY collection
            """, (user_id,))
            rows = cursor.fetchall()
            return [r["collection"] for r in rows]
    finally:
        conn.close()