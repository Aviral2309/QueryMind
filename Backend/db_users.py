import pymysql
import pymysql.cursors
import os
from dotenv import load_dotenv

load_dotenv()


def get_mysql_connection():
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", 3306)),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DATABASE", "querymind_users"),
        cursorclass=pymysql.cursors.DictCursor
    )


def init_users_table():
    """Create users table if it doesn't exist."""
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id          INT AUTO_INCREMENT PRIMARY KEY,
                    name        VARCHAR(100) NOT NULL,
                    email       VARCHAR(255) NOT NULL UNIQUE,
                    password    VARCHAR(255) DEFAULT NULL,
                    auth_type   VARCHAR(20) DEFAULT 'email',
                    google_id   VARCHAR(255) DEFAULT NULL,
                    avatar      TEXT DEFAULT NULL,
                    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_login  DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)
        conn.commit()
        print("✅ Users table ready.")
    finally:
        conn.close()


def create_user(name, email, hashed_password, auth_type="email", google_id=None, avatar=None):
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO users (name, email, password, auth_type, google_id, avatar)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (name, email, hashed_password, auth_type, google_id, avatar))
            conn.commit()
            user_id = cursor.lastrowid
            cursor.execute("""
                SELECT id, name, email, auth_type, avatar, created_at
                FROM users WHERE id = %s
            """, (user_id,))
            return cursor.fetchone()
    except pymysql.err.IntegrityError:
        conn.rollback()
        return None
    finally:
        conn.close()


def get_user_by_email(email):
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            return cursor.fetchone()
    finally:
        conn.close()


def get_user_by_id(user_id):
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            return cursor.fetchone()
    finally:
        conn.close()


def get_user_by_google_id(google_id):
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE google_id = %s", (google_id,))
            return cursor.fetchone()
    finally:
        conn.close()


def update_last_login(user_id):
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s",
                (user_id,)
            )
        conn.commit()
    finally:
        conn.close()