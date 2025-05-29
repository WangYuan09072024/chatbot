import telebot
from telebot import types

API_TOKEN = '7892392901:AAH57r7JA9I4LVT2iCfIaydY1KzJtpVYAEs'  # 🔁 Đổi bằng token thật
bot = telebot.TeleBot(API_TOKEN)

connected_users = []
session_active = False
# Lưu 2 chiều: (sender_id, sender_msg_id) => (receiver_id, receiver_msg_id)
# và ngược lại
message_log = {}

def get_other_user(current_id):
    return connected_users[1] if connected_users[0] == current_id else connected_users[0]

@bot.message_handler(commands=['start'])
def handle_start(message):
    global session_active
    user_id = message.from_user.id

    if user_id not in connected_users:
        if len(connected_users) < 2:
            connected_users.append(user_id)
            bot.send_message(user_id, "✅ Connected! Waiting for the other user...")
            if len(connected_users) == 2:
                session_active = True
                print("== Connected Users ==\n", connected_users)
                for uid in connected_users:
                    send_main_menu(uid, "🎉 Two users connected! You can start chatting.")
        else:
            bot.send_message(user_id, "❗ This bot only supports 2 users.")
    else:
        bot.send_message(user_id, "🔄 You are already connected.")

def send_main_menu(chat_id, text):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("Continue chatting", "End chat")
    bot.send_message(chat_id, text, reply_markup=markup)

@bot.message_handler(content_types=['animation', 'photo', 'video', 'document'])
def handle_media(message):
    if not session_active or message.from_user.id not in connected_users:
        bot.send_message(message.chat.id, "❗ Not connected or chat not started.")
        return

    receiver_id = get_other_user(message.from_user.id)
    sent = None

    if message.content_type == 'animation':
        sent = bot.send_animation(receiver_id, message.animation.file_id)
    elif message.content_type == 'photo':
        sent = bot.send_photo(receiver_id, message.photo[-1].file_id)
    elif message.content_type == 'video':
        sent = bot.send_video(receiver_id, message.video.file_id)
    elif message.content_type == 'document':
        sent = bot.send_document(receiver_id, message.document.file_id)

    if sent:
        message_log[(message.from_user.id, message.message_id)] = (receiver_id, sent.message_id)
        message_log[(receiver_id, sent.message_id)] = (message.from_user.id, message.message_id)

@bot.message_handler(commands=['delete'])
def handle_delete_command(message):
    if not message.reply_to_message:
        bot.send_message(message.chat.id, "❗ Please reply to the message you want to delete.")
        return

    key = (message.from_user.id, message.reply_to_message.message_id)
    if key in message_log:
        receiver_id, msg_id = message_log[key]
        try:
            bot.delete_message(receiver_id, msg_id)
        except:
            bot.send_message(message.chat.id, "❌ Failed to delete message.")
    else:
        bot.send_message(message.chat.id, "⚠️ Cannot find the forwarded message.")

@bot.message_handler(func=lambda message: True)
def relay_message(message):
    global session_active
    user_id = message.from_user.id
    text = message.text

    if text == "End chat":
        session_active = False
        for uid in connected_users:
            bot.send_message(uid, "❗ Chat ended. Thank you!", reply_markup=types.ReplyKeyboardRemove())
        connected_users.clear()
        return

    if text == "Continue chatting":
        bot.send_message(user_id, "✅ You can continue chatting.")
        return

    if session_active and user_id in connected_users:
        receiver_id = get_other_user(user_id)

        reply_to_id = None
        if message.reply_to_message:
            # Lấy message_id tương ứng bên phía người nhận
            reply_key = (user_id, message.reply_to_message.message_id)
            if reply_key in message_log:
                receiver_id, receiver_msg_id = message_log[reply_key]
                reply_to_id = receiver_msg_id

        if reply_to_id:
            sent = bot.send_message(receiver_id, text, reply_to_message_id=reply_to_id)
        else:
            sent = bot.send_message(receiver_id, text)

        # Lưu 2 chiều
        message_log[(user_id, message.message_id)] = (receiver_id, sent.message_id)
        message_log[(receiver_id, sent.message_id)] = (user_id, message.message_id)
    else:
        bot.send_message(user_id, "❗ Not connected or chat not started.")

@bot.edited_message_handler(func=lambda m: True)
def handle_edited_message(message):
    if not session_active or message.from_user.id not in connected_users:
        return

    key = (message.from_user.id, message.message_id)
    if key in message_log:
        receiver_id, old_msg_id = message_log[key]
        try:
            bot.delete_message(receiver_id, old_msg_id)
            sent = bot.send_message(receiver_id, message.text)
            message_log[key] = (receiver_id, sent.message_id)
            message_log[(receiver_id, sent.message_id)] = (message.from_user.id, message.message_id)
        except:
            print("❌ Failed to simulate message edit.")

print("🤖 Bot is running... waiting for /start")
bot.infinity_polling()
