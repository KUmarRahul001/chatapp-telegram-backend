import os
import random
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from telegram import Bot
from dotenv import load_dotenv
import threading
import asyncio
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

load_dotenv()

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
bot = Bot(token=TELEGRAM_BOT_TOKEN)

# In-memory user storage: phone -> telegram_id
user_store = {
    # Example: "+918434237052": 7844936105,
}

otp_store = {}  # phone -> (otp, expiry)

OTP_EXPIRY_MINUTES = 5

# Telegram bot async handlers
async def start(update: ContextTypes.DEFAULT_TYPE, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(f"Welcome! Your Telegram user ID is {user_id}. Please register your phone number with the app.")

async def message_handler(update: ContextTypes.DEFAULT_TYPE, context: ContextTypes.DEFAULT_TYPE):
    # Optionally handle messages or registrations
    await update.message.reply_text("Please use the mobile app to register your phone number.")

application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), message_handler))

def run_telegram_bot():
    asyncio.run(application.run_polling())


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "running",
        "message": "Telegram OTP API is live!",
        "available_endpoints": ["/register", "/send_otp", "/verify_otp"]
    })
    
@app.route("/send_otp", methods=["POST"])
def send_otp():
    data = request.json
    phone = data.get("phone")
    if phone not in user_store:
        return jsonify({"status": "error", "reason": "phone_not_registered"}), 400
    telegram_id = user_store[phone]

    otp = str(random.randint(100000, 999999))
    expiry = datetime.now() + timedelta(minutes=OTP_EXPIRY_MINUTES)
    otp_store[phone] = (otp, expiry)

    print(f"DEBUG: OTP for {phone} is {otp}")
    try:
        bot.send_message(chat_id=telegram_id, text=f"Your OTP is: {otp}. It expires in {OTP_EXPIRY_MINUTES} minutes.")
        return jsonify({"status": "sent"})
    except Exception as e:
        return jsonify({"status": "error", "reason": "telegram_send_failed", "details": str(e)}), 500

@app.route("/verify_otp", methods=["POST"])
def verify_otp():
    data = request.json
    phone = data.get("phone")
    otp = data.get("otp")
    record = otp_store.get(phone)

    if record:
        real_otp, expiry = record
        if datetime.now() > expiry:
            del otp_store[phone]
            return jsonify({"status": "error", "reason": "otp_expired"})
        if otp == real_otp:
            del otp_store[phone]
            return jsonify({"status": "verified"})
    return jsonify({"status": "error", "reason": "otp_invalid"})

if __name__ == "__main__":
    thread = threading.Thread(target=run_telegram_bot, daemon=True)
    thread.start()

    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
