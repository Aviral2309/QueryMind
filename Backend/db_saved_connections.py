import pymysql
import pymysql.cursors
import os
import base64
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


def _encode(text):
    """Simple base64 encode for storage (not production encryption)."""
    if not text:
        return None
    return base64.b64encode(text.encode()).decode()


def _decode(text):
    if not text:
        return ""
    try:
        return base64.b64decode(text.encode()).decode()
    except:
        return ""


def init_connections_table():
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS saved_connections (
                    id          INT AUTO_INCREMENT PRIMARY KEY,
                    user_id     INT NOT NULL,
                    nickname    VARCHAR(100) NOT NULL,
                    db_type     VARCHAR(20) NOT NULL,
                    host        VARCHAR(255),
                    port        VARCHAR(10),
                    username    VARCHAR(100),
                    password    TEXT,
                    database_name VARCHAR(255),
                    filepath    TEXT,
                    last_used   DATETIME DEFAULT CURRENT_TIMESTAMP,
                    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                        ON DELETE CASCADE
                );
            """)
        conn.commit()
        print("✅ Saved connections table ready.")
    finally:
        conn.close()


def save_connection(user_id, nickname, db_type, host=None,
                    port=None, username=None, password=None,
                    database_name=None, filepath=None):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO saved_connections
                    (user_id, nickname, db_type, host, port,
                     username, password, database_name, filepath)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                user_id, nickname, db_type, host, port,
                username, _encode(password), database_name, filepath
            ))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_user_connections(user_id):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, nickname, db_type, host, port,
                       username, database_name, filepath,
                       last_used, created_at
                FROM saved_connections
                WHERE user_id = %s
                ORDER BY last_used DESC
            """, (user_id,))
            return cursor.fetchall()
    finally:
        conn.close()


def get_connection_by_id(conn_id, user_id):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM saved_connections
                WHERE id = %s AND user_id = %s
            """, (conn_id, user_id))
            row = cursor.fetchone()
            if row:
                row["password"] = _decode(row["password"])
            return row
    finally:
        conn.close()


def update_last_used(conn_id):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE saved_connections
                SET last_used = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (conn_id,))
        conn.commit()
    finally:
        conn.close()


def delete_connection(conn_id, user_id):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                DELETE FROM saved_connections
                WHERE id = %s AND user_id = %s
            """, (conn_id, user_id))
        conn.commit()
    finally:
        conn.close()