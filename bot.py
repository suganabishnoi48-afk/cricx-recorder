import os
import subprocess
import asyncio
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Flask web server taaki Render ki Web Service active rahe
app = Flask(__name__)

@app.route('/')
def home():
    return "CricX Recorder Bot is running 24/7!"

# Telegram Bot Token
TOKEN = "9125619030:AAEG6FMEEqr5IDtgWxZpOl6rZhZPWax4FZ0"

RECORDING_ACTIVE = False
STREAM_URL = ""
CHAT_ID = None
DURATION_SECONDS = 3600

async def record_loop(context: ContextTypes.DEFAULT_TYPE):
    global RECORDING_ACTIVE, STREAM_URL, CHAT_ID, DURATION_SECONDS
    
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
            await asyncio.sleep(5)
            
        if not RECORDING_ACTIVE:
            if os.path.exists(output_file):
                os.remove(output_file)
            break
            
        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            try:
                await context.bot.send_document(
                    chat_id=CHAT_ID,
                    document=open(output_file, "rb"),
                    caption=f"✅ CricXAbhi Match Part {part_num} uploaded successfully!"
                )
            except Exception as e:
                print(f"Upload error: {e}")
            
            os.remove(output_file)
            
        part_num += 1

async def start_record(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global RECORDING_ACTIVE, STREAM_URL, CHAT_ID, DURATION_SECONDS
    args = context.args
    
    if len(args) < 1:
        await update.message.reply_text("❌ Bhai sahi tarika ye hai:\n`/record <m3u8_link> <minutes>`\nExample: `/record https://...m3u8 60`")
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
    
    asyncio.create_task(record_loop(context))

async def stop_record(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global RECORDING_ACTIVE
    if RECORDING_ACTIVE:
        RECORDING_ACTIVE = False
        await update.message.reply_text("⏹️ Recording roki ja rahi hai... Current part upload hone ke baad bot band ho jayega.")
    else:
        await update.message.reply_text("Koi active recording nahi chal rahi hai.")

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, use_reloader=False)

def main():
    # Flask ko alag thread me chalao taaki web service khush rahe
    import threading
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()
    
    # Telegram Bot ko start karo
    bot_app = ApplicationBuilder().token(TOKEN).build()
    bot_app.add_handler(CommandHandler("record", start_record))
    bot_app.add_handler(CommandHandler("stop", stop_record))
    
    print("Bot is starting polling...")
    bot_app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
