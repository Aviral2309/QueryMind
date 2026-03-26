import os
from dotenv import load_dotenv
import pymysql
import pymysql.cursors

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


def init_ragas_table():
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ragas_scores (
                    id                  INT AUTO_INCREMENT PRIMARY KEY,
                    user_id             INT NOT NULL,
                    session_id          VARCHAR(20),
                    question            TEXT,
                    sql_query           TEXT,
                    answer              TEXT,
                    faithfulness        FLOAT DEFAULT NULL,
                    answer_relevancy    FLOAT DEFAULT NULL,
                    context_precision   FLOAT DEFAULT NULL,
                    sql_correctness     FLOAT DEFAULT NULL,
                    overall_score       FLOAT DEFAULT NULL,
                    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id)
                        REFERENCES users(id) ON DELETE CASCADE
                );
            """)
        conn.commit()
        print("✅ RAGAS table ready.")
    finally:
        conn.close()


def compute_sql_correctness(sql: str, success: bool, row_count: int) -> float:
    """
    Rule-based SQL correctness score since full RAGAS needs
    reference answers. Score 0-1.
    """
    if not success:
        return 0.0
    if not sql or not sql.strip():
        return 0.0

    score = 0.6  # base score for successful execution

    sql_upper = sql.upper()

    # Reward proper SQL patterns
    if "SELECT" in sql_upper:
        score += 0.1
    if "FROM" in sql_upper:
        score += 0.05
    if row_count > 0:
        score += 0.1
    if any(kw in sql_upper for kw in ["JOIN", "GROUP BY", "ORDER BY", "WHERE"]):
        score += 0.1
    if row_count == 0 and "LIMIT" not in sql_upper:
        score -= 0.1

    return round(min(max(score, 0.0), 1.0), 3)


def compute_answer_relevancy(question: str, explanation: str) -> float:
    """
    Heuristic relevancy score based on keyword overlap.
    """
    if not question or not explanation:
        return 0.5

    q_words = set(question.lower().split())
    e_words = set(explanation.lower().split())

    # Remove stop words
    stop = {"the", "a", "an", "is", "are", "was", "were", "of",
            "to", "in", "on", "at", "by", "for", "with", "what",
            "how", "show", "me", "give", "list", "find", "get"}
    q_words -= stop
    e_words -= stop

    if not q_words:
        return 0.5

    overlap = len(q_words & e_words)
    score   = overlap / len(q_words)
    return round(min(score * 1.5, 1.0), 3)


def store_ragas_score(user_id, session_id, question, sql,
                      explanation, success, row_count):
    sql_score      = compute_sql_correctness(sql, success, row_count)
    relevancy_score = compute_answer_relevancy(question, explanation)

    # Faithfulness — did we actually execute and get results?
    faithfulness = 1.0 if success and row_count > 0 else (
        0.5 if success else 0.0
    )

    # Context precision — did FAISS find right tables? Approximation
    context_precision = 0.85 if success else 0.4

    overall = round(
        (sql_score + relevancy_score + faithfulness + context_precision) / 4,
        3
    )

    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO ragas_scores
                    (user_id, session_id, question, sql_query,
                     answer, faithfulness, answer_relevancy,
                     context_precision, sql_correctness, overall_score)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                user_id, session_id, question, sql,
                explanation, faithfulness, relevancy_score,
                context_precision, sql_score, overall
            ))
        conn.commit()
    finally:
        conn.close()

    return {
        "faithfulness":      faithfulness,
        "answer_relevancy":  relevancy_score,
        "context_precision": context_precision,
        "sql_correctness":   sql_score,
        "overall_score":     overall
    }


def get_ragas_summary(user_id):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    COUNT(*) as total_evaluated,
                    ROUND(AVG(faithfulness)*100, 1)      as faithfulness,
                    ROUND(AVG(answer_relevancy)*100, 1)  as answer_relevancy,
                    ROUND(AVG(context_precision)*100, 1) as context_precision,
                    ROUND(AVG(sql_correctness)*100, 1)   as sql_correctness,
                    ROUND(AVG(overall_score)*100, 1)     as overall_score
                FROM ragas_scores WHERE user_id = %s
            """, (user_id,))
            return cursor.fetchone()
    finally:
        conn.close()


def get_ragas_trend(user_id, days=14):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    DATE(created_at) as date,
                    ROUND(AVG(overall_score)*100,1) as avg_score,
                    ROUND(AVG(sql_correctness)*100,1) as sql_score,
                    COUNT(*) as count
                FROM ragas_scores
                WHERE user_id = %s
                  AND created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
                GROUP BY DATE(created_at)
                ORDER BY date ASC
            """, (user_id, days))
            return cursor.fetchall()
    finally:
        conn.close()


def get_low_scoring_queries(user_id, limit=5):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT question, sql_query, overall_score,
                       sql_correctness, faithfulness,
                       DATE_FORMAT(created_at,'%Y-%m-%d') as date
                FROM ragas_scores
                WHERE user_id = %s
                ORDER BY overall_score ASC
                LIMIT %s
            """, (user_id, limit))
            return cursor.fetchall()
    finally:
        conn.close()