"""Text-to-SQL agent built with LangGraph (with conversation memory).

Flow:
  get_schema -> generate_sql -> (harmful?) -> guardrail (email verify + confirm) -> execute
                                            -> execute
  execute -> (read error?) -> retry generate_sql (self-correction, up to MAX_RETRIES)
  all terminal paths -> finalize (records the answer into conversation memory)

Conversation memory:
  The state carries a `messages` list (with the add_messages reducer). Each turn
  appends the user's question and the assistant's answer, so follow-up questions
  like "and what are their emails?" can be resolved against earlier turns.
"""
import os
import re
import sqlite3
from typing import Annotated, Optional, TypedDict

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import AnyMessage, AIMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.types import interrupt, Command
from langgraph.checkpoint.memory import InMemorySaver

load_dotenv()

DB_PATH = os.path.join(os.path.dirname(__file__), "chinook.db")
MODEL = os.getenv("LLM_MODEL")
MAX_RETRIES = 3
HARMFUL_STARTS = {"DELETE", "UPDATE", "INSERT", "DROP", "ALTER", "TRUNCATE", "REPLACE", "CREATE"}

llm = init_chat_model(MODEL)


# ----------------------------- database helpers -----------------------------
def _connect():
    return sqlite3.connect(DB_PATH)


def fetch_schema() -> str:
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT name, sql FROM sqlite_master "
        "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    parts = []
    for name, create_sql in cur.fetchall():
        parts.append(create_sql.strip())
        try:
            cur.execute(f"SELECT * FROM {name} LIMIT 2")
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
            if rows:
                parts.append(f"-- {name} sample (cols {cols}):")
                for r in rows:
                    parts.append(f"--   {r}")
        except Exception:
            pass
    conn.close()
    return "\n".join(parts)


def verify_member(email: str):
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT FirstName, LastName, Title FROM employees WHERE lower(Email)=lower(?)",
        (email.strip(),),
    )
    row = cur.fetchone()
    conn.close()
    if row:
        return True, f"{row[0]} {row[1]} ({row[2]})"
    return False, None


def preview_impact(sql: str) -> int:
    """Run the write query inside a transaction, read rowcount, then roll back."""
    conn = _connect()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN")
        cur.execute(sql)
        n = cur.rowcount
        conn.rollback()
        return n
    except Exception:
        conn.rollback()
        return -1
    finally:
        conn.close()


def run_read(sql: str):
    conn = _connect()
    cur = conn.cursor()
    cur.execute(sql)
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description] if cur.description else []
    conn.close()
    return cols, rows


def run_write(sql: str) -> int:
    conn = _connect()
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()
    n = cur.rowcount
    conn.close()
    return n


def format_table(cols, rows, limit=50) -> str:
    if not rows:
        return "_(no rows returned)_"
    rows = rows[:limit]
    header = "| " + " | ".join(str(c) for c in cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    body = "\n".join("| " + " | ".join(str(v) for v in r) + " |" for r in rows)
    extra = "" if len(rows) < limit else f"\n\n_(showing first {limit} rows)_"
    return "\n".join([header, sep, body]) + extra


# ------------------------------- LLM helpers --------------------------------
SQL_PROMPT = """You are an expert SQLite analyst. Given the schema and a question,
write ONE valid SQLite query that answers it.

Rules:
- Return ONLY the SQL. No explanation, no markdown fences.
- Use only tables and columns that appear in the schema.
- For "top"/"most"/"highest", use ORDER BY ... DESC with LIMIT.
- The question may be a FOLLOW-UP that refers to a previous one (e.g. "their emails",
  "those customers", "that genre"). Use the conversation below to resolve such references.
{error_note}
Schema:
{schema}
{history}Question: {question}
SQL:"""


def _clean_sql(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    return text.rstrip(";").strip() + ";"


def format_history(messages, max_msgs: int = 6, max_chars: int = 500) -> str:
    if not messages:
        return ""
    lines = ["Conversation so far:"]
    for m in messages[-max_msgs:]:
        role = "User" if isinstance(m, HumanMessage) else "Assistant"
        content = (m.content or "")[:max_chars]
        lines.append(f"{role}: {content}")
    return "\n".join(lines) + "\n"


def generate_sql(question: str, schema: str, history: str, error: Optional[str]) -> str:
    note = ""
    if error:
        note = f"Your previous attempt failed with this error. Fix it:\n{error}\n"
    prompt = SQL_PROMPT.format(
        schema=schema, question=question, history=history, error_note=note
    )
    resp = llm.invoke(prompt)
    return _clean_sql(resp.content)


def explain_result(question: str, cols, rows) -> str:
    if not rows:
        return "_No matching records found._"
    prompt = (
        f"Question: {question}\nColumns: {cols}\nRows (sample): {rows[:10]}\n"
        "In ONE short, friendly sentence, answer the question from this data. "
        "No preamble, no restating the question."
    )
    try:
        return llm.invoke(prompt).content.strip()
    except Exception:
        return ""


def is_harmful(sql: str) -> bool:
    s = sql.strip().lstrip("(").strip()
    first = s.split()[0].upper() if s.split() else ""
    return first in HARMFUL_STARTS


# --------------------------------- graph ------------------------------------
class State(TypedDict, total=False):
    question: str
    messages: Annotated[list[AnyMessage], add_messages]
    schema: str
    sql_query: str
    error: str
    retry_count: int
    is_harmful: bool
    final_answer: str


def node_get_schema(state: State):
    return {"schema": fetch_schema()}


def node_generate(state: State):
    # history = everything except the current question (which is the last message)
    history = format_history(state.get("messages", [])[:-1])
    sql = generate_sql(state["question"], state["schema"], history, state.get("error"))
    return {"sql_query": sql, "is_harmful": is_harmful(sql)}


def route_after_generate(state: State):
    return "guardrail" if state["is_harmful"] else "execute"


def node_guardrail(state: State):
    sql = state["sql_query"]
    email = interrupt(
        "This query will **modify the database**. Please enter your "
        "**company email** to verify you are authorized:"
    )
    verified, name = verify_member(str(email))
    if not verified:
        return {
            "final_answer": (
                f"Access denied. `{email}` is not a recognized authorized "
                f"member, so the query was **not** executed.\n\n"
                f"**Blocked query:**\n```sql\n{sql}\n```"
            )
        }

    affected = preview_impact(sql)
    op = sql.split()[0].upper()
    impact = f"about **{affected} row(s)**" if affected >= 0 else "an unknown number of rows"
    confirm = interrupt(
        f"Verified: **{name}**.\n\n"
        f"This query will **{op}** {impact}:\n```sql\n{sql}\n```\n\n"
        f"Do you still want to proceed?  (**yes** / **no**)"
    )
    if str(confirm).strip().lower() in ("yes", "y", "proceed", "confirm", "ok"):
        return {}  # verified + confirmed -> execute
    return {
        "final_answer": (
            f"Cancelled by **{name}**. No changes were made.\n\n"
            f"**Query:**\n```sql\n{sql}\n```"
        )
    }


def route_after_guardrail(state: State):
    return "finalize" if state.get("final_answer") else "execute"


def node_execute(state: State):
    sql = state["sql_query"]
    try:
        if state.get("is_harmful"):
            n = run_write(sql)
            return {
                "final_answer": (
                    f"Executed successfully. **{n} row(s) affected.**\n\n"
                    f"**Query:**\n```sql\n{sql}\n```"
                ),
                "error": "",
            }
        cols, rows = run_read(sql)
        table = format_table(cols, rows)
        summary = explain_result(state["question"], cols, rows)
        return {
            "final_answer": (
                f"**Query:**\n```sql\n{sql}\n```\n\n"
                f"**Result:**\n{table}\n\n{summary}"
            ),
            "error": "",
        }
    except Exception as e:
        return {"error": str(e), "retry_count": state.get("retry_count", 0) + 1}


def route_after_execute(state: State):
    if state.get("error"):
        if not state.get("is_harmful") and state.get("retry_count", 0) < MAX_RETRIES:
            return "generate"  # self-correct
        return "fail"
    return "finalize"


def node_fail(state: State):
    return {
        "final_answer": (
            f"Sorry, I couldn't run this after {MAX_RETRIES} attempts.\n\n"
            f"**Last query:**\n```sql\n{state.get('sql_query', '')}\n```\n"
            f"**Error:** {state.get('error')}"
        )
    }


def node_finalize(state: State):
    # Record the assistant's answer into conversation memory.
    return {"messages": [AIMessage(content=state.get("final_answer", ""))]}


def build_graph():
    b = StateGraph(State)
    b.add_node("get_schema", node_get_schema)
    b.add_node("generate", node_generate)
    b.add_node("guardrail", node_guardrail)
    b.add_node("execute", node_execute)
    b.add_node("fail", node_fail)
    b.add_node("finalize", node_finalize)

    b.add_edge(START, "get_schema")
    b.add_edge("get_schema", "generate")
    b.add_conditional_edges("generate", route_after_generate)
    b.add_conditional_edges("guardrail", route_after_guardrail)
    b.add_conditional_edges("execute", route_after_execute)
    b.add_edge("fail", "finalize")
    b.add_edge("finalize", END)

    return b.compile(checkpointer=InMemorySaver())


graph = build_graph()
