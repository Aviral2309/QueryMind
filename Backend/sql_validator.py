""" Block all dangerous queries - only SELECT Allowed"""

import sqlparse
from sqlparse.sql import Statement
from sqlparse.tokens import Keyword, DDL, DML


BLOCKED_KEYWORDS = {
    "DROP", "DELETE", "UPDATE", "INSERT", "ALTER",
    "TRUNCATE", "CREATE", "REPLACE", "MERGE", "EXEC",
    "EXECUTE", "GRANT", "REVOKE", "RENAME"
}


def validate_sql(sql: str) -> dict:
    """
    Returns {"valid": True} if safe SELECT query.
    Returns {"valid": False, "reason": "..."} if dangerous.
    """
    if not sql or not sql.strip():
        return {"valid": False, "reason": "Empty SQL query."}

    # Clean up LLM artifacts — remove markdown code fences if present
    cleaned = sql.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [l for l in lines if not l.startswith("```")]
        cleaned = "\n".join(lines).strip()

    parsed = sqlparse.parse(cleaned)
    if not parsed:
        return {"valid": False, "reason": "Could not parse SQL."}

    statement = parsed[0]
    tokens = list(statement.flatten())

    found_select = False
    for token in tokens:
        token_val = token.value.upper()

        # Check for blocked keywords
        if token_val in BLOCKED_KEYWORDS:
            return {
                "valid": False,
                "reason": f"Query contains blocked keyword: '{token.value}'. Only SELECT queries are allowed."
            }

        # Check it starts with SELECT
        if token.ttype in (DML,) and token_val == "SELECT":
            found_select = True

    if not found_select:
        return {
            "valid": False,
            "reason": "Only SELECT queries are permitted."
        }

    return {"valid": True, "cleaned_sql": cleaned}