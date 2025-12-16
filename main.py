import telebot
from background import keep_alive 
import time

# --- حط معلوماتك هنا ---
TOKEN = 8172386548:AAEBXoaZ-44Q9vHlpWddVEpqMepa4X_71Yk
ADMIN_ID = 667318916  # آيديك_هنا

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "هلا! أرسل رسالتك وسأرد عليك.")

@bot.message_handler(func=lambda message: message.chat.id != ADMIN_ID)
def forward_to_admin(message):
    user_id = message.chat.id
    msg_text = message.text
    user_name = message.chat.first_name
    admin_msg = f"رسالة من: {user_name}\nID: {user_id}\n\n{msg_text}"
    bot.send_message(ADMIN_ID, admin_msg)

@bot.message_handler(commands=['rep'], func=lambda message: message.chat.id == ADMIN_ID)
def reply_to_user(message):
    try:
        parts = message.text.split(maxsplit=2)
        if len(parts) < 3:
            bot.reply_to(message, "الصيغة غلط! اكتب: /rep الايدي الرسالة")
            return
        target_id = parts[1]
        reply_text = parts[2]
        bot.send_message(target_id, reply_text)
        bot.reply_to(message, "تم ✅")
    except Exception as e:
        bot.reply_to(message, f"خطأ: {e}")

keep_alive()
bot.infinity_polling()
