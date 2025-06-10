import os
import json
import gspread
import telebot
from datetime import datetime
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
SHEET_ID = os.getenv("SHEET_ID")
GOOGLE_CREDS_RAW = os.getenv("GOOGLE_CREDS_RAW")
SOURCE_CHANNEL_ID = int(os.getenv("SOURCE_CHANNEL_ID", "0"))

if not all([BOT_TOKEN, SHEET_ID, GOOGLE_CREDS_RAW, SOURCE_CHANNEL_ID]):
    raise ValueError("Missing one or more required environment variables.")

# Setup Google Sheet client
creds_path = "/tmp/google-creds.json"
with open(creds_path, "w") as f:
    f.write(GOOGLE_CREDS_RAW)

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID).worksheet("BOT Community Partner")
print(f"📄 Sheet aktif: {sheet.title}")

# Setup Telegram bot
bot = telebot.TeleBot(BOT_TOKEN)

# Helper: get list grup aktif
def get_active_groups():
    records = sheet.get_all_records()
    return [
        int(row["Group ID"])
        for row in records
        if row.get("Group ID") and row.get("Status", "").strip().lower() == "aktif"
    ]

# Auto add group ke sheet
@bot.my_chat_member_handler()
def auto_add_group(event):
    if event.new_chat_member.status in ['member', 'administrator']:
        chat_id = event.chat.id
        chat_name = event.chat.title or "Unnamed Group"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        existing = sheet.get_all_records()
        updated = False

        for idx, row in enumerate(existing, start=2):
            if row.get("Group Name", "").strip() == chat_name.strip():
                sheet.update_cell(idx, 1, str(chat_id))
                sheet.update_cell(idx, 4, "Aktif")
                print(f"🔁 Group ID diperbarui: {chat_name} (ID baru: {chat_id})")
                updated = True
                break

        if not updated:
            new_row = [str(chat_id), chat_name, "", "Aktif"]
            target_row = len(existing) + 2
            sheet.insert_row(new_row, target_row)
            print(f"🆕 Grup baru ditambahkan ke baris {target_row}: {new_row}")

# Forward pesan dari channel (tanpa tag "forwarded from")
@bot.channel_post_handler(content_types=['text', 'photo', 'video', 'document'])
def blast_message(message):
    if message.chat.id != SOURCE_CHANNEL_ID:
        print(f"⛔ Channel tidak diizinkan: {message.chat.id}")
        return

    active_groups = get_active_groups()
    print(f"🚀 Blast ke {len(active_groups)} grup aktif...")

    for group_id in active_groups:
        try:
            if message.content_type == 'text':
                bot.send_message(group_id, message.text, entities=message.entities)
            elif message.content_type == 'photo':
                bot.send_photo(group_id, message.photo[-1].file_id, caption=message.caption, caption_entities=message.caption_entities)
            elif message.content_type == 'video':
                bot.send_video(group_id, message.video.file_id, caption=message.caption, caption_entities=message.caption_entities)
            elif message.content_type == 'document':
                bot.send_document(group_id, message.document.file_id, caption=message.caption, caption_entities=message.caption_entities)

            print(f"✅ Berhasil kirim ke {group_id} ({message.content_type})")
        except Exception as e:
            print(f"❌ Gagal kirim ke {group_id}: {e}")

# Start bot
print("🤖 Bot aktif... Menunggu pesan dari channel yang diizinkan...")
bot.infinity_polling()
