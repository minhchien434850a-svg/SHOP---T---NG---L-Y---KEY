import os
import re
import sqlite3

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ChatPermissions
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# =========================================
# TOKEN
# =========================================

TOKEN = os.getenv("8927671568:AAEIs-A6sS3H2KljAHpQ3hBvwYyYhnobPUo")

if not TOKEN:
    raise ValueError("BOT_TOKEN not found!")

# =========================================
# DATABASE
# =========================================

conn = sqlite3.connect(
    "/tmp/bot.db",
    check_same_thread=False
)

cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS antilink(
    chat_id TEXT PRIMARY KEY
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS warnings(
    user_id TEXT PRIMARY KEY,
    count INTEGER
)
""")

conn.commit()

# =========================================
# REGEX
# =========================================

LINK_REGEX = r"(https?://|www\.|t\.me|discord\.gg|\.com|\.net|\.org)"

# =========================================
# ADMIN CHECK
# =========================================

async def is_admin(update: Update):

    admins = await update.effective_chat.get_administrators()

    return any(
        admin.user.id == update.effective_user.id
        for admin in admins
    )

# =========================================
# PANEL
# =========================================

def panel():

    keyboard = [

        [
            InlineKeyboardButton(
                "🛡 ON",
                callback_data="on"
            ),

            InlineKeyboardButton(
                "❌ OFF",
                callback_data="off"
            )
        ],

        [
            InlineKeyboardButton(
                "📊 STATS",
                callback_data="stats"
            )
        ]
    ]

    return InlineKeyboardMarkup(keyboard)

# =========================================
# START
# =========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = """
🤖 BOT ONLINE

COMMANDS:

/menu
/mute
/ban
"""

    await update.message.reply_text(text)

# =========================================
# MENU
# =========================================

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await is_admin(update):

        return await update.message.reply_text(
            "❌ Admin only"
        )

    await update.message.reply_text(
        "⚙️ CONTROL PANEL",
        reply_markup=panel()
    )

# =========================================
# BUTTONS
# =========================================

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    chat_id = str(query.message.chat.id)

    # ENABLE

    if query.data == "on":

        cur.execute(
            "INSERT OR IGNORE INTO antilink VALUES (?)",
            (chat_id,)
        )

        conn.commit()

        await query.message.reply_text(
            "🛡 AntiLink Enabled"
        )

    # DISABLE

    elif query.data == "off":

        cur.execute(
            "DELETE FROM antilink WHERE chat_id=?",
            (chat_id,)
        )

        conn.commit()

        await query.message.reply_text(
            "❌ AntiLink Disabled"
        )

    # STATS

    elif query.data == "stats":

        cur.execute(
            "SELECT COUNT(*) FROM warnings"
        )

        total = cur.fetchone()[0]

        await query.message.reply_text(
            f"📊 Total warned users: {total}"
        )

# =========================================
# MUTE
# =========================================

async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await is_admin(update):
        return

    if not update.message.reply_to_message:

        return await update.message.reply_text(
            "⚠️ Reply user"
        )

    user_id = update.message.reply_to_message.from_user.id

    try:

        await update.effective_chat.restrict_member(
            user_id,
            permissions=ChatPermissions(
                can_send_messages=False
            )
        )

        await update.message.reply_text(
            "🔇 User muted"
        )

    except Exception as e:

        print(e)

        await update.message.reply_text(
            "❌ Cannot mute user"
        )

# =========================================
# BAN
# =========================================

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await is_admin(update):
        return

    if not update.message.reply_to_message:

        return await update.message.reply_text(
            "⚠️ Reply user"
        )

    user_id = update.message.reply_to_message.from_user.id

    try:

        await update.effective_chat.ban_member(
            user_id
        )

        await update.message.reply_text(
            "🚫 User banned"
        )

    except Exception as e:

        print(e)

        await update.message.reply_text(
            "❌ Cannot ban user"
        )

# =========================================
# ANTI LINK
# =========================================

async def anti_link(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    text = update.message.text

    if not text:
        return

    chat_id = str(update.effective_chat.id)

    # CHECK ENABLE

    cur.execute(
        "SELECT * FROM antilink WHERE chat_id=?",
        (chat_id,)
    )

    enabled = cur.fetchone()

    if not enabled:
        return

    # CHECK LINK

    if re.search(LINK_REGEX, text, re.IGNORECASE):

        admins = await update.effective_chat.get_administrators()

        # IGNORE ADMINS

        if any(
            admin.user.id == update.message.from_user.id
            for admin in admins
        ):
            return

        # DELETE MESSAGE

        try:

            await update.message.delete()

        except Exception as e:

            print(e)

        user_id = str(update.message.from_user.id)

        # GET WARNING

        cur.execute(
            "SELECT count FROM warnings WHERE user_id=?",
            (user_id,)
        )

        row = cur.fetchone()

        # UPDATE WARNING

        if row:

            count = row[0] + 1

            cur.execute(
                "UPDATE warnings SET count=? WHERE user_id=?",
                (count, user_id)
            )

        else:

            count = 1

            cur.execute(
                "INSERT INTO warnings VALUES (?, ?)",
                (user_id, count)
            )

        conn.commit()

        # AUTO BAN

        if count >= 3:

            try:

                await update.effective_chat.ban_member(
                    int(user_id)
                )

                await update.message.reply_text(
                    "🚫 User auto banned"
                )

            except Exception as e:

                print(e)

        else:

            await update.message.reply_text(
                f"⚠️ Warning {count}/3"
            )

# =========================================
# ERROR
# =========================================

async def error_handler(update, context):

    print("ERROR:", context.error)

# =========================================
# MAIN
# =========================================

def main():

    print("🚀 BOT STARTING...")

    app = Application.builder().token(TOKEN).build()

    # COMMANDS

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("menu", menu)
    )

    app.add_handler(
        CommandHandler("mute", mute)
    )

    app.add_handler(
        CommandHandler("ban", ban)
    )

    # BUTTONS

    app.add_handler(
        CallbackQueryHandler(buttons)
    )

    # TEXT

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            anti_link
        )
    )

    # ERROR

    app.add_error_handler(error_handler)

    print("✅ BOT ONLINE")

    app.run_polling()

# =========================================
# RUN
# =========================================

if __name__ == "__main__":
    main()
