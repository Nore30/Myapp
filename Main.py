from fastapi import FastAPI, Request
import requests
import uvicorn
import os

app = FastAPI()

# ==============================
#  MASUKKAN TOKEN BOT DI SINI
# ==============================
TELEGRAM_TOKEN = "8386697150:AAEMLVEUPtozaSjxQJ5dLPNRn9r_dLrOhjo"
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# ==============================
#  ROOT
# ==============================
@app.get("/")
async def root():
    return {"message": "Bot berjalan 🔥"}

# ==============================
#  HEALTH
# ==============================
@app.get("/health")
async def health():
    return {"status": "ok"}

# ==============================
#  WEBHOOK ENDPOINT
# ==============================
@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        # Balasan otomatis
        reply = f"Kamu bilang: {text}"

        requests.get(f"{TELEGRAM_API}/sendMessage", params={
            "chat_id": chat_id,
            "text": reply
        })

    return {"ok": True}

# ==============================
#  SET WEBHOOK MANUAL
# ==============================
@app.get("/set_webhook")
async def set_webhook():
    # Ganti URL kamu sendiri dari Railway
    WEBHOOK_URL = "https://your-railway-url.up.railway.app/webhook"

    r = requests.get(f"{TELEGRAM_API}/setWebhook?url={WEBHOOK_URL}")
    return r.json()

# ==============================
#  RUN LOCAL
# ==============================
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
