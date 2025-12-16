import telebot
from background import keep_alive
import re 

# --- بياناتك جاهزة هنا ---
TOKEN = "8172386548:AAEBXoaZ-44Q9vHlpWddVEpqMepa4X_71Yk"
ADMIN_ID = 667318916

bot = telebot.TeleBot(TOKEN)

# --- 1. ترحيب ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "👋 أهلاً بك! \nأرسل رسالتك الآن وسأقوم بالرد عليك.")

# --- 2. تحويل الرسائل للمدير ---
@bot.message_handler(func=lambda message: message.chat.id != ADMIN_ID, content_types=['text', 'photo', 'voice', 'video', 'document'])
def forward_to_admin(message):
    user_id = message.chat.id
    user_name = message.chat.first_name or "مجهول"
    username = f"@{message.chat.username}" if message.chat.username else "لا يوجد"
    
    # تنسيق الرسالة (مهم جداً لا تغير كلمة ID)
    info_text = f"📩 رسالة من: {user_name}\n👤 يوزر: {username}\n🆔 ID: {user_id}\n\n"
    
    try:
        if message.content_type == 'text':
            bot.send_message(ADMIN_ID, info_text + f"الرسالة:\n{message.text}")
        elif message.content_type == 'photo':
            bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=info_text + "[صورة]")
        elif message.content_type == 'voice':
            bot.send_voice(ADMIN_ID, message.voice.file_id, caption=info_text + "[بصمة صوتية]")
            
    except Exception as e:
        print(f"Error: {e}")

# --- 3. الرد الذكي من المدير ---
@bot.message_handler(content_types=['text', 'photo', 'voice', 'sticker'], func=lambda m: m.chat.id == ADMIN_ID and m.reply_to_message)
def admin_reply(message):
    try:
        original_text = message.reply_to_message.text or message.reply_to_message.caption or ""
        search_id = re.search(r"ID: (\d+)", original_text)
        
        if search_id:
            user_id = search_id.group(1)
            
            if message.content_type == 'text':
                bot.send_message(user_id, f"👮‍♂️ رد الإدارة:\n\n{message.text}")
            elif message.content_type == 'photo':
                bot.send_photo(user_id, message.photo[-1].file_id, caption=message.caption)
            elif message.content_type == 'voice':
                bot.send_voice(user_id, message.voice.file_id)
            elif message.content_type == 'sticker':
                bot.send_sticker(user_id, message.sticker.file_id)
                
            bot.reply_to(message, "✅ تم الإرسال.")
        else:
            bot.reply_to(message, "❌ لم أستطع تحديد الآيدي، تأكد أنك ترد على رسالة وصلت من البوت.")

    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

keep_alive()
bot.infinity_polling()
