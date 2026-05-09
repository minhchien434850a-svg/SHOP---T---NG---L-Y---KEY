from flask import Flask
from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

import sqlite3
import requests
import threading
import random
import string

# =========================================
# CONFIG
# =========================================

BOT_TOKEN = "8712999576:AAGpRyiWBvzrqNPVSfoT9em9rtNJv9nuA4k"

SEPAY_API_KEY = "UMRLQBWEP5ZMBIJDTWR0KUCFRLUMFXGWGZUSIP9DVND3LJCP6SZ2DESJY19HVTAK"

ADMIN_ID = 8126773907

BANK_NAME = "MSB"

BANK_NUMBER = "80003122324"

BANK_OWNER = "TRAN MINH CHIEN"

# =========================================
# BOT
# =========================================

bot = TeleBot(BOT_TOKEN)

app = Flask(__name__)

# =========================================
# DATABASE
# =========================================

conn = sqlite3.connect(
    "shop.db",
    check_same_thread=False
)

cursor = conn.cursor()

# PRODUCTS

cursor.execute("""
CREATE TABLE IF NOT EXISTS products(
    product_code TEXT,
    display_name TEXT,
    status INTEGER
)
""")

# PRICES

cursor.execute("""
CREATE TABLE IF NOT EXISTS prices(
    product_code TEXT,
    package TEXT,
    price INTEGER
)
""")

# KEYS

cursor.execute("""
CREATE TABLE IF NOT EXISTS keys_data(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_code TEXT,
    package TEXT,
    key_value TEXT,
    sold INTEGER DEFAULT 0
)
""")

# ORDERS

cursor.execute("""
CREATE TABLE IF NOT EXISTS orders(
    payment_code TEXT,
    chat_id TEXT,
    product_code TEXT,
    package TEXT,
    amount INTEGER,
    status TEXT
)
""")

conn.commit()

# =========================================
# START
# =========================================

@bot.message_handler(commands=['start'])
def start(message):

    markup = InlineKeyboardMarkup()

    cursor.execute("""
    SELECT *
    FROM products
    WHERE status=1
    """)

    products = cursor.fetchall()

    for product in products:

        product_code = product[0]

        display_name = product[1]

        markup.row(
            InlineKeyboardButton(
                display_name,
                callback_data=f"product_{product_code}"
            )
        )

    bot.send_message(
        message.chat.id,
        """
🎮 SHOP TOOL ONLINE

💰 THANH TOÁN TỰ ĐỘNG
🔑 GIAO KEY TỰ ĐỘNG
📱 IOS / ANDROID
""",
        reply_markup=markup
    )

# =========================================
# CALLBACK
# =========================================

@bot.callback_query_handler(func=lambda call: True)
def callback(call):

    data = call.data

    # ====================================
    # CHỌN GAME
    # ====================================

    if data.startswith("product_"):

        product_code = data.replace(
            "product_",
            ""
        )

        markup = InlineKeyboardMarkup()

        markup.row(

            InlineKeyboardButton(
                "🍎 IOS",
                callback_data=f"device_{product_code}_ios"
            ),

            InlineKeyboardButton(
                "🤖 ANDROID",
                callback_data=f"device_{product_code}_android"
            )
        )

        bot.send_message(
            call.message.chat.id,
            "📱 CHỌN HỆ ĐIỀU HÀNH",
            reply_markup=markup
        )

    # ====================================
    # CHỌN IOS / ANDROID
    # ====================================

    elif data.startswith("device_"):

        split_data = data.split("_")

        product_code = split_data[1]

        device = split_data[2]

        markup = InlineKeyboardMarkup()

        versions = [
            "vingold",
            "vipred",
            "lite"
        ]

        for version in versions:

            markup.row(
                InlineKeyboardButton(
                    version.upper(),
                    callback_data=f"version_{product_code}_{device}_{version}"
                )
            )

        bot.send_message(
            call.message.chat.id,
            f"""
🎮 {product_code.upper()}

📱 {device.upper()}

📦 CHỌN PHIÊN BẢN
""",
            reply_markup=markup
        )

    # ====================================
    # CHỌN PHIÊN BẢN
    # ====================================

    elif data.startswith("version_"):

        split_data = data.split("_")

        product_code = split_data[1]

        device = split_data[2]

        version = split_data[3]

        markup = InlineKeyboardMarkup()

        markup.row(
            InlineKeyboardButton(
                "⏰ GIỜ",
                callback_data=f"buy_{product_code}_{device}_{version}_gio"
            )
        )

        markup.row(
            InlineKeyboardButton(
                "📅 NGÀY",
                callback_data=f"buy_{product_code}_{device}_{version}_ngay"
            )
        )

        markup.row(
            InlineKeyboardButton(
                "🗓 TUẦN",
                callback_data=f"buy_{product_code}_{device}_{version}_tuan"
            )
        )

        markup.row(
            InlineKeyboardButton(
                "📦 THÁNG",
                callback_data=f"buy_{product_code}_{device}_{version}_thang"
            )
        )

        bot.send_message(
            call.message.chat.id,
            f"""
🎮 {product_code.upper()}

📱 {device.upper()}

📦 {version.upper()}

⏰ CHỌN THỜI GIAN
""",
            reply_markup=markup
        )

    # ====================================
    # MUA
    # ====================================

    elif data.startswith("buy_"):

        split_data = data.split("_")

        product_code = split_data[1]

        device = split_data[2]

        version = split_data[3]

        package = split_data[4]

        full_package = f"{device}_{version}_{package}"

        cursor.execute("""
        SELECT price
        FROM prices
        WHERE product_code=?
        AND package=?
        """, (
            product_code,
            full_package
        ))

        result = cursor.fetchone()

        if not result:

            bot.send_message(
                call.message.chat.id,
                "❌ CHƯA CÓ GÓI"
            )

            return

        amount = result[0]

        payment_code = "PAY" + ''.join(
            random.choices(
                string.digits,
                k=6
            )
        )

        cursor.execute("""
        INSERT INTO orders
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            payment_code,
            str(call.message.chat.id),
            product_code,
            full_package,
            amount,
            "pending"
        ))

        conn.commit()

        qr_url = f"https://img.vietqr.io/image/{BANK_NAME}-{BANK_NUMBER}-compact2.png?amount={amount}&addInfo={payment_code}&accountName={BANK_OWNER}"

        text = f"""
🎮 GAME:
{product_code.upper()}

📱 HỆ:
{device.upper()}

📦 PHIÊN BẢN:
{version.upper()}

⏰ GÓI:
{package.upper()}

💵 GIÁ:
{amount:,}đ

🏦 BANK:
{BANK_NAME}

💳 STK:
{BANK_NUMBER}

👤 CHỦ TK:
{BANK_OWNER}

📌 NỘI DUNG:
{payment_code}
"""

        markup = InlineKeyboardMarkup()

        markup.row(
            InlineKeyboardButton(
                "🧾 KIỂM TRA THANH TOÁN",
                callback_data=f"check_{payment_code}"
            )
        )

        markup.row(
            InlineKeyboardButton(
                "🔄 RESET QR",
                callback_data=f"buy_{product_code}_{device}_{version}_{package}"
            )
        )

        bot.send_photo(
            call.message.chat.id,
            qr_url,
            caption=text,
            reply_markup=markup
        )

    # ====================================
    # CHECK THANH TOÁN
    # ====================================

    elif data.startswith("check_"):

        payment_code = data.replace(
            "check_",
            ""
        )

        headers = {
            "Authorization": f"Bearer {SEPAY_API_KEY}"
        }

        response = requests.get(
            "https://my.sepay.vn/userapi/transactions/list",
            headers=headers
        )

        data_json = response.json()

        found = False

        for trans in data_json["data"]:

            content = str(
                trans.get(
                    "transaction_content",
                    ""
                )
            )

            if payment_code in content:

                found = True

                cursor.execute("""
                SELECT *
                FROM orders
                WHERE payment_code=?
                """, (payment_code,))

                order = cursor.fetchone()

                if not order:
                    return

                product_code = order[2]

                package = order[3]

                cursor.execute("""
                SELECT id, key_value
                FROM keys_data
                WHERE product_code=?
                AND package=?
                AND sold=0
                LIMIT 1
                """, (
                    product_code,
                    package
                ))

                key_data = cursor.fetchone()

                if not key_data:

                    bot.send_message(
                        call.message.chat.id,
                        "❌ HẾT KEY"
                    )

                    return

                key_id = key_data[0]

                key_value = key_data[1]

                cursor.execute("""
                UPDATE keys_data
                SET sold=1
                WHERE id=?
                """, (key_id,))

                conn.commit()

                bot.send_message(
                    call.message.chat.id,
                    f"""
✅ THANH TOÁN THÀNH CÔNG

🔑 KEY:
{key_value}
"""
                )

                return

        if not found:

            bot.send_message(
                call.message.chat.id,
                "❌ CHƯA THANH TOÁN"
            )

# =========================================
# ADD PRODUCT
# =========================================

@bot.message_handler(commands=['addproduct'])
def addproduct(message):

    if message.from_user.id != ADMIN_ID:
        return

    try:

        split_text = message.text.split()

        product_code = split_text[1]

        display_name = split_text[2]

        cursor.execute("""
        INSERT INTO products
        VALUES (?, ?, ?)
        """, (
            product_code,
            display_name,
            1
        ))

        conn.commit()

        bot.reply_to(
            message,
            "✅ ĐÃ THÊM GAME"
        )

    except:

        bot.reply_to(
            message,
            "❌ /addproduct code ten"
        )

# =========================================
# ADD PACKAGE
# =========================================

@bot.message_handler(commands=['addpackage'])
def addpackage(message):

    if message.from_user.id != ADMIN_ID:
        return

    try:

        split_text = message.text.split()

        product_code = split_text[1]

        package = split_text[2]

        price = int(split_text[3])

        cursor.execute("""
        INSERT INTO prices
        VALUES (?, ?, ?)
        """, (
            product_code,
            package,
            price
        ))

        conn.commit()

        bot.reply_to(
            message,
            "✅ ĐÃ THÊM GÓI"
        )

    except:

        bot.reply_to(
            message,
            "❌ /addpackage game goi gia"
        )

# =========================================
# CHANGE PRICE
# =========================================

@bot.message_handler(commands=['changeprice'])
def changeprice(message):

    if message.from_user.id != ADMIN_ID:
        return

    try:

        split_text = message.text.split()

        product_code = split_text[1]

        package = split_text[2]

        new_price = int(split_text[3])

        cursor.execute("""
        UPDATE prices
        SET price=?
        WHERE product_code=?
        AND package=?
        """, (
            new_price,
            product_code,
            package
        ))

        conn.commit()

        bot.reply_to(
            message,
            "✅ ĐÃ ĐỔI GIÁ"
        )

    except:

        bot.reply_to(
            message,
            "❌ /changeprice game goi gia"
        )

# =========================================
# ADD KEY
# =========================================

@bot.message_handler(commands=['addkey'])
def addkey(message):

    if message.from_user.id != ADMIN_ID:
        return

    try:

        split_text = message.text.split()

        product_code = split_text[1]

        package = split_text[2]

        key_value = split_text[3]

        cursor.execute("""
        INSERT INTO keys_data(
            product_code,
            package,
            key_value
        )
        VALUES (?, ?, ?)
        """, (
            product_code,
            package,
            key_value
        ))

        conn.commit()

        bot.reply_to(
            message,
            "✅ ĐÃ THÊM KEY"
        )

    except:

        bot.reply_to(
            message,
            "❌ /addkey game goi key"
        )

# =========================================
# DELETE PRODUCT
# =========================================

@bot.message_handler(commands=['delproduct'])
def delproduct(message):

    if message.from_user.id != ADMIN_ID:
        return

    try:

        split_text = message.text.split()

        product_code = split_text[1]

        cursor.execute("""
        DELETE FROM products
        WHERE product_code=?
        """, (product_code,))

        conn.commit()

        bot.reply_to(
            message,
            "✅ ĐÃ XOÁ GAME"
        )

    except:

        bot.reply_to(
            message,
            "❌ /delproduct game"
        )

# =========================================
# DELETE PACKAGE
# =========================================

@bot.message_handler(commands=['delpackage'])
def delpackage(message):

    if message.from_user.id != ADMIN_ID:
        return

    try:

        split_text = message.text.split()

        product_code = split_text[1]

        package = split_text[2]

        cursor.execute("""
        DELETE FROM prices
        WHERE product_code=?
        AND package=?
        """, (
            product_code,
            package
        ))

        conn.commit()

        bot.reply_to(
            message,
            "✅ ĐÃ XOÁ GÓI"
        )

    except:

        bot.reply_to(
            message,
            "❌ /delpackage game goi"
        )

# =========================================
# DELETE KEY
# =========================================

@bot.message_handler(commands=['delkey'])
def delkey(message):

    if message.from_user.id != ADMIN_ID:
        return

    try:

        split_text = message.text.split()

        product_code = split_text[1]

        package = split_text[2]

        key_value = split_text[3]

        cursor.execute("""
        DELETE FROM keys_data
        WHERE product_code=?
        AND package=?
        AND key_value=?
        """, (
            product_code,
            package,
            key_value
        ))

        conn.commit()

        bot.reply_to(
            message,
            "✅ ĐÃ XOÁ KEY"
        )

    except:

        bot.reply_to(
            message,
            "❌ /delkey game goi key"
        )

# =========================================
# CHANGE VERSION
# =========================================

@bot.message_handler(commands=['changeversion'])
def changeversion(message):

    if message.from_user.id != ADMIN_ID:
        return

    try:

        split_text = message.text.split()

        old_version = split_text[1]

        new_version = split_text[2]

        cursor.execute("""
        UPDATE prices
        SET package = REPLACE(
            package,
            ?,
            ?
        )
        WHERE package LIKE ?
        """, (
            old_version,
            new_version,
            f"%{old_version}%"
        ))

        cursor.execute("""
        UPDATE keys_data
        SET package = REPLACE(
            package,
            ?,
            ?
        )
        WHERE package LIKE ?
        """, (
            old_version,
            new_version,
            f"%{old_version}%"
        ))

        conn.commit()

        bot.reply_to(
            message,
            "✅ ĐÃ ĐỔI PHIÊN BẢN"
        )

    except:

        bot.reply_to(
            message,
            "❌ /changeversion old new"
        )

# =========================================
# CHANGE TIME
# =========================================

@bot.message_handler(commands=['changetime'])
def changetime(message):

    if message.from_user.id != ADMIN_ID:
        return

    try:

        split_text = message.text.split()

        old_time = split_text[1]

        new_time = split_text[2]

        cursor.execute("""
        UPDATE prices
        SET package = REPLACE(
            package,
            ?,
            ?
        )
        WHERE package LIKE ?
        """, (
            old_time,
            new_time,
            f"%{old_time}%"
        ))

        cursor.execute("""
        UPDATE keys_data
        SET package = REPLACE(
            package,
            ?,
            ?
        )
        WHERE package LIKE ?
        """, (
            old_time,
            new_time,
            f"%{old_time}%"
        ))

        conn.commit()

        bot.reply_to(
            message,
            "✅ ĐÃ ĐỔI THỜI GIAN"
        )

    except:

        bot.reply_to(
            message,
            "❌ /changetime old new"
        )

# =========================================
# RUN BOT
# =========================================

threading.Thread(
    target=lambda: bot.infinity_polling()
).start()

# =========================================
# FLASK
# =========================================

@app.route("/")
def home():
    return "BOT ONLINE"

app.run(
    host="0.0.0.0",
    port=3000
)
