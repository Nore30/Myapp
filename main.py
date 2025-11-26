from fastapi import FastAPI, Request
import requests
import os
import uvicorn
from huggingface_hub import InferenceClient

# ======================================================
# 1. Konfigurasi Awal
# ======================================================

# Inisialisasi Aplikasi FastAPI
app = FastAPI()

# Ambil Token dari Environment Variables
# Di Railway/Heroku/platform cloud lain, ini harus disetel di settings/vars
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")  

if not TELEGRAM_TOKEN or not HF_TOKEN:
    print("WARNING: TELEGRAM_TOKEN atau HF_TOKEN belum disetel!")

# URL API Telegram
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# Model Inference Client Hugging Face
# Pastikan HF_TOKEN sudah ada agar koneksi berhasil
try:
    hf_client = InferenceClient(api_key=HF_TOKEN)
except Exception as e:
    print(f"Error in initializing InferenceClient: {e}")
    hf_client = None

# URL WEBHOOK (Ganti dengan URL aplikasi Anda yang sudah di-deploy)
# Contoh: WEBHOOK_URL = "https://nama-aplikasi-anda.up.railway.app/webhook"
WEBHOOK_URL = os.getenv("WEBHOOK_BASE_URL", "https://your-default-url.com") + "/webhook"


# ======================================================
# 2. Endpoint Utama
# ======================================================

@app.get("/")
async def root():
    """Endpoint untuk cek status dasar."""
    return {"message": "Bot aktif 🔥", "status": "running"}

@app.get("/health")
async def health():
    """Endpoint untuk monitoring kesehatan aplikasi."""
    return {"status": "ok", "hf_client_ready": hf_client is not None}

# ======================================================
# 3. Webhook (Menerima Pesan Telegram)
# ======================================================
@app.post("/webhook")
async def telegram_webhook(request: Request):
    """Menerima dan memproses pesan dari Telegram."""
    try:
        data = await request.json()
    except Exception as e:
        print(f"Error parsing JSON: {e}")
        return {"ok": True}

    # Pastikan pesan masuk
    if "message" not in data:
        return {"ok": True}

    chat_id = data["message"]["chat"]["id"]
    text = data["message"].get("text", "")

    # Logika Pemrosesan Teks via Hugging Face
    if text and hf_client:
        try:
            # PENTING: Prompt untuk instruksi perubahan/penghalusan
            prompt = (
                f"Perhalus melodi humming ini agar jadi indah dan tidak putus-putus:\n"
                f"{text}\n"
                f"Melodi yang diperhalus:"
            )

            response = hf_client.text_generation(
                model="meta-llama/Llama-3.2-1B-Instruct",
                prompt=prompt,
                max_new_tokens=150,  # Ditingkatkan sedikit
                temperature=0.8
            )

            generated_text = response.strip()

        except Exception as e:
            # Tangani error saat berkomunikasi dengan HF
            generated_text = f"❌ Error pemrosesan AI: Terjadi kesalahan saat menghubungi model AI. Detail: {e}"

        # Kirim hasilnya kembali ke Telegram
        requests.get(
            f"{TELEGRAM_API}/sendMessage",
            params={"chat_id": chat_id, "text": generated_text}
        )
    elif not hf_client:
        requests.get(
            f"{TELEGRAM_API}/sendMessage",
            params={"chat_id": chat_id, "text": "❌ Bot sedang tidak dapat memproses AI (HF Client Error)."}
        )


    return {"ok": True}

# ======================================================
# 4. Set Webhook
# ======================================================
@app.get("/set_webhook")
async def set_webhook():
    """Endpoint untuk mendaftarkan URL aplikasi ini ke Telegram."""
    if not TELEGRAM_TOKEN:
        return {"ok": False, "message": "TELEGRAM_TOKEN tidak disetel."}
        
    try:
        # Kirim permintaan ke Telegram untuk menyetel webhook
        url = f"{TELEGRAM_API}/setWebhook?url={WEBHOOK_URL}"
        response = requests.get(url).json()
        return response
    except Exception as e:
        return {"ok": False, "message": f"Gagal menghubungi Telegram API: {e}"}


# ======================================================
# 5. Local Test/Running
# ======================================================
if __name__ == "__main__":
    # Untuk menjalankan aplikasi secara lokal
    port = int(os.environ.get("PORT", 8000))
    print(f"Aplikasi berjalan di http://0.0.0.0:{port}")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port
    )
    
