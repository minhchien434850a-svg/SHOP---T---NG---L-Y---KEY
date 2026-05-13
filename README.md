# REQUIRE:
# pip install pytelegrambotapi flask

from flask import Flask
from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup
from telebot.types import InlineKeyboardButton

import threading
import telebot
import time

# =========================================
# CONFIG
# =========================================

BOT_TOKEN = "8710597616:AAHMg3o10lZnGEWLEr8CkYzFTa1WAuKrITY"

bot = TeleBot(BOT_TOKEN)

app = Flask(__name__)

# =========================================
# DATA
# =========================================

user_cooldown = {}

group_settings = {}

# =========================================
# CREATE GROUP
# =========================================

def create_group(group_id):

    if group_id not in group_settings:

        group_settings[group_id] = {

            "antilink": True,
            "cooldown": 1,
            "welcome": True,
            "afk": {}
        }

# =========================================
# CHECK ADMIN
# =========================================

def is_admin(chat_id, user_id):

    try:

        member = bot.get_chat_member(
            chat_id,
            user_id
        )

        if member.status in [
            "administrator",
            "creator"
        ]:
            return True

    except:
        pass

    return False

# =========================================
# START
# =========================================

@bot.message_handler(commands=['start'])
def start(message):

    markup = InlineKeyboardMarkup(row_width=3)

    buttons = [

        "Quản trị",
        "AFK",
        "Antiflood",

        "AntiRaid",
        "Authenticator",
        "Tự động Chặn",

        "AutoReactions",
        "BlacklistChat",
        "ChannelPost",

        "CleanService",
        "Kết nối",
        "CôngCụDán",

        "ĐiểmDanh",
        "FameRank",
        "Bộ lọc",

        "Chào mừng",
        "Import/Export",
        "Khóa",

        "Modmail",
        "NhãnDán",
        "NightMode",

        "Ghi chú",
        "OwnerEvents",
        "PhânTíchNhạc",

        "Lịch sử Tên",
        "SiêuQuảnTrị",
        "Chủ đề",

        "Translate",
        "TìmKiếmẢnh",
        "TảiVề",

        "TínhNăngInline",
        "TínhNăngKhác",
        "TạoPhiên"
    ]

    for btn in buttons:

        markup.add(
            InlineKeyboardButton(
                btn,
                callback_data="menu"
            )
        )

    bot.send_message(
        message.chat.id,
        """
🤖 BOT QUẢN LÝ NHÓM

✅ AntiLink
✅ AntiFlood
✅ AFK
✅ Welcome
✅ Mute
✅ Ban
✅ Kick
""",
        reply_markup=markup
    )

# =========================================
# HELP
# =========================================

@bot.message_handler(commands=['help'])
def help_cmd(message):

    bot.reply_to(
        message,
        """
📚 LỆNH BOT

/start
/help

💤 AFK
/afk [lý do]

🛡 CHỐNG LINK
/antilink_on
/antilink_off

⏰ FLOOD
/setflood 1

🔇 MUTE
/mute 5
/unmute

🚫 BAN
/ban
/unban userid

👢 KICK
/kick

📌 NOTE:
- Thành viên chỉ gửi 1 tin / 1 giây
- Chỉ admin mới gửi được link
"""
    )

# =========================================
# WELCOME
# =========================================

@bot.message_handler(content_types=['new_chat_members'])
def welcome(message):

    group_id = message.chat.id

    create_group(group_id)

    if not group_settings[group_id]["welcome"]:
        return

    for user in message.new_chat_members:

        bot.send_message(
            group_id,
            f"""
👋 CHÀO MỪNG

{user.first_name}

ĐẾN:
{message.chat.title}
"""
        )

# =========================================
# AFK
# =========================================

@bot.message_handler(commands=['afk'])
def afk(message):

    if message.chat.type == "private":
        return

    group_id = message.chat.id

    create_group(group_id)

    reason = "AFK"

    try:

        reason = message.text.split(
            " ",
            1
        )[1]

    except:
        pass

    group_settings[group_id]["afk"][
        message.from_user.id
    ] = reason

    bot.reply_to(
        message,
        f"""
💤 ĐÃ AFK

📌 {reason}
"""
    )

# =========================================
# ANTI SPAM + LINK
# =========================================

@bot.message_handler(func=lambda m: True)
def all_message(message):

    if message.chat.type == "private":
        return

    group_id = message.chat.id

    user_id = message.from_user.id

    create_group(group_id)

    # REMOVE AFK

    if user_id in group_settings[group_id]["afk"]:

        del group_settings[group_id]["afk"][
            user_id
        ]

        bot.reply_to(
            message,
            "✅ ĐÃ TẮT AFK"
        )

    # ANTI FLOOD

    if not is_admin(
        group_id,
        user_id
    ):

        cooldown = group_settings[group_id][
            "cooldown"
        ]

        current = time.time()

        if user_id in user_cooldown:

            diff = current - user_cooldown[user_id]

            if diff < cooldown:

                try:

                    bot.delete_message(
                        group_id,
                        message.message_id
                    )

                except:
                    pass

                return

        user_cooldown[user_id] = current

    # ANTI LINK

    if group_settings[group_id]["antilink"]:

        if not is_admin(
            group_id,
            user_id
        ):

            text = ""

            if message.text:
                text = message.text.lower()

            patterns = [

                "http://",
                "https://",
                "t.me/",
                "telegram.me/",
                ".com",
                ".net",
                ".xyz"
            ]

            for p in patterns:

                if p in text:

                    try:

                        bot.delete_message(
                            group_id,
                            message.message_id
                        )

                    except:
                        pass

                    bot.send_message(
                        group_id,
                        f"""
🚫 LINK BỊ CHẶN

👤 {message.from_user.first_name}
"""
                    )

                    return

# =========================================
# ANTI LINK ON
# =========================================

@bot.message_handler(commands=['antilink_on'])
def antilink_on(message):

    if not is_admin(
        message.chat.id,
        message.from_user.id
    ):
        return

    create_group(message.chat.id)

    group_settings[
        message.chat.id
    ]["antilink"] = True

    bot.reply_to(
        message,
        "✅ ĐÃ BẬT ANTI LINK"
    )

# =========================================
# ANTI LINK OFF
# =========================================

@bot.message_handler(commands=['antilink_off'])
def antilink_off(message):

    if not is_admin(
        message.chat.id,
        message.from_user.id
    ):
        return

    create_group(message.chat.id)

    group_settings[
        message.chat.id
    ]["antilink"] = False

    bot.reply_to(
        message,
        "❌ ĐÃ TẮT ANTI LINK"
    )

# =========================================
# SET FLOOD
# =========================================

@bot.message_handler(commands=['setflood'])
def setflood(message):

    if not is_admin(
        message.chat.id,
        message.from_user.id
    ):
        return

    try:

        second = int(
            message.text.split()[1]
        )

        create_group(message.chat.id)

        group_settings[
            message.chat.id
        ]["cooldown"] = second

        bot.reply_to(
            message,
            f"""
✅ ĐÃ SET

⏰ {second} GIÂY / TIN
"""
        )

    except:

        bot.reply_to(
            message,
            "❌ /setflood 1"
        )

# =========================================
# MUTE
# =========================================

@bot.message_handler(commands=['mute'])
def mute_user(message):

    if not is_admin(
        message.chat.id,
        message.from_user.id
    ):
        return

    try:

        if not message.reply_to_message:

            bot.reply_to(
                message,
                "❌ Reply người cần mute"
            )

            return

        minutes = int(
            message.text.split()[1]
        )

        target = message.reply_to_message.from_user.id

        until = int(
            time.time()
        ) + (minutes * 60)

        bot.restrict_chat_member(
            message.chat.id,
            target,
            until_date=until,
            can_send_messages=False
        )

        bot.reply_to(
            message,
            f"""
🔇 ĐÃ MUTE

⏰ {minutes} PHÚT
"""
        )

    except Exception as e:

        bot.reply_to(
            message,
            f"❌ {e}"
        )

# =========================================
# UNMUTE
# =========================================

@bot.message_handler(commands=['unmute'])
def unmute_user(message):

    if not is_admin(
        message.chat.id,
        message.from_user.id
    ):
        return

    try:

        if not message.reply_to_message:

            bot.reply_to(
                message,
                "❌ Reply người cần unmute"
            )

            return

        target = message.reply_to_message.from_user.id

        bot.restrict_chat_member(
            message.chat.id,
            target,
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True
        )

        bot.reply_to(
            message,
            "✅ ĐÃ UNMUTE"
        )

    except Exception as e:

        bot.reply_to(
            message,
            f"❌ {e}"
        )

# =========================================
# BAN
# =========================================

@bot.message_handler(commands=['ban'])
def ban_user(message):

    if not is_admin(
        message.chat.id,
        message.from_user.id
    ):
        return

    try:

        if not message.reply_to_message:

            bot.reply_to(
                message,
                "❌ Reply người cần ban"
            )

            return

        target = message.reply_to_message.from_user.id

        bot.ban_chat_member(
            message.chat.id,
            target
        )

        bot.reply_to(
            message,
            "🚫 ĐÃ BAN"
        )

    except Exception as e:

        bot.reply_to(
            message,
            f"❌ {e}"
        )

# =========================================
# UNBAN
# =========================================

@bot.message_handler(commands=['unban'])
def unban_user(message):

    if not is_admin(
        message.chat.id,
        message.from_user.id
    ):
        return

    try:

        user_id = int(
            message.text.split()[1]
        )

        bot.unban_chat_member(
            message.chat.id,
            user_id
        )

        bot.reply_to(
            message,
            "✅ ĐÃ UNBAN"
        )

    except Exception as e:

        bot.reply_to(
            message,
            f"❌ {e}"
        )

# =========================================
# KICK
# =========================================

@bot.message_handler(commands=['kick'])
def kick_user(message):

    if not is_admin(
        message.chat.id,
        message.from_user.id
    ):
        return

    try:

        if not message.reply_to_message:

            bot.reply_to(
                message,
                "❌ Reply người cần kick"
            )

            return

        target = message.reply_to_message.from_user.id

        bot.ban_chat_member(
            message.chat.id,
            target
        )

        bot.unban_chat_member(
            message.chat.id,
            target
        )

        bot.reply_to(
            message,
            "👢 ĐÃ KICK"
        )

    except Exception as e:

        bot.reply_to(
            message,
            f"❌ {e}"
        )

# =========================================
# FLASK
# =========================================

@app.route("/")
def home():

    return "BOT ONLINE"

# =========================================
# RUN
# =========================================

def run_bot():

    bot.remove_webhook()

    bot.infinity_polling(
        skip_pending=True
    )

threading.Thread(
    target=run_bot
).start()

print("BOT ONLINE")

app.run(
    host="0.0.0.0",
    port=3000
)
