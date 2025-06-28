import os
import telebot
from telebot.types import Message
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

# ✅ Telegram Bot Token (Hardcoded)
BOT_TOKEN = '7958998385:AAFgajM3uh6Tuwhjv17a-1itNHUg0xcV1sI'
bot = telebot.TeleBot(BOT_TOKEN)

# 🔐 Google Drive Auth (Using saved credentials.json)
gauth = GoogleAuth()
gauth.LocalWebserverAuth()
drive = GoogleDrive(gauth)

# 🧠 User-wise current Course/Module folders
user_courses = {}
user_modules = {}

# 📁 Create or get folder inside Google Drive
def create_or_get_folder(name, parent_id=None):
    query = f"title='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    folders = drive.ListFile({'q': query}).GetList()
    if folders:
        return folders[0]['id']
    metadata = {'title': name, 'mimeType': 'application/vnd.google-apps.folder'}
    if parent_id:
        metadata['parents'] = [{'id': parent_id}]
    folder = drive.CreateFile(metadata)
    folder.Upload()
    return folder['id']

def get_root_courses_folder():
    return create_or_get_folder("Courses")

@bot.message_handler(commands=['folder'])
def set_folder(message: Message):
    try:
        course_name = message.text.split(" ", 1)[1].strip()
        root_id = get_root_courses_folder()
        course_id = create_or_get_folder(course_name, parent_id=root_id)
        user_courses[message.from_user.id] = course_id
        user_modules.pop(message.from_user.id, None)
        bot.reply_to(message, f"✅ Course set: `{course_name}`", parse_mode='Markdown')
    except:
        bot.reply_to(message, "⚠️ Use: /folder Course Name")

@bot.message_handler(commands=['module'])
def set_module(message: Message):
    user_id = message.from_user.id
    if user_id not in user_courses:
        bot.reply_to(message, "⚠️ Set a course first using /folder")
        return
    try:
        module_name = message.text.split(" ", 1)[1].strip()
        module_id = create_or_get_folder(module_name, parent_id=user_courses[user_id])
        user_modules[user_id] = module_id
        bot.reply_to(message, f"✅ Module set: `{module_name}`", parse_mode='Markdown')
    except:
        bot.reply_to(message, "⚠️ Use: /module Module Name")

@bot.message_handler(content_types=['document', 'video', 'audio', 'photo'])
def upload_file(message: Message):
    user_id = message.from_user.id
    if user_id not in user_modules:
        bot.reply_to(message, "⚠️ Set a module using /module before uploading.")
        return

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
        file_name = "image.jpg"
    else:
        bot.reply_to(message, "❌ Unsupported file type.")
        return

    # Download the file
    downloaded = bot.download_file(file_info.file_path)
    with open(file_name, 'wb') as f:
        f.write(downloaded)

    # Prepare title and description
    caption = message.caption or ""
    title = f"{file_name} | TG:- @Skillneast"
    description = f"{caption}\n\nTG:- @Skillneast"

    # Upload to Google Drive
    gfile = drive.CreateFile({
        'title': title,
        'parents': [{'id': user_modules[user_id]}],
        'description': description
    })
    gfile.SetContentFile(file_name)
    gfile.Upload()
    os.remove(file_name)

    # Share link
    link = f"https://drive.google.com/file/d/{gfile['id']}/view"
    bot.reply_to(message, f"✅ Uploaded: [{title}]({link})", parse_mode='Markdown')

bot.polling()