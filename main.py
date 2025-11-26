from fastapi import FastAPI, Request
import requests
import os
import uvicorn
from huggingface_hub import InferenceClient

# ======================================================
# 1. Konfigurasi Awal & Model
# ======================================================

app = FastAPI()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")  

if not TELEGRAM_TOKEN or not HF_TOKEN:
    print("WARNING: TELEGRAM_TOKEN atau HF_TOKEN belum disetel!")

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
TELEGRAM_FILE_API = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}"

# Model AI untuk Penghalusan Teks (Diganti ke Mistral untuk stabilitas)
HF_MODEL_LLM = "mistralai/Mistral-7B-Instruct-v0.2" 
# Model AI untuk Transkripsi Audio
HF_MODEL_ASR = "openai/whisper-tiny"

# --- LOGIKA INFERENCET CLIENT DAN DEBUGGING KONEKSI ---
hf_client = None
try:
    if HF_TOKEN:
        # Panggil InferenceClient hanya jika token ditemukan
        hf_client = InferenceClient(api_key=HF_TOKEN)
        
        # UJI KONEKSI SEDERHANA: Coba panggil model yang sangat kecil
        test_result = hf_client.text_generation(
            model="hf-internal-testing/tiny-random-falcon",
            prompt="Hello",
            max_new_tokens=1
        )
        print("✅ HF Client Test Berhasil. Koneksi API berfungsi.")
    else:
        print("❌ HF_TOKEN TIDAK DITEMUKAN DI LINGKUNGAN.")

except Exception as e:
    hf_client = None
    print(f"❌ Error fatal saat inisialisasi InferenceClient dan tes koneksi: {e}")
# -----------------------------------------------------------------------

WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "https://your-default-url.com")
WEBHOOK_URL = WEBHOOK_BASE_URL + "/webhook"


# ======================================================
# 2. Fungsi Pembantu: Mengirim Pesan
# ======================================================
def send_telegram_message(chat_id, text):
    """Fungsi sederhana untuk mengirim pesan ke Telegram."""
    try:
        requests.get(
            f"{TELEGRAM_API}/sendMessage",
            params={"chat_id": chat_id, "text": text}
        )
    except Exception as e:
        print(f"Failed to send message: {e}")


# ======================================================
# 3. Webhook (Menerima Pesan Telegram)
# ======================================================
@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
    except Exception:
        return {"ok": True}

    if "message" not in data:
        return {"ok": True}

    message = data["message"]
    chat_id = message["chat"]["id"]
    
    input_text = ""
    
    # --- A. Mendapatkan Teks Input (dari Teks atau Audio) ---
    
    if "text" in message:
        input_text = message["text"]
    
    elif "voice" in message and hf_client:
        
        send_telegram_message(chat_id, "⏳ Menerima senandung Anda... sedang ditranskripsi menjadi teks.")
        
        try:
            voice_data = message["voice"]
            file_id = voice_data["file_id"]

            resp = requests.get(f"{TELEGRAM_API}/getFile?file_id={file_id}").json()
            file_path = resp["result"]["file_path"]
            
            audio_url = f"{TELEGRAM_FILE_API}/{file_path}"
            audio_content = requests.get(audio_url).content
            
            transcription_result = hf_client.automatic_speech_recognition(
                model=HF_MODEL_ASR,
                data=audio_content
            )
            
            input_text = transcription_result.get('text', '').strip()
            
            send_telegram_message(chat_id, f"✅ Transkripsi berhasil. Teks: *{input_text}*.\nSekarang diproses untuk penghalusan melodi...")
            
        except Exception as e:
            error_msg = f"❌ Gagal memproses audio dengan {HF_MODEL_ASR}. Detail: {e}"
            send_telegram_message(chat_id, error_msg)
            return {"ok": True}


    # --- B. Logika LLM: Memperhalus Teks Input ---
    
    if input_text and hf_client:
        try:
            # Prompt yang dioptimalkan untuk 'Melodi Indah'
            prompt = (
                f"Anda adalah komposer musik AI. Perhalus melodi humming/siulan ini menjadi melodi indah yang merdu, "
                f"berikan output hanya dalam bentuk notasi musik sederhana atau urutan humming yang diperbaiki. \n"
                f"Melodi asli: {input_text}\n"
                f"Melodi yang diperindah:"
            )

            response = hf_client.text_generation(
                model=HF_MODEL_LLM, 
                prompt=prompt,
                max_new_tokens=200, 
                temperature=0.8
            )
            
            generated_text = response.strip()

        except Exception as e:
            generated_text = f"❌ Error pemrosesan LLM: Gagal menghubungi model {HF_MODEL_LLM}. Detail: {e}"

        send_telegram_message(chat_id, generated_text)
        
    elif not hf_client:
        send_telegram_message(chat_id, "❌ Bot sedang tidak dapat memproses AI. Koneksi Hugging Face gagal saat startup.")
        
    return {"ok": True}


# ======================================================
# 4. Endpoints Info dan Set Webhook
# ======================================================
@app.get("/")
async def root():
    return {"message": f"Bot aktif 🔥 Menggunakan model LLM: {HF_MODEL_LLM}, ASR: {HF_MODEL_ASR}", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "ok", "hf_client_ready": hf_client is not None}

@app.get("/set_webhook")
async def set_webhook():
    if not TELEGRAM_TOKEN:
        return {"ok": False, "message": "TELEGRAM_TOKEN tidak disetel."}
        
    try:
        url = f"{TELEGRAM_API}/setWebhook?url={WEBHOOK_URL}"
        response = requests.get(url).json()
        return response
    except Exception as e:
        return {"ok": False, "message": f"Gagal menghubungi Telegram API: {e}"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Aplikasi berjalan di http://0.0.0.0:{port}")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port
    )
