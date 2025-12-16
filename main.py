import telebot
from background import keep_alive
import re
import json
import os
from datetime import datetime

# --- إعدادات البوت والمدراء ---
TOKEN = "8172386548:AAEBXoaZ-44Q9vHlpWddVEpqMepa4X_71Yk"
ADMIN_IDS = [667318916, 462652633] # أنت وياسر

bot = telebot.TeleBot(TOKEN)
HISTORY_FILE = "chat_history.json"

# --- دوال السجل ---
def load_history():
    if not os.path.exists(HISTORY_FILE): return {}
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f: return json.load(f)
    except: return {}

def save_message(user_id, sender_name, text, is_admin=False):
    history = load_history()
    user_id = str(user_id)
    if user_id not in history: history[user_id] = []
    
    time_now = datetime.now().strftime("%Y-%m-%d %H:%M")
    icon = "👮‍♂️" if is_admin else "👤"
    entry = f"{time_now} | {icon} {sender_name}: {text}"
    
    history[user_id].append(entry)
    if len(history[user_id]) > 50: history[user_id] = history[user_id][-50:]
        
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=4)

# --- 1. ترحيب ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "👋 أهلاً بك! \nأرسل رسالتك وسأرد عليك قريباً.")

# --- 2. السجل ---
@bot.message_handler(commands=['history'])
def get_user_history(message):
    if message.chat.id not in ADMIN_IDS: return
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ اكتب: `/history الايدي`", parse_mode="Markdown")
            return
        target_id = parts[1]
        history = load_history()
        if target_id in history and history[target_id]:
            last_msgs = history[target_id][-15:] 
            msg_text = f"📜 **سجل {target_id}:**\n\n" + "\n".join(last_msgs)
            bot.reply_to(message, msg_text)
        else:
            bot.reply_to(message, "📭 السجل فارغ.")
    except Exception as e:
        bot.reply_to(message, f"خطأ: {e}")

# --- 3. استلام الرسائل ---
@bot.message_handler(func=lambda message: message.chat.id not in ADMIN_IDS, content_types=['text', 'photo', 'voice', 'video', 'sticker', 'document'])
def forward_to_admins(message):
    user_id = message.chat.id
    user_name = message.chat.first_name or "مجهول"
    
    if message.from_user.username:
        username = f"@{message.from_user.username}"
    else:
        username = "لا يوجد"

    msg_content = message.text if message.content_type == 'text' else f"[{message.content_type}]"
    save_message(user_id, user_name, msg_content, is_admin=False)
    
    info_text = f"📩 **رسالة جديدة**\n👤 الاسم: {user_name}\n🔗 يوزر: {username}\n🆔 ID: `{user_id}`\n\n"
    
    for admin in ADMIN_IDS:
        try:
            if message.content_type == 'text':
                bot.send_message(admin, info_text + f"📝 النص:\n{message.text}", parse_mode="Markdown")
            else:
                bot.send_message(admin, info_text + f"📎 أرسل ملف: {message.content_type}", parse_mode="Markdown")
                bot.forward_message(admin, user_id, message.message_id)
        except: pass

# --- 4. الرد الذكي ---
@bot.message_handler(content_types=['text', 'photo', 'voice', 'sticker'], func=lambda m: m.chat.id in ADMIN_IDS and m.reply_to_message)
def admin_reply(message):
    try:
        # البحث عن الآيدي في الرسالة القديمة
        original_text = message.reply_to_message.text or message.reply_to_message.caption or ""
        search_id = re.search(r"ID: `(\d+)`", original_text) or re.search(r"ID: (\d+)", original_text)
        
        if search_id:
            user_id = search_id.group(1)
            replier_name = message.from_user.first_name
            replier_id = message.from_user.id
            
            # حفظ الرد
            reply_content = message.text if message.content_type == 'text' else f"[{message.content_type}]"
            save_message(user_id, replier_name, reply_content, is_admin=True)

            # إرسال للمستخدم
            if message.content_type == 'text':
                bot.send_message(user_id, f"👮‍♂️ رد الإدارة:\n\n{message.text}")
            elif message.content_type == 'photo':
                bot.send_photo(user_id, message.photo[-1].file_id, caption=message.caption)
            elif message.content_type == 'voice':
                bot.send_voice(user_id, message.voice.file_id)
            elif message.content_type == 'sticker':
                bot.send_sticker(user_id, message.sticker.file_id)
            
            # 🔥 التعديل هنا: نكتب الآيدي في رسالة التأكيد عشان تقدرون تردون عليها بعدين 🔥
            bot.reply_to(message, f"✅ تم الإرسال.\n🆔 ID: `{user_id}`", parse_mode="Markdown")
            
            # تنبيه المدير الآخر
            for admin in ADMIN_IDS:
                if admin != replier_id:
                    try:
                        bot.send_message(admin, f"⚠️ **تنبيه:**\nالمشرف {replier_name} رد على {user_id}.", parse_mode="Markdown")
                    except: pass
        else:
            bot.reply_to(message, "❌ ما لكيت الآيدي! \n⚠️ **ملاحظة:** لازم ترد على الرسالة اللي فيها كلمة (ID: الأرقام).")

    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

keep_alive()
bot.infinity_polling()
