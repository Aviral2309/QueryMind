import os
import sqlite3
import pandas as pd
import shortuuid

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def save_uploaded_file(file_storage):
    original_name = file_storage.filename
    ext           = os.path.splitext(original_name)[1].lower()
    unique_name   = f"{shortuuid.uuid()}{ext}"
    filepath      = os.path.join(UPLOAD_FOLDER, unique_name)
    file_storage.save(filepath)
    return filepath, ext, original_name


def csv_to_sqlite(csv_filepath):
    db_path    = csv_filepath.replace(".csv", ".db")
    table_name = os.path.splitext(
        os.path.basename(csv_filepath))[0]
    table_name = "".join(
        c if c.isalnum() else "_" for c in table_name)

    df   = pd.read_csv(csv_filepath)
    conn = sqlite3.connect(db_path)
    df.to_sql(table_name, conn, if_exists="replace", index=False)
    conn.close()
    return db_path, table_name


def sql_dump_to_sqlite(sql_filepath):
    db_path = sql_filepath.replace(".sql", ".db")

    with open(sql_filepath, "r",
              encoding="utf-8", errors="ignore") as f:
        sql_content = f.read()

    sql_content = sql_content.replace("ENGINE=InnoDB", "")
    sql_content = sql_content.replace("DEFAULT CHARSET=utf8mb4", "")
    sql_content = sql_content.replace("DEFAULT CHARSET=utf8", "")
    sql_content = sql_content.replace("AUTO_INCREMENT", "AUTOINCREMENT")
    sql_content = sql_content.replace("`", '"')

    conn   = sqlite3.connect(db_path)
    cursor = conn.cursor()
    errors = []

    for stmt in sql_content.split(";"):
        stmt = stmt.strip()
        if stmt:
            try:
                cursor.execute(stmt)
            except Exception as e:
                errors.append(str(e))

    conn.commit()
    conn.close()
    return db_path, errors