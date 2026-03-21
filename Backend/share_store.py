import pymysql
import pymysql.cursors
import os
import shortuuid
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


def init_share_table():
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS shared_queries (
                    id          INT AUTO_INCREMENT PRIMARY KEY,
                    share_id    VARCHAR(12) NOT NULL UNIQUE,
                    user_id     INT NOT NULL,
                    question    TEXT NOT NULL,
                    sql_query   TEXT NOT NULL,
                    columns_json TEXT,
                    rows_json   LONGTEXT,
                    row_count   INT DEFAULT 0,
                    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );
            """)
        conn.commit()
        print("✅ Share table ready.")
    finally:
        conn.close()


def create_share(user_id, question, sql, columns, rows, row_count):
    import json
    conn     = get_conn()
    share_id = shortuuid.uuid()[:10]
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO shared_queries
                    (share_id, user_id, question, sql_query, columns_json, rows_json, row_count)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                share_id, user_id, question, sql,
                json.dumps(columns), json.dumps(rows), row_count
            ))
        conn.commit()
        return share_id
    finally:
        conn.close()


def get_share(share_id):
    import json
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM shared_queries WHERE share_id = %s", (share_id,)
            )
            row = cursor.fetchone()
            if row:
                row["columns"] = json.loads(row["columns_json"])
                row["rows"]    = json.loads(row["rows_json"])
            return row
    finally:
        conn.close()