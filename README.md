# 🧮 SQL Analyst Agent

A **natural-language database assistant** built with **LangGraph**. Ask a
question in plain English → the agent writes SQL, runs it, and explains the
result. It **fixes its own broken queries** and requires an **email-verified
human approval** before running anything that changes the database.

Built on a self-contained **Chinook** music-store SQLite database, with a
polished **Gradio** UI.

---

## ✨ What it does

- **Text → SQL:** converts English questions into SQLite queries using the live database schema.
- **Self-correction loop:** if a query errors, it reads the error and rewrites the query (up to 3 tries).
- **Safety guardrail (human-in-the-loop):** any `DELETE` / `UPDATE` / `INSERT` / `DROP`:
  1. asks for your **company email**,
  2. verifies it against the `employees` table,
  3. **previews the impact** ("this will delete 4 rows"),
  4. asks you to **confirm** before executing.
- **Transparent:** shows the exact SQL it wrote for every answer.

## 🧠 Architecture (LangGraph)

```
START → get_schema → generate_sql → (harmful?) ──► guardrail ──► execute
                                    (read)     ──────────────►  execute
execute ──(read error, retries left)──► generate_sql   (self-correction)
guardrail: interrupt(email) → verify → preview impact → interrupt(confirm)
```

- **State** carries the question, schema, SQL, error, retry count.
- **Interrupts** power the email + confirmation steps.
- **Conditional edges** route read-vs-write, verified-or-denied, retry-or-finish.
- **Checkpointer** (`InMemorySaver`) persists state across the interrupt/resume.

## 🚀 Setup

```bash
# 1. install
pip install -r requirements.txt

# 2. add your API key
cp .env.example .env        # then edit .env and paste your GOOGLE_API_KEY

# 3. build the database
python setup_database.py

# 4. run the app
python app.py
```

Then open the local URL Gradio prints (usually http://127.0.0.1:7860).

> Uses **Google Gemini** by default (free tier). To switch to Claude/OpenAI,
> change `LLM_MODEL` in `.env` and install the matching package.

## 💬 Things to try

| Ask this | What happens |
|---|---|
| *Who are the top 5 customers by total spending?* | read query + plain-English answer |
| *How many customers are there in each country?* | grouped aggregation |
| *What are the 5 longest tracks?* | ORDER BY + LIMIT |
| *Delete all invoices from Germany* | triggers **email verification + confirmation** |

**Authorized emails** (in the `employees` table): `andrew@chinookcorp.com`,
`nancy@chinookcorp.com`, `michael@chinookcorp.com`. An unknown email is denied.

> Ran a destructive query and want your data back? Just run
> `python setup_database.py` again to reset.

## 📁 Files

| File | Purpose |
|---|---|
| `setup_database.py` | builds the Chinook SQLite database |
| `agent.py` | the LangGraph agent (schema, SQL gen, self-correction, guardrail) |
| `app.py` | the Gradio chat UI |
| `requirements.txt` / `.env.example` | dependencies & config |

## 🧾 Résumé line

> Built a self-correcting **Text-to-SQL agent** (LangGraph, RAG-style schema
> grounding) that turns natural-language questions into validated SQL with
> automatic error recovery and **email-verified human-approval guardrails** for
> data-changing operations.
