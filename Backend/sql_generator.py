import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    api_key=os.getenv("GEMINI_API_KEY"),
    temperature=0.1
)

generation_prompt = ChatPromptTemplate.from_template("""
You are an expert SQL developer. Based on the database schema below,
write a SQL SELECT query that answers the user's question.

STRICT RULES:
- Return ONLY the raw SQL query — no explanation, no markdown, no code fences
- Write the entire query on a single line
- Only use SELECT statements — never DROP, DELETE, UPDATE, INSERT, ALTER
- Use backticks for column/table names that contain spaces or special characters

Table Schema:
{schema}

Question: {question}

SQL Query:
""")

correction_prompt = ChatPromptTemplate.from_template("""
You are an expert SQL developer. Fix the following broken SQL query.

STRICT RULES:
- Return ONLY the corrected raw SQL — no explanation, no markdown, no code fences
- Single line only
- SELECT only

Question: {question}
Schema: {schema}
Broken SQL: {broken_sql}
Error: {error}

Corrected SQL:
""")

explanation_prompt = ChatPromptTemplate.from_template("""
Explain this SQL query in 2-3 plain English sentences.
Mention which tables were used and what the query does.
Do not include the SQL itself.

SQL: {sql}
Question: {question}
""")

suggestions_prompt = ChatPromptTemplate.from_template("""
You are a data analyst. Based on the database schema below,
suggest exactly 5 interesting questions a user could ask about this data.

STRICT RULES:
- Return exactly 5 questions
- One question per line
- No numbering, no bullets, no extra text
- Keep each question short and specific (under 10 words)
- Questions should be answerable with a SELECT query

Schema:
{schema}

5 Questions:
""")

chart_detection_prompt = ChatPromptTemplate.from_template("""
Given these SQL query results, determine the best chart type to visualize them.

Columns: {columns}
Sample rows (first 3): {sample_rows}
Question asked: {question}

Return ONLY one of these exact strings — nothing else:
- bar
- line
- pie
- none

Chart type:
""")


def generate_sql(schema: str, question: str) -> str:
    chain  = generation_prompt | llm | StrOutputParser()
    return chain.invoke({"schema": schema, "question": question}).strip()


def correct_sql(schema: str, question: str, broken_sql: str, error: str) -> str:
    chain  = correction_prompt | llm | StrOutputParser()
    return chain.invoke({
        "schema": schema, "question": question,
        "broken_sql": broken_sql, "error": error
    }).strip()


def explain_sql(sql: str, question: str) -> str:
    chain  = explanation_prompt | llm | StrOutputParser()
    return chain.invoke({"sql": sql, "question": question}).strip()


def suggest_questions(schema: str) -> list:
    chain    = suggestions_prompt | llm | StrOutputParser()
    result   = chain.invoke({"schema": schema}).strip()
    questions = [q.strip() for q in result.split("\n") if q.strip()]
    return questions[:5]


def detect_chart_type(columns: list, rows: list, question: str) -> str:
    if not rows or len(rows) == 0:
        return "none"
    sample = rows[:3]
    chain  = chart_detection_prompt | llm | StrOutputParser()
    result = chain.invoke({
        "columns":     str(columns),
        "sample_rows": str(sample),
        "question":    question
    }).strip().lower()
    if result not in ["bar", "line", "pie"]:
        return "none"
    return result