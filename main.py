from fastapi import FastAPI, Request
import requests
import os
import uvicorn

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

# --- URL & MODEL BARU ---
# URL API Hugging Face standar (paling stabil untuk model ASR dan Falcon)
HF_API_BASE_URL = "https://api-inference.huggingface.co/models" 
# Model LLM yang stabil
HF_MODEL_LLM = "tiiuae/falcon-7b-instruct" 
# Model ASR terbaik untuk lirik
HF_MODEL_ASR = "openai/whisper-tiny" 
# ------------------------

WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "https://your-default-url.com")
WEBHOOK_URL = WEBHOOK_BASE_URL + "/webhook"

# Header Otentikasi untuk API Hugging Face
HF_HEADERS = {"Authorization": f"Bearer {HF_TOKEN}"} if HF_TOKEN else {}

# ======================================================
# 2. Fungsi Pembantu
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

def run_hf_inference(model_id, data, is_audio=False):
    """Mengirim request POST langsung ke Hugging Face Inference API."""
    
    url = f"{HF_API_BASE_URL}/{model_id}"
    
    if is_audio:
        response = requests.post(url, headers=HF_HEADERS, data=data)
        
        if response.status_code == 200:
            return response.json().get('text', '')
        else:
            raise Exception(f"HF ASR Error (Code {response.status_code}): {response.text}")
    
    else:
        payload = {
            "inputs": data,
            "parameters": {
                "max_new_tokens": 500, # Diperpanjang untuk lirik
                "temperature": 0.5     # Diturunkan agar lebih fokus pada chord
            }
        }
        response = requests.post(url, headers=HF_HEADERS, json=payload)
        
        if response.status_code == 200:
            return response.json()[0]['generated_text']
        else:
            raise Exception(f"HF LLM Error (Code {response.status_code}): {response.text}")


# ======================================================
# 3. Webhook (Menerima Pesan Telegram)
# ======================================================
@app.post("/webhook")
async def telegram_webhook(request: Request):
    # ... (Penanganan data masuk tetap sama)
    try:
        data = await request.json()
    except Exception:
        return {"ok": True}

    if "message" not in data:
        return {"ok": True}

    message = data["message"]
    chat_id = message["chat"]["id"]
    input_text = ""
    
    if not HF_TOKEN:
        send_telegram_message(chat_id, "❌ Koneksi HF gagal: HF_TOKEN belum disetel.")
        return {"ok": True}
    
    # --- A. Mendapatkan Teks Input (dari Teks atau Audio) ---
    
    if "text" in message:
        input_text = message["text"]
        send_telegram_message(chat_id, f"Memproses teks Anda ({input_text}) menjadi lirik dan chord...")
    
    elif "voice" in message:
        
        send_telegram_message(chat_id, "⏳ Menerima audio... sedang ditranskripsi menjadi lirik.")
        
        try:
            # Logika Transkripsi Audio (ASR)
            voice_data = message["voice"]
            file_id = voice_data["file_id"]

            resp = requests.get(f"{TELEGRAM_API}/getFile?file_id={file_id}").json()
            file_path = resp["result"]["file_path"]
            
            audio_url = f"{TELEGRAM_FILE_API}/{file_path}"
            audio_content = requests.get(audio_url).content
            
            # Panggil fungsi inferensi ASR untuk mendapatkan lirik
            transcribed_text = run_hf_inference(HF_MODEL_ASR, audio_content, is_audio=True)
            input_text = transcribed_text.strip()
            
            send_telegram_message(chat_id, f"✅ Transkripsi lirik berhasil. Teks: *{input_text}*.\nSekarang diproses untuk menentukan chord...")
            
        except Exception as e:
            error_msg = f"❌ Gagal memproses audio. Detail: {e}"
            send_telegram_message(chat_id, error_msg)
            return {"ok": True}


    # --- B. Logika LLM: Mengubah Teks menjadi Lirik dan Chord ---
    
    if input_text:
        try:
            # Prompt yang dioptimalkan untuk menghasilkan Chord dan Lirik
            prompt = (
                f"Anda adalah seorang transkrip musik profesional. Tugas Anda adalah menentukan chord yang paling sesuai "
                f"dengan melodi yang dinyanyikan/diucapkan dalam lirik ini. Tambahkan urutan chord gitar sederhana (misal: C, G, Am, F) "
                f"di atas setiap baris lirik yang sudah disempurnakan. \n"
                f"Lirik hasil transkripsi: {input_text}\n"
                f"Format Output (Chord dan Lirik):"
            )

            generated_text = run_hf_inference(HF_MODEL_LLM, prompt, is_audio=False)
            generated_text = generated_text.strip()

        except Exception as e:
            generated_text = f"❌ Error pemrosesan LLM: Gagal menghubungi model {HF_MODEL_LLM}. Detail: {e}"

        send_telegram_message(chat_id, generated_text)
        
    return {"ok": True}


# ======================================================
# 4. Endpoints Info dan Set Webhook (Tetap sama)
# ======================================================
@app.get("/")
async def root():
    return {"message": f"Bot aktif 🔥 Menggunakan model LLM: {HF_MODEL_LLM}, ASR: {HF_MODEL_ASR}", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "ok", "hf_token_set": HF_TOKEN is not None}

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
    
