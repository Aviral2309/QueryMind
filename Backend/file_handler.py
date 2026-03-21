import os
import sqlite3
import pandas as pd
import shortuuid

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def save_uploaded_file(file_storage):
    """Save uploaded file to uploads folder with unique name."""
    original_name = file_storage.filename
    ext           = os.path.splitext(original_name)[1].lower()
    unique_name   = f"{shortuuid.uuid()}{ext}"
    filepath      = os.path.join(UPLOAD_FOLDER, unique_name)
    file_storage.save(filepath)
    return filepath, ext, original_name


def csv_to_sqlite(csv_filepath):
    """Convert CSV file to SQLite database."""
    db_path    = csv_filepath.replace(".csv", ".db")
    table_name = os.path.splitext(os.path.basename(csv_filepath))[0]
    table_name = "".join(c if c.isalnum() else "_" for c in table_name)

    df   = pd.read_csv(csv_filepath)
    conn = sqlite3.connect(db_path)
    df.to_sql(table_name, conn, if_exists="replace", index=False)
    conn.close()

    return db_path, table_name


def sql_dump_to_sqlite(sql_filepath):
    """Restore SQL dump to a new SQLite database."""
    db_path = sql_filepath.replace(".sql", ".db")

    with open(sql_filepath, "r", encoding="utf-8", errors="ignore") as f:
        sql_content = f.read()

    # Clean MySQL-specific syntax for SQLite compatibility
    sql_content = sql_content.replace("ENGINE=InnoDB", "")
    sql_content = sql_content.replace("DEFAULT CHARSET=utf8mb4", "")
    sql_content = sql_content.replace("DEFAULT CHARSET=utf8", "")
    sql_content = sql_content.replace("AUTO_INCREMENT", "AUTOINCREMENT")
    sql_content = sql_content.replace("`", '"')

    conn   = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Execute statement by statement
    statements = [s.strip() for s in sql_content.split(";") if s.strip()]
    errors     = []
    for stmt in statements:
        try:
            cursor.execute(stmt)
        except Exception as e:
            errors.append(str(e))

    conn.commit()
    conn.close()

    return db_path, errors


def cleanup_old_uploads(max_age_hours=24):
    """Remove uploaded files older than max_age_hours."""
    import time
    now = time.time()
    for filename in os.listdir(UPLOAD_FOLDER):
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.isfile(filepath):
            age_hours = (now - os.path.getmtime(filepath)) / 3600
            if age_hours > max_age_hours:
                os.remove(filepath)