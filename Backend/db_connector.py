from langchain_community.utilities import SQLDatabase
from urllib.parse import quote_plus
import os

_db_instance     = None
_db_type         = None
_raw_conn_string = None


def connect_mysql(host, port, username, password, database):
    global _db_instance, _db_type, _raw_conn_string
    encoded_password = quote_plus(password)
    uri              = f"mysql+pymysql://{username}:{encoded_password}@{host}:{port}/{database}"
    _db_instance     = SQLDatabase.from_uri(uri, sample_rows_in_table_info=1)
    _db_type         = "mysql"
    _raw_conn_string = uri
    return {"status": "connected", "db_type": "mysql", "database": database}


def connect_sqlite(filepath):
    global _db_instance, _db_type, _raw_conn_string
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"SQLite file not found: {filepath}")
    uri              = f"sqlite:///{filepath}"
    _db_instance     = SQLDatabase.from_uri(uri, sample_rows_in_table_info=1)
    _db_type         = "sqlite"
    _raw_conn_string = uri
    return {"status": "connected", "db_type": "sqlite", "filepath": filepath}


def connect_uploaded_db(filepath):
    global _db_instance, _db_type, _raw_conn_string
    uri              = f"sqlite:///{filepath}"
    _db_instance     = SQLDatabase.from_uri(uri, sample_rows_in_table_info=1)
    _db_type         = "sqlite_upload"
    _raw_conn_string = uri
    return {"status": "connected", "db_type": "sqlite_upload", "filepath": filepath}


def get_db():
    if _db_instance is None:
        raise ConnectionError("No database connected.")
    return _db_instance


def get_schema():
    return get_db().get_table_info()


def get_table_names():
    return get_db().get_usable_table_names()


def is_connected():
    return _db_instance is not None


def get_db_type():
    return _db_type


def disconnect():
    global _db_instance, _db_type, _raw_conn_string
    _db_instance     = None
    _db_type         = None
    _raw_conn_string = None