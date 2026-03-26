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
You are an expert SQL developer. Based on the schema below,
write a SQL SELECT query that answers the user's question.

RULES:
- Return ONLY raw SQL — no markdown, no fences, no explanation
- Single line only
- Only SELECT statements allowed

Schema: {schema}
Question: {question}

SQL:
""")

memory_prompt = ChatPromptTemplate.from_template("""
You are an expert SQL developer with conversation context.

Previous conversation:
{context}

Database Schema: {schema}
Current Question: {question}

Write a SQL SELECT query based on context and schema.
RULES: Only raw SQL, single line, SELECT only.

SQL:
""")

correction_prompt = ChatPromptTemplate.from_template("""
Fix this broken SQL query. Return ONLY corrected SQL, single line.

Question: {question}
Schema: {schema}
Broken SQL: {broken_sql}
Error: {error}

Fixed SQL:
""")

explanation_prompt = ChatPromptTemplate.from_template("""
Explain this SQL result in 2-3 plain English sentences.
Be specific about what the data shows. Do not include the SQL.

SQL: {sql}
Question: {question}
Row count: {row_count}
""")

suggestions_prompt = ChatPromptTemplate.from_template("""
Based on this database schema, suggest exactly 5 short, specific
questions a data analyst would ask.
One per line. No numbers or bullets. Each under 10 words.

Schema: {schema}

Questions:
""")

storytelling_prompt = ChatPromptTemplate.from_template("""
You are a data analyst. Based on these database query results,
write a short 3-4 sentence business summary.
Focus on key findings, trends, and actionable insights.
Be specific with numbers where available.

Question asked: {question}
SQL used: {sql}
Result summary: {result_summary}

Business Summary:
""")


def generate_sql(schema: str, question: str) -> str:
    chain = generation_prompt | llm | StrOutputParser()
    return chain.invoke(
        {"schema": schema, "question": question}).strip()


def generate_sql_with_memory(schema: str, question: str,
                              context: list) -> str:
    context_str = "\n".join([
        f"{m['role'].upper()}: {m['content']}"
        for m in context
    ])
    chain = memory_prompt | llm | StrOutputParser()
    return chain.invoke({
        "schema":   schema,
        "question": question,
        "context":  context_str
    }).strip()


def correct_sql(schema: str, question: str,
                broken_sql: str, error: str) -> str:
    chain = correction_prompt | llm | StrOutputParser()
    return chain.invoke({
        "schema":     schema,
        "question":   question,
        "broken_sql": broken_sql,
        "error":      error
    }).strip()


def explain_sql(sql: str, question: str,
                row_count: int = 0) -> str:
    chain = explanation_prompt | llm | StrOutputParser()
    return chain.invoke({
        "sql":       sql,
        "question":  question,
        "row_count": row_count
    }).strip()


def suggest_questions(schema: str) -> list:
    chain     = suggestions_prompt | llm | StrOutputParser()
    result    = chain.invoke({"schema": schema}).strip()
    questions = [q.strip() for q in result.split("\n") if q.strip()]
    return questions[:5]


def generate_story(question: str, sql: str,
                   result_summary: str) -> str:
    chain = storytelling_prompt | llm | StrOutputParser()
    return chain.invoke({
        "question":       question,
        "sql":            sql,
        "result_summary": result_summary
    }).strip()