import sqlparse
from sqlparse.tokens import DML

BLOCKED_KEYWORDS = {
    "DROP", "DELETE", "UPDATE", "INSERT", "ALTER",
    "TRUNCATE", "CREATE", "REPLACE", "MERGE", "EXEC",
    "EXECUTE", "GRANT", "REVOKE", "RENAME"
}


def validate_sql(sql: str) -> dict:
    if not sql or not sql.strip():
        return {"valid": False, "reason": "Empty SQL query."}

    cleaned = sql.strip()
    if cleaned.startswith("```"):
        lines   = cleaned.split("\n")
        lines   = [l for l in lines if not l.startswith("```")]
        cleaned = "\n".join(lines).strip()

    parsed = sqlparse.parse(cleaned)
    if not parsed:
        return {"valid": False, "reason": "Could not parse SQL."}

    tokens      = list(parsed[0].flatten())
    found_select = False

    for token in tokens:
        token_val = token.value.upper()
        if token_val in BLOCKED_KEYWORDS:
            return {
                "valid":  False,
                "reason": f"Blocked keyword detected: '{token.value}'. Only SELECT queries are allowed."
            }
        if token.ttype in (DML,) and token_val == "SELECT":
            found_select = True

    if not found_select:
        return {"valid": False, "reason": "Only SELECT queries are permitted."}

    return {"valid": True, "cleaned_sql": cleaned}