from fastapi import FastAPI, Request
import requests
import uvicorn
import os

app = FastAPI()

# ======================================================
# TOKEN BOT TELEGRAM
# ======================================================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")  # ambil dari env
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# URL Railway kamu
WEBHOOK_URL = "https://web-production-6187d.up.railway.app/webhook"


# ======================================================
# ROOT
# ======================================================
@app.get("/")
async def root():
    return {"message": "API berjalan 🔥 Bot sudah online"}


# ======================================================
# HEALTH
# ======================================================
@app.get("/health")
async def health():
    return {"status": "ok"}


# ======================================================
# WEBHOOK — menerima update Telegram
# ======================================================
@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()

    message = data.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")

    if chat_id:
        reply = f"Kamu bilang: {text}"

        requests.get(
            f"{TELEGRAM_API}/sendMessage",
            params={"chat_id": chat_id, "text": reply}
        )

    return {"ok": True}


# ======================================================
# SET WEBHOOK
# ======================================================
@app.get("/set_webhook")
async def set_webhook():
    url = f"{TELEGRAM_API}/setWebhook?url={WEBHOOK_URL}"
    return requests.get(url).json()


# ======================================================
# RUN LOCAL
# ======================================================
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
