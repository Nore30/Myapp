from fastapi import FastAPI, Request
import requests
import uvicorn
import os

app = FastAPI()

# ==============================
# KONFIGURASI
# ==============================
TELEGRAM_TOKEN = "8386697150:AAEMLVEUPtozaSjxQJ5dLPNRn9r_dLrOhjo"
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# GANTI dengan URL Railway akun kamu
WEBHOOK_URL = "https://web-production-6187d.up.railway.app/webhook"


# ==============================
# ROOT
# ==============================
@app.get("/")
async def root():
    return {"message": "Bot Telegram aktif 🔥"}


# ==============================
# HEALTH
# ==============================
@app.get("/health")
async def health():
    return {"status": "ok"}


# ==============================
# WEBHOOK
# ==============================
@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        reply = f"Kamu bilang: {text}"

        requests.get(
            f"{TELEGRAM_API}/sendMessage",
            params={"chat_id": chat_id, "text": reply}
        )

    return {"ok": True}


# ==============================
# SET WEBHOOK
# ==============================
@app.get("/set_webhook")
async def set_webhook():
    r = requests.get(f"{TELEGRAM_API}/setWebhook?url={WEBHOOK_URL}")
    return r.json()


# ==============================
# RUN LOCAL
# ==============================
if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000))
    )
