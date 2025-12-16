import telebot
from telebot import types
from background import keep_alive
import re
import json
import os
from datetime import datetime

# --- إعدادات البوت والمدراء ---
TOKEN = "8172386548:AAEBXoaZ-44Q9vHlpWddVEpqMepa4X_71Yk"
ADMIN_IDS = [667318916, 462652633]

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
    
    # تنظيف الاسم
    sender_name = sender_name.replace(":", "").replace("|", "")
    
    entry = f"{time_now} | {icon} {sender_name}: {text}"
    
    history[user_id].append(entry)
    if len(history[user_id]) > 50: history[user_id] = history[user_id][-50:]
        
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=4)

# 🔥 دالة ذكية تجيب أحدث اسم تم حفظه للشخص 🔥
def get_customer_name(user_id, history):
    user_id = str(user_id)
    if user_id in history:
        # نبحث من الأخير للأول (عكسي) عشان نلقى أحدث اسم
        for msg in reversed(history[user_id]):
            if "👤" in msg:
                try:
                    return msg.split('| 👤')[1].split(':')[0].strip()
                except: pass
    return "غير معروف"

# --- 1. ترحيب ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "👋 أهلاً بك! \nأرسل رسالتك وسأرد عليك قريباً.")

# --- 2. لوحة التحكم ---
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.chat.id not in ADMIN_IDS: return
    show_admin_menu(message.chat.id)

def show_admin_menu(chat_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("📬 لم يتم الرد", callback_data="no_reply")
    btn2 = types.InlineKeyboardButton("🕒 آخر 5 نشطين", callback_data="recent_users")
    btn3 = types.InlineKeyboardButton("📊 الإحصائيات", callback_data="stats")
    btn4 = types.InlineKeyboardButton("🟢 حالة السيرفر", callback_data="status")
    btn_close = types.InlineKeyboardButton("❌ إغلاق", callback_data="close")
    
    markup.add(btn1, btn2)
    markup.add(btn3, btn4)
    markup.add(btn_close)
    
    bot.send_message(chat_id, "🛠 **لوحة تحكم الإدارة:**\nاختر من القائمة أدناه:", reply_markup=markup)

# --- 3. معالج الأزرار ---
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.message.chat.id not in ADMIN_IDS: return

    # >> زر: لم يتم الرد
    if call.data == "no_reply":
        history = load_history()
        unanswered = []
        for uid, msgs in history.items():
            if msgs and "👤" in msgs[-1]: 
                name = get_customer_name(uid, history)
                unanswered.append(f"• {name}\n🆔 `{uid}`")
        
        if unanswered:
            text = "📬 **قائمة الرسائل التي تنتظر الرد:**\n\n" + "\n".join(unanswered)
            bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
        else:
            bot.answer_callback_query(call.id, "🎉 ممتاز! الكل تم الرد عليه.")

    # >> زر: آخر 5 مستخدمين
    elif call.data == "recent_users":
        history = load_history()
        if not history:
            bot.answer_callback_query(call.id, "السجل فارغ.")
            return

        sorted_users = sorted(history.keys(), key=lambda k: history[k][-1].split('|')[0], reverse=True)[:5]
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        for uid in sorted_users:
            display_name = get_customer_name(uid, history)
            # تنسيق الزر: الاسم واليوزر | الايدي
            button_text = f"{display_name} | {uid}"
            markup.add(types.InlineKeyboardButton(button_text, callback_data=f"hist_{uid}"))
        
        markup.add(types.InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="back_home"))
        
        bot.edit_message_text("🕒 **آخر 5 أشخاص:**\n(اضغط على الاسم لفتح السجل)", call.message.chat.id, call.message.message_id, reply_markup=markup)

    # >> زر: الرجوع
    elif call.data == "back_home":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        show_admin_menu(call.message.chat.id)

    # >> زر: عرض السجل
    elif call.data.startswith("hist_"):
        user_id = call.data.split("_")[1]
        history = load_history()
        if user_id in history:
            name = get_customer_name(user_id, history)
            last_msgs = history[user_id][-10:]
            msg_text = f"📜 **سجل: {name}**\n🆔 ID: `{user_id}`\n\n" + "\n".join(last_msgs)
            bot.send_message(call.message.chat.id, msg_text, parse_mode="Markdown")
        else:
            bot.answer_callback_query(call.id, "لا يوجد سجل.")

    # >> باقي الأزرار
    elif call.data == "stats":
        bot.answer_callback_query(call.id, f"عدد المسجلين: {len(load_history())}")
    elif call.data == "status":
        bot.answer_callback_query(call.id, "السيرفر شغال ✅")
    elif call.data == "close":
        bot.delete_message(call.message.chat.id, call.message.message_id)

# --- 4. استلام الرسائل ---
@bot.message_handler(func=lambda message: message.chat.id not in ADMIN_IDS, content_types=['text', 'photo', 'voice', 'video', 'sticker', 'document'])
def forward_to_admins(message):
    user_id = message.chat.id
    
    # 🔥 تجهيز الاسم مع اليوزر بشكل إجباري 🔥
    first_name = message.chat.first_name or "مجهول"
    
    if message.from_user.username:
        # إذا عنده يوزر
        user_name_full = f"{first_name} (@{message.from_user.username})"
        username_link = f"@{message.from_user.username}"
    else:
        # إذا ما عنده يوزر، نكتب (لا يوجد يوزر) عشان الادمن يعرف
        user_name_full = f"{first_name} (لا يوجد يوزر)"
        username_link = "لا يوجد"

    msg_content = message.text if message.content_type == 'text' else f"[{message.content_type}]"
    
    # حفظ الاسم الجديد في السجل
    save_message(user_id, user_name_full, msg_content, is_admin=False)
    
    info_text = f"📩 **رسالة جديدة**\n👤 الاسم: {first_name}\n🔗 يوزر: {username_link}\n🆔 ID: `{user_id}`\n\n"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📜 عرض السجل", callback_data=f"hist_{user_id}"))

    for admin in ADMIN_IDS:
        try:
            if message.content_type == 'text':
                bot.send_message(admin, info_text + f"📝 النص:\n{message.text}", parse_mode="Markdown", reply_markup=markup)
            else:
                bot.send_message(admin, info_text + f"📎 أرسل ملف: {message.content_type}", parse_mode="Markdown")
                bot.forward_message(admin, user_id, message.message_id)
                bot.send_message(admin, f"تحكم بـ {user_id}", reply_markup=markup)
        except: pass

# --- 5. الرد الذكي ---
@bot.message_handler(content_types=['text', 'photo', 'voice', 'sticker'], func=lambda m: m.chat.id in ADMIN_IDS and m.reply_to_message)
def admin_reply(message):
    try:
        original_text = message.reply_to_message.text or message.reply_to_message.caption or ""
        search_id = re.search(r"ID: `(\d+)`", original_text) or re.search(r"ID: (\d+)", original_text) or re.search(r"تحكم بـ (\d+)", original_text) or re.search(r"سجل: .*?(\d+)", original_text)
        
        if search_id:
            user_id = search_id.group(1)
            replier_name = message.from_user.first_name
            replier_id = message.from_user.id
            
            reply_content = message.text if message.content_type == 'text' else f"[{message.content_type}]"
            save_message(user_id, replier_name, reply_content, is_admin=True)

            if message.content_type == 'text':
                bot.send_message(user_id, f"👮‍♂️ رد الإدارة:\n\n{message.text}")
            elif message.content_type == 'photo':
                bot.send_photo(user_id, message.photo[-1].file_id, caption=message.caption)
            elif message.content_type == 'voice':
                bot.send_voice(user_id, message.voice.file_id)
            elif message.content_type == 'sticker':
                bot.send_sticker(user_id, message.sticker.file_id)
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("📜 عرض السجل", callback_data=f"hist_{user_id}"))
            
            bot.reply_to(message, f"✅ تم الإرسال.\n🆔 ID: `{user_id}`", parse_mode="Markdown", reply_markup=markup)
            
            for admin in ADMIN_IDS:
                if admin != replier_id:
                    try: bot.send_message(admin, f"⚠️ المشرف {replier_name} رد على {user_id}.")
                    except: pass
        else:
            bot.reply_to(message, "❌ لم أجد الآيدي.")

    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

keep_alive()
bot.infinity_polling()
