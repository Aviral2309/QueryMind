'''Generate SQL using Gemini with a self correction loop on error.'''

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

from langchain_ollama import ChatOllama

'''llm = ChatOllama(
    model="gemma3:1b",
    temperature=0
)'''


# Primary generation prompt
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

# Self-correction prompt
correction_prompt = ChatPromptTemplate.from_template("""
You are an expert SQL developer. The following SQL query produced an error.
Fix the query so it works correctly.

STRICT RULES:
- Return ONLY the corrected raw SQL query — no explanation, no markdown, no code fences  
- Write the entire query on a single line
- Only use SELECT statements

Original Question: {question}
Table Schema: {schema}
Broken SQL: {broken_sql}
Error Message: {error}

Corrected SQL Query:
""")

# Explanation prompt
explanation_prompt = ChatPromptTemplate.from_template("""
Explain the following SQL query in simple plain English in 2-3 sentences.
Mention which tables were used and what the query does.
Do not include the SQL itself in your explanation.

SQL Query: {sql}
Question it answers: {question}
""")


def generate_sql(schema: str, question: str) -> str:
    chain = generation_prompt | llm | StrOutputParser()
    result = chain.invoke({"schema": schema, "question": question})
    return result.strip()


def correct_sql(schema: str, question: str, broken_sql: str, error: str) -> str:
    chain = correction_prompt | llm | StrOutputParser()
    result = chain.invoke({
        "schema": schema,
        "question": question,
        "broken_sql": broken_sql,
        "error": error
    })
    return result.strip()


def explain_sql(sql: str, question: str) -> str:
    chain = explanation_prompt | llm | StrOutputParser()
    result = chain.invoke({"sql": sql, "question": question})
    return result.strip()