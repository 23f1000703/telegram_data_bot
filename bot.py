'''
import os
import json
import time

from openai import OpenAI
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    filters,
)

# ==========================
# Environment Variables
# ==========================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
AIPIPE_TOKEN = os.getenv("AIPIPE_TOKEN")

# Temporary value
LOG_URL = "https://raw.githubusercontent.com/23f1000703/telegram_data_bot/refs/heads/main/run.jsonl"

client = OpenAI(
    base_url="https://aipipe.org/openai/v1",
    api_key=AIPIPE_TOKEN,
)

LOG_FILE = "run.jsonl"

conversation_history = {}


# ==========================
# Logging
# ==========================

def log_event(event):
    event["timestamp"] = time.time()

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")


# ==========================
# Telegram Handler
# ==========================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat_id = update.effective_chat.id
    question = update.message.text

    log_event({
        "type": "incoming",
        "chat_id": chat_id,
        "question": question
    })

    history = conversation_history.setdefault(chat_id, [])

    history.append(
        {
            "role": "user",
            "content": question
        }
    )

    system_prompt = """
You are an expert data analyst.

Answer ONLY the user's LAST message.

Reply with ONLY one JSON object.

Never write markdown.

Never write explanation.

Never use ```.

Return only valid JSON.
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            }
        ] + history[-6:]
    )

    reply = response.choices[0].message.content.strip()

    try:
        data = json.loads(reply)

    except:

        start = reply.find("{")
        end = reply.rfind("}")

        data = json.loads(reply[start:end + 1])

    data["log_url"] = LOG_URL

    final_reply = json.dumps(data)

    history.append(
        {
            "role": "assistant",
            "content": final_reply
        }
    )

    log_event({
        "type": "outgoing",
        "chat_id": chat_id,
        "response": final_reply
    })

    await update.message.reply_text(final_reply)


# ==========================
# Run Bot
# ==========================

app = ApplicationBuilder().token(
    TELEGRAM_BOT_TOKEN
).build()

app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message,
    )
)

print("Bot Running...")

app.run_polling()
'''

import os
import json
import time
import base64
import requests

from openai import OpenAI
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    filters,
)

# ==========================
# Environment Variables
# ==========================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
AIPIPE_TOKEN = os.getenv("AIPIPE_TOKEN")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_OWNER = os.getenv("GITHUB_OWNER")
GITHUB_REPO = os.getenv("GITHUB_REPO")

BRANCH = "main"

LOG_FILE = "run.jsonl"

LOG_URL = (
    f"https://raw.githubusercontent.com/"
    f"{GITHUB_OWNER}/{GITHUB_REPO}/{BRANCH}/run.jsonl"
)

client = OpenAI(
    base_url="https://aipipe.org/openai/v1",
    api_key=AIPIPE_TOKEN,
)

conversation_history = {}

# ==========================
# GitHub Upload
# ==========================

def upload_log_to_github():

    if not (
        GITHUB_TOKEN
        and GITHUB_OWNER
        and GITHUB_REPO
    ):
        return

    url = (
        f"https://api.github.com/repos/"
        f"{GITHUB_OWNER}/{GITHUB_REPO}/contents/{LOG_FILE}"
    )

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }

    sha = None

    r = requests.get(url, headers=headers)

    if r.status_code == 200:
        sha = r.json()["sha"]

    with open(LOG_FILE, "rb") as f:
        content = base64.b64encode(
            f.read()
        ).decode()

    payload = {
        "message": "Update run.jsonl",
        "content": content,
        "branch": BRANCH,
    }

    if sha:
        payload["sha"] = sha

    requests.put(
        url,
        headers=headers,
        json=payload,
        timeout=30,
    )

    # ==========================
# Logging
# ==========================

def log_event(event):

    event["timestamp"] = time.time()

    with open(
        LOG_FILE,
        "a",
        encoding="utf-8"
    ) as f:

        f.write(
            json.dumps(event, ensure_ascii=False)
            + "\n"
        )

    try:
        upload_log_to_github()

    except Exception as e:
        print("GitHub upload failed:", e)

# ==========================
# Telegram Handler
# ==========================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat_id = update.effective_chat.id
    question = update.message.text

    log_event({
        "type": "incoming",
        "chat_id": chat_id,
        "question": question
    })

    history = conversation_history.setdefault(chat_id, [])

    history.append(
        {
            "role": "user",
            "content": question
        }
    )

    system_prompt = """
You are an expert data analyst.

Always answer ONLY the user's LAST message.

If the user requests JSON,
return ONLY valid JSON.

Never use markdown.

Never use ```.

Never explain your answer.

Follow the requested schema exactly.

Do not invent extra keys.

If a schema is provided,
match it exactly.

Return only valid JSON.
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            }
        ] + history[-6:]
    )

    reply = response.choices[0].message.content.strip()

    # ----------------------
    # Robust JSON Parsing
    # ----------------------

    try:
        data = json.loads(reply)

    except Exception:

        start = reply.find("{")
        end = reply.rfind("}")

        if start != -1 and end != -1:

            try:
                data = json.loads(reply[start:end + 1])

            except Exception:
                data = {
                    "answer": reply
                }

        else:

            data = {
                "answer": reply
            }

    # ----------------------
    # Add log_url ONLY when requested
    # ----------------------

    if "log_url" in question.lower():
        data["log_url"] = LOG_URL

    final_reply = json.dumps(
        data,
        ensure_ascii=False
    )

    history.append(
        {
            "role": "assistant",
            "content": final_reply
        }
    )

    if len(history) > 20:
        conversation_history[chat_id] = history[-20:]

    log_event({
        "type": "outgoing",
        "chat_id": chat_id,
        "response": final_reply
    })

    await update.message.reply_text(final_reply)

# ==========================
# Run Bot
# ==========================

def main():

    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("Missing TELEGRAM_BOT_TOKEN")

    if not AIPIPE_TOKEN:
        raise ValueError("Missing AIPIPE_TOKEN")

    app = (
        ApplicationBuilder()
        .token(TELEGRAM_BOT_TOKEN)
        .build()
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message,
        )
    )

    print("Bot Running...")

    app.run_polling()


if __name__ == "__main__":
    main()