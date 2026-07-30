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