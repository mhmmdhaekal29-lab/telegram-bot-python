import logging
import os
import json
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters
)

from core import get_bot_reply
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

# =============================
# LOGGING
# =============================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

# =============================
# ENVIRONMENT VARIABLES
# =============================
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not TOKEN:
    print("❌ TELEGRAM_BOT_TOKEN belum diset")
    exit()

if not GROQ_API_KEY:
    print("❌ GROQ_API_KEY belum diset")
    exit()

os.environ["GROQ_API_KEY"] = GROQ_API_KEY

# =============================
# INISIALISASI GROQ AI
# =============================
llm = ChatGroq(
    model_name="llama-3.1-8b-instant",
    temperature=0.3
)

# =============================
# MEMORY SINGKAT PER CHAT
# =============================
conversation_history = {}  # {chat_id: [{"user": msg, "bot": msg}, ...]}

# =============================
# COMMAND /START
# =============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    conversation_history[chat_id] = []  # reset history

    await update.message.reply_text(
        "Halo 👋 Saya *Hi Snack* 🍰\n"
        "Silakan ketik pertanyaanmu atau ingin memesan produk 😊",
        parse_mode="Markdown"
    )

# =============================
# HANDLE PESAN USER
# =============================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_text = update.message.text

    if chat_id not in conversation_history:
        conversation_history[chat_id] = []

    # 1️⃣ Jawab dari core.py
    reply = get_bot_reply(user_text)

    # 2️⃣ Jika core.py tidak paham → lempar ke Groq AI
    if "belum memahami" in reply.lower() or "tidak tahu" in reply.lower():
        try:
            # Ambil 3 history terakhir untuk konteks
            history_text = ""
            for h in conversation_history[chat_id][-3:]:
                history_text += f"User: {h['user']}\nBot: {h['bot']}\n"

            prompt = ChatPromptTemplate.from_messages([
                (
                    "system",
                    """
Kamu adalah admin Hi Snack.
Tugasmu:
1. Tangkap produk, jumlah, alamat, dan nomor telepon jika user ingin memesan.
2. Jika informasi kurang lengkap, tanyakan secara singkat dan ramah.
3. Jika user bertanya tentang menu, paket, harga, atau jam buka, jawab sesuai topik.
4. Gunakan bahasa WhatsApp, ramah, singkat, jelas.
5. Jangan mengulang jawaban default jika user sudah menyebut produk atau jumlah.
6. Fokus hanya pada Hi Snack.
"""
                ),
                ("human", "{history}\nUser: {input}")
            ])

            chain = prompt | llm
            ai_response = chain.invoke({
                "input": user_text,
                "history": history_text
            })

            reply = ai_response.content

        except Exception as e:
            logging.error("Groq AI Error: %s", e)
            reply = (
                "Maaf kak 🙏 sistem Hi Snack sedang sibuk.\n"
                "Bisa ditanyakan lagi sebentar ya 😊"
            )

    # Simpan history
    conversation_history[chat_id].append({
        "user": user_text,
        "bot": reply
    })

    await update.message.reply_text(reply)

# =============================
# MAIN PROGRAM
# =============================
if __name__ == "__main__":
    print("🤖 Bot Hi Snack sedang dijalankan...")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(
        MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    )

    app.run_polling()
