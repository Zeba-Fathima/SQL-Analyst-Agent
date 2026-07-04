"""Gradio UI for the Text-to-SQL Analyst Agent."""
import os
import uuid

import gradio as gr
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from agent import DB_PATH, graph
import setup_database

# Make sure the database exists before we start.
if not os.path.exists(DB_PATH):
    setup_database.build_database()


WELCOME = (
    "Hi! I'm your **SQL Analyst**. Ask me anything about the music-store "
    "database in plain English and I'll write and run the query for you.\n\n"
    "Try one of the examples below, or ask your own. Data-changing queries "
    "(DELETE / UPDATE) will ask you to verify your company email first."
)


def chat_fn(message, history, sess):
    message = (message or "").strip()
    if not message:
        return history, sess, ""

    # One thread per browser session -> the whole conversation is remembered.
    if sess is None:
        sess = {"thread_id": str(uuid.uuid4()), "pending": False}

    config = {"configurable": {"thread_id": sess["thread_id"]}}

    try:
        if sess["pending"]:
            result = graph.invoke(Command(resume=message), config)
        else:
            result = graph.invoke(
                {
                    "messages": [HumanMessage(content=message)],
                    "question": message,
                    "retry_count": 0,
                    "error": "",
                },
                config,
            )
    except Exception as e:
        bot = f"⚠️ Something went wrong: `{e}`"
        history = history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": bot},
        ]
        sess["pending"] = False
        return history, sess, ""

    interrupts = result.get("__interrupt__")
    if interrupts:
        bot = interrupts[0].value
        sess["pending"] = True
    else:
        bot = result.get("final_answer") or "Done."
        sess["pending"] = False

    history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": bot},
    ]
    return history, sess, ""


INFO_PANEL = """
### 🗄️ The Database
A small **music store** (Chinook-style):
`employees` · `customers` · `invoices` · `invoice_items` · `tracks` · `albums` · `artists` · `genres`

### 🔐 Try the safety guardrail
Ask something destructive like *"Delete all invoices from Germany"* — the agent
will demand a verified **company email** before it runs.

**Authorized emails you can test with:**
- `andrew@chinookcorp.com`
- `nancy@chinookcorp.com`
- `michael@chinookcorp.com`

(An unknown email will be **denied**.)

### ✨ Under the hood
- Writes SQL from the live **schema**
- **Self-corrects** failed queries automatically
- **Human-in-the-loop** approval for risky writes
"""

# Force the page into light mode so contrast is always good.
FORCE_LIGHT = """
() => {
    const url = new URL(window.location.href);
    if (url.searchParams.get('__theme') !== 'light') {
        url.searchParams.set('__theme', 'light');
        window.location.href = url.href;
    }
}
"""

CSS = """
.gradio-container {
    background: linear-gradient(135deg, #eef2ff 0%, #f8fafc 55%, #ecfeff 100%) !important;
}
#hero {
    text-align: center;
    padding: 28px 16px 10px 16px;
}
#hero h1 {
    font-size: 2.25rem;
    font-weight: 800;
    margin: 0;
    background: linear-gradient(90deg, #4f46e5, #0891b2);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
#hero p {
    color: #475569;
    margin-top: 6px;
    font-size: 1.02rem;
}
#chat {
    border: 1px solid #e2e8f0 !important;
    border-radius: 16px !important;
    background: #ffffff !important;
    box-shadow: 0 6px 22px rgba(79,70,229,0.08);
}
#chat * { color: #0f172a; }
#panel {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    padding: 6px 18px;
    box-shadow: 0 6px 22px rgba(79,70,229,0.08);
}
#panel, #panel * { color: #1e293b !important; }
#panel code, #chat code {
    background: #eef2ff !important;
    color: #4338ca !important;
    padding: 2px 6px;
    border-radius: 6px;
    font-size: 0.9em;
}
.gr-button-primary, button.primary {
    background: linear-gradient(90deg, #4f46e5, #6366f1) !important;
    border: none !important;
    color: #ffffff !important;
}
footer { visibility: hidden; }
"""

theme = gr.themes.Soft(
    primary_hue="indigo",
    secondary_hue="cyan",
    neutral_hue="slate",
)

with gr.Blocks(title="SQL Analyst Agent", js=FORCE_LIGHT) as demo:
    gr.HTML(
        "<div id='hero'>"
        "<h1>🧮 SQL Analyst Agent</h1>"
        "<p>Ask your database in plain English — with self-correction &amp; "
        "email-verified safety guardrails</p>"
        "</div>"
    )

    chatbot = gr.Chatbot(
        value=[{"role": "assistant", "content": WELCOME}],
        height=520,
        elem_id="chat",
        show_label=False,
    )
    with gr.Row():
        msg = gr.Textbox(
            placeholder="e.g. Who are the top 5 customers by total spending?",
            show_label=False,
            scale=8,
            autofocus=True,
        )
        send = gr.Button("Send  ➤", variant="primary", scale=1)

    gr.Examples(
        examples=[
            "How many customers are there in each country?",
            "Who are the top 5 customers by total spending?",
            "List all employees and their titles",
            "What are the 5 longest tracks?",
            "Which genre has the most tracks?",
            "Delete all invoices from Germany",
        ],
        inputs=msg,
        label="Try an example",
    )

    sess = gr.State(None)

    send.click(chat_fn, [msg, chatbot, sess], [chatbot, sess, msg])
    msg.submit(chat_fn, [msg, chatbot, sess], [chatbot, sess, msg])


if __name__ == "__main__":
    demo.launch(theme=theme, css=CSS)
