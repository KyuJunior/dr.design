import telebot
from telebot import types
from background import keep_alive
import re
import json
import os
import time
from datetime import datetime

# --- إعدادات البوت والمدراء ---
TOKEN = "8172386548:AAEBXoaZ-44Q9vHlpWddVEpqMepa4X_71Yk"
ADMIN_IDS = [667318916, 462652633] # أنت وياسر

bot = telebot.TeleBot(TOKEN)
HISTORY_FILE = "chat_history.json"
BLOCKED_FILE = "blocked_users.json"

# --- دوال السجل والبيانات ---
def load_json(filename):
    if not os.path.exists(filename): return {}
    try:
        with open(filename, "r", encoding="utf-8") as f: return json.load(f)
    except: return {}

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def save_message(user_id, sender_name, text, is_admin=False):
    history = load_json(HISTORY_FILE)
    user_id = str(user_id)
    if user_id not in history: history[user_id] = []
    
    time_now = datetime.now().strftime("%Y-%m-%d %H:%M")
    icon = "👮‍♂️" if is_admin else "👤"
    sender_name = sender_name.replace(":", "").replace("|", "")
    entry = f"{time_now} | {icon} {sender_name}: {text}"
    
    history[user_id].append(entry)
    if len(history[user_id]) > 50: history[user_id] = history[user_id][-50:]
    save_json(HISTORY_FILE, history)

def get_customer_name(user_id, history):
    user_id = str(user_id)
    if user_id in history:
        for msg in reversed(history[user_id]):
            if "👤" in msg:
                try: return msg.split('| 👤')[1].split(':')[0].strip()
                except: pass
    return "غير معروف"

# --- دوال الحظر ---
def is_user_blocked(user_id):
    blocked = load_json(BLOCKED_FILE)
    return str(user_id) in blocked

def toggle_block(user_id, admin_name):
    blocked = load_json(BLOCKED_FILE)
    user_id = str(user_id)
    if user_id in blocked:
        del blocked[user_id] # إلغاء الحظر
        status = "unblocked"
    else:
        blocked[user_id] = {"by": admin_name, "date": str(datetime.now())} # حظر
        status = "blocked"
    save_json(BLOCKED_FILE, blocked)
    return status

# --- 1. ترحيب ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    if is_user_blocked(message.chat.id): return # تجاهل المحظورين
    bot.reply_to(message, "👋 أهلاً بك! \nأرسل رسالتك وسأرد عليك قريباً.")

# --- 2. الإذاعة (Broadcast) ---
@bot.message_handler(commands=['broadcast'])
def broadcast_message(message):
    if message.chat.id not in ADMIN_IDS: return

    # استخراج النص بعد الأمر
    msg_text = message.text.replace("/broadcast", "").strip()
    if not msg_text:
        bot.reply_to(message, "❌ خطأ: اكتب الرسالة بعد الأمر.\nمثال: `/broadcast السلام عليكم`", parse_mode="Markdown")
        return

    history = load_json(HISTORY_FILE)
    users = list(history.keys())
    
    if not users:
        bot.reply_to(message, "📭 لا يوجد مستخدمين لإرسال الرسالة لهم.")
        return

    status_msg = bot.reply_to(message, f"⏳ جاري إرسال الرسالة إلى {len(users)} مستخدم...")
    
    success_count = 0
    blocked_count = 0
    
    for user_id in users:
        try:
            bot.send_message(user_id, f"📢 **تنويه عام:**\n\n{msg_text}", parse_mode="Markdown")
            success_count += 1
            time.sleep(0.1) # استراحة بسيطة لتجنب الحظر من تيليجرام
        except Exception as e:
            # غالباً الخطأ يعني أن المستخدم حظر البوت
            blocked_count += 1

    bot.edit_message_text(f"✅ **تمت الإذاعة بنجاح!**\n\n📤 تم الإرسال لـ: {success_count}\n❌ فشل (حظروا البوت): {blocked_count}", message.chat.id, status_msg.message_id)

# --- 3. لوحة التحكم ---
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
    
    bot.send_message(chat_id, "🛠 **لوحة تحكم الإدارة:**", reply_markup=markup)

# --- 4. معالج الأزرار (تحديث الحظر) ---
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.message.chat.id not in ADMIN_IDS: return

    # >> زر الحظر / فك الحظر
    if call.data.startswith("block_"):
        user_id = call.data.split("_")[1]
        admin_name = call.from_user.first_name
        status = toggle_block(user_id, admin_name)
        
        # تحديث نص الزر فوراً
        new_markup = types.InlineKeyboardMarkup()
        btn_hist = types.InlineKeyboardButton("📜 السجل", callback_data=f"hist_{user_id}")
        
        if status == "blocked":
            btn_block = types.InlineKeyboardButton("✅ إلغاء الحظر", callback_data=f"block_{user_id}")
            bot.answer_callback_query(call.id, "🚫 تم حظر المستخدم")
            bot.send_message(call.message.chat.id, f"🚫 قام {admin_name} بحظر المستخدم `{user_id}`.", parse_mode="Markdown")
        else:
            btn_block = types.InlineKeyboardButton("⛔ حظر", callback_data=f"block_{user_id}")
            bot.answer_callback_query(call.id, "✅ تم إلغاء الحظر")
            bot.send_message(call.message.chat.id, f"✅ قام {admin_name} برفع الحظر عن `{user_id}`.", parse_mode="Markdown")
            
        new_markup.add(btn_hist, btn_block)
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=new_markup)

    # >> زر: لم يتم الرد
    elif call.data == "no_reply":
        history = load_json(HISTORY_FILE)
        unanswered = []
        for uid, msgs in history.items():
            if msgs and "👤" in msgs[-1]: 
                name = get_customer_name(uid, history)
                unanswered.append(f"• {name}\n🆔 `{uid}`")
        
        if unanswered:
            text = "📬 **رسائل تنتظر الرد:**\n\n" + "\n".join(unanswered)
            bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
        else:
            bot.answer_callback_query(call.id, "الكل تم الرد عليه! 🎉")

    # >> زر: آخر 5 مستخدمين
    elif call.data == "recent_users":
        history = load_json(HISTORY_FILE)
        if not history:
            bot.answer_callback_query(call.id, "السجل فارغ.")
            return

        sorted_users = sorted(history.keys(), key=lambda k: history[k][-1].split('|')[0], reverse=True)[:5]
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        for uid in sorted_users:
            display_name = get_customer_name(uid, history)
            # إضافة علامة 🚫 بجانب الاسم اذا كان محظور
            if is_user_blocked(uid): display_name = "🚫 " + display_name
            
            markup.add(types.InlineKeyboardButton(f"{display_name} | {uid}", callback_data=f"hist_{uid}"))
        
        markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_home"))
        bot.edit_message_text("🕒 **آخر 5 أشخاص:**", call.message.chat.id, call.message.message_id, reply_markup=markup)

    # >> عرض السجل (مع أزرار التحكم)
    elif call.data.startswith("hist_"):
        user_id = call.data.split("_")[1]
        history = load_json(HISTORY_FILE)
        
        # تجهيز أزرار التحكم تحت السجل
        markup = types.InlineKeyboardMarkup()
        if is_user_blocked(user_id):
            markup.add(types.InlineKeyboardButton("✅ إلغاء الحظر", callback_data=f"block_{user_id}"))
        else:
            markup.add(types.InlineKeyboardButton("⛔ حظر المستخدم", callback_data=f"block_{user_id}"))

        if user_id in history:
            name = get_customer_name(user_id, history)
            last_msgs = history[user_id][-10:]
            msg_text = f"📜 **سجل: {name}**\n🆔 `{user_id}`\n\n" + "\n".join(last_msgs)
            bot.send_message(call.message.chat.id, msg_text, parse_mode="Markdown", reply_markup=markup)
        else:
            bot.answer_callback_query(call.id, "لا يوجد سجل.")

    elif call.data == "back_home":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        show_admin_menu(call.message.chat.id)
    elif call.data == "stats":
        bot.answer_callback_query(call.id, f"المستخدمين: {len(load_json(HISTORY_FILE))}")
    elif call.data == "status":
        bot.answer_callback_query(call.id, "شغال 100%")
    elif call.data == "close":
        bot.delete_message(call.message.chat.id, call.message.message_id)

# --- 5. استلام الرسائل ---
@bot.message_handler(func=lambda message: message.chat.id not in ADMIN_IDS, content_types=['text', 'photo', 'voice', 'video', 'sticker', 'document'])
def forward_to_admins(message):
    user_id = message.chat.id
    
    # ⛔ التحقق من الحظر
    if is_user_blocked(user_id):
        return # تجاهل الرسالة تماماً

    first_name = message.chat.first_name or "مجهول"
    user_name_full = f"{first_name} (@{message.from_user.username})" if message.from_user.username else f"{first_name} (لا يوجد يوزر)"
    username_link = f"@{message.from_user.username}" if message.from_user.username else "لا يوجد"

    msg_content = message.text if message.content_type == 'text' else f"[{message.content_type}]"
    save_message(user_id, user_name_full, msg_content, is_admin=False)
    
    info_text = f"📩 **رسالة جديدة**\n👤 {first_name}\n🔗 {username_link}\n🆔 `{user_id}`\n\n"
    
    # أزرار الرد (سجل + حظر)
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📜 السجل", callback_data=f"hist_{user_id}"), 
               types.InlineKeyboardButton("⛔ حظر", callback_data=f"block_{user_id}"))

    for admin in ADMIN_IDS:
        try:
            if message.content_type == 'text':
                bot.send_message(admin, info_text + f"📝:\n{message.text}", parse_mode="Markdown", reply_markup=markup)
            else:
                bot.send_message(admin, info_text + f"📎 ملف: {message.content_type}", parse_mode="Markdown")
                bot.forward_message(admin, user_id, message.message_id)
                bot.send_message(admin, f"تحكم بـ {user_id}", reply_markup=markup)
        except: pass

# --- 6. الرد الذكي ---
@bot.message_handler(content_types=['text', 'photo', 'voice', 'sticker'], func=lambda m: m.chat.id in ADMIN_IDS and m.reply_to_message)
def admin_reply(message):
    try:
        original_text = message.reply_to_message.text or message.reply_to_message.caption or ""
        search_id = re.search(r"ID: `(\d+)`", original_text) or re.search(r"ID: (\d+)", original_text) or re.search(r"تحكم بـ (\d+)", original_text) or re.search(r"سجل: .*?(\d+)", original_text)
        
        if search_id:
            user_id = search_id.group(1)
            replier_name = message.from_user.first_name
            
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
            
            # إعادة الأزرار (سجل + حظر) مع رسالة التأكيد
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("📜 السجل", callback_data=f"hist_{user_id}"), 
                       types.InlineKeyboardButton("⛔ حظر", callback_data=f"block_{user_id}"))
            
            bot.reply_to(message, f"✅ تم الإرسال.\n🆔 ID: `{user_id}`", parse_mode="Markdown", reply_markup=markup)
            
            for admin in ADMIN_IDS:
                if admin != message.from_user.id:
                    try: bot.send_message(admin, f"⚠️ {replier_name} رد على {user_id}.")
                    except: pass
        else:
            bot.reply_to(message, "❌ لم أجد الآيدي.")

    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

keep_alive()
bot.infinity_polling()
