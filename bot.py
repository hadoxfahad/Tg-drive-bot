import os
import json
import telebot
from telebot.types import Message
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from oauth2client.service_account import ServiceAccountCredentials

# ✅ Telegram Bot Token (HARD CODED)
BOT_TOKEN = "7958998385:AAFgajM3uh6Tuwhjv17a-1itNHUg0xcV1sI"

# ✅ Google Drive Service Account Credentials (HARD CODED)
CREDENTIAL_JSON = {
 "type": "service_account",
 "project_id": "adminneast",
 "private_key_id": "xxxx",
 "private_key": "-----BEGIN PRIVATE KEY-----\nYOUR-PRIVATE-KEY-HERE\n-----END PRIVATE KEY-----\n",
 "client_email": "your-service-email@adminneast.iam.gserviceaccount.com",
 "client_id": "12345678901234567890",
 "auth_uri": "https://accounts.google.com/o/oauth2/auth",
 "token_uri": "https://oauth2.googleapis.com/token",
 "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
 "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/your-service-email%40adminneast.iam.gserviceaccount.com"
}

# ✅ Authenticate Google Drive
scope = ['https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_dict(CREDENTIAL_JSON, scope)
gauth = GoogleAuth()
gauth.credentials = credentials
drive = GoogleDrive(gauth)

bot = telebot.TeleBot(BOT_TOKEN)

# 🔁 User-session storage
user_courses = {}
user_modules = {}

# 📁 Create or get folder inside Drive
def create_or_get_folder(name, parent_id=None):
    query = f"title='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    file_list = drive.ListFile({'q': query}).GetList()
    if file_list:
        return file_list[0]['id']
    metadata = {'title': name, 'mimeType': 'application/vnd.google-apps.folder'}
    if parent_id:
        metadata['parents'] = [{'id': parent_id}]
    folder = drive.CreateFile(metadata)
    folder.Upload()
    return folder['id']

def get_root_folder():
    return create_or_get_folder("Courses")

@bot.message_handler(commands=['folder'])
def handle_folder(message: Message):
    try:
        name = message.text.split(" ", 1)[1].strip()
        root = get_root_folder()
        folder_id = create_or_get_folder(name, root)
        user_courses[message.from_user.id] = folder_id
        user_modules.pop(message.from_user.id, None)
        bot.reply_to(message, f"✅ Course set: `{name}`", parse_mode="Markdown")
    except:
        bot.reply_to(message, "⚠️ Use: /folder Course Name")

@bot.message_handler(commands=['module'])
def handle_module(message: Message):
    uid = message.from_user.id
    if uid not in user_courses:
        return bot.reply_to(message, "⚠️ Set course first using /folder")
    try:
        name = message.text.split(" ", 1)[1].strip()
        mod_id = create_or_get_folder(name, user_courses[uid])
        user_modules[uid] = mod_id
        bot.reply_to(message, f"✅ Module set: `{name}`", parse_mode="Markdown")
    except:
        bot.reply_to(message, "⚠️ Use: /module Module Name")

@bot.message_handler(content_types=['document', 'video', 'audio', 'photo'])
def handle_upload(message: Message):
    uid = message.from_user.id
    if uid not in user_modules:
        return bot.reply_to(message, "⚠️ Use /module to select module folder")

    file_name = "file"
    file_info = None
    if message.document:
        file_info = bot.get_file(message.document.file_id)
        file_name = message.document.file_name
    elif message.video:
        file_info = bot.get_file(message.video.file_id)
        file_name = message.video.file_name or "video.mp4"
    elif message.audio:
        file_info = bot.get_file(message.audio.file_id)
        file_name = message.audio.file_name or "audio.mp3"
    elif message.photo:
        file_info = bot.get_file(message.photo[-1].file_id)
        file_name = "photo.jpg"
    else:
        return bot.reply_to(message, "❌ Unsupported file type.")

    # Download file
    downloaded = bot.download_file(file_info.file_path)
    with open(file_name, 'wb') as f:
        f.write(downloaded)

    # Prepare title and description
    caption = message.caption or ""
    desc = f"{caption}\n\nTG:- @Skillneast"

    # Upload to Drive
    gfile = drive.CreateFile({
        'title': file_name,
        'parents': [{'id': user_modules[uid]}],
        'description': desc
    })
    gfile.SetContentFile(file_name)
    gfile.Upload()
    os.remove(file_name)

    link = f"https://drive.google.com/file/d/{gfile['id']}/view"
    bot.reply_to(message, f"✅ Uploaded: [{file_name}]({link})", parse_mode="Markdown")

# ✅ Bot Start
bot.polling()
