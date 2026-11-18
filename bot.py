import os
import subprocess
import threading
import time
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

app = Flask(__name__)

@app.route('/')
def home():
    return "CricX Recorder Bot is running 24/7!"

# Render ke environment variable se token uthayega
TOKEN = os.environ.get("BOT_TOKEN")

RECORDING_ACTIVE = False
STREAM_URL = ""
CHAT_ID = None
DURATION_SECONDS = 3600

def record_process():
    global RECORDING_ACTIVE, STREAM_URL, DURATION_SECONDS
    part_num = 1
    
    while RECORDING_ACTIVE:
        output_file = f"match_part_{part_num}.mp4"
        
        ffmpeg_cmd = [
            "ffmpeg", "-i", STREAM_URL,
            "-t", str(DURATION_SECONDS),
            "-c", "copy",
            "-bsf:a", "aac_adtstoasc",
            output_file
        ]
        
        process = subprocess.Popen(
            ffmpeg_cmd, 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL
        )
        
        while process.poll() is None:
            if not RECORDING_ACTIVE:
                process.terminate()
                break
            time.sleep(2)
            
        if not RECORDING_ACTIVE:
            if os.path.exists(output_file):
                os.remove(output_file)
            break
            
        part_num += 1

async def start_record(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global RECORDING_ACTIVE, STREAM_URL, CHAT_ID, DURATION_SECONDS
    args = context.args
    
    if len(args) < 1:
        await update.message.reply_text("❌ Sahi tarika ye hai:\n`/record <m3u8_link> <minutes>`")
        return
        
    if RECORDING_ACTIVE:
        await update.message.reply_text("⚠️ Recording pehle se chal rahi hai!")
        return

    STREAM_URL = args[0]
    
    if len(args) > 1:
        try:
            minutes = int(args[1])
            DURATION_SECONDS = minutes * 60
        except ValueError:
            DURATION_SECONDS = 3600
    else:
        DURATION_SECONDS = 3600

    CHAT_ID = update.effective_chat.id
    RECORDING_ACTIVE = True
    
    await update.message.reply_text(f"🚀 Recording shuru ho gayi hai!\n⏱️ Timer: {DURATION_SECONDS // 60} minutes per part.\nRokne ke liye `/stop` bhejein.")
    
    t = threading.Thread(target=record_process)
    t.daemon = True
    t.start()

async def stop_record(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global RECORDING_ACTIVE
    if RECORDING_ACTIVE:
        RECORDING_ACTIVE = False
        await update.message.reply_text("⏹️ Recording roki ja rahi hai...")
    else:
        await update.message.reply_text("Koi active recording nahi chal rahi hai.")

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, use_reloader=False)

def main():
    if not TOKEN:
        print("ERROR: BOT_TOKEN environment variable not set!")
        return

    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    bot_app = ApplicationBuilder().token(TOKEN).build()
    bot_app.add_handler(CommandHandler("record", start_record))
    bot_app.add_handler(CommandHandler("stop", stop_record))
    
    print("Bot polling started successfully...")
    bot_app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
