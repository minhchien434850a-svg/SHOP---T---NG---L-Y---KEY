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

# PACKAGE LINKS

cursor.execute("""
CREATE TABLE IF NOT EXISTS package_links(
    product_code TEXT,
    package TEXT,
    link TEXT
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

📥 BOT TỰ ĐỘNG
💰 THANH TOÁN SEPAY
🔑 TỰ ĐỘNG GIAO KEY
""",
        reply_markup=markup
    )

# =========================================
# CALLBACK
# =========================================

@bot.callback_query_handler(func=lambda call: True)
def callback(call):

    data = call.data

    # =====================================
    # PRODUCT
    # =====================================

    if data.startswith("product_"):

        product_code = data.replace(
            "product_",
            ""
        )

        markup = InlineKeyboardMarkup()

        cursor.execute("""
        SELECT package, price
        FROM prices
        WHERE product_code=?
        """, (product_code,))

        packages = cursor.fetchall()

        if not packages:

            bot.answer_callback_query(
                call.id,
                "❌ CHƯA CÓ GÓI"
            )
            return

        for package_data in packages:

            package = package_data[0]

            price = package_data[1]

            markup.row(
                InlineKeyboardButton(
                    f"{package.upper()} - {price:,}đ",
                    callback_data=f"buy_{product_code}_{package}"
                )
            )

        # FIX IPHONE BUTTON

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="📦 CHỌN GÓI",
            reply_markup=markup
        )

    # =====================================
    # BUY
    # =====================================

    elif data.startswith("buy_"):

        split_data = data.split("_")

        product_code = split_data[1]

        package = split_data[2]

        cursor.execute("""
        SELECT price
        FROM prices
        WHERE product_code=?
        AND package=?
        """, (
            product_code,
            package
        ))

        result = cursor.fetchone()

        if not result:

            bot.send_message(
                call.message.chat.id,
                "❌ CHƯA CÓ GIÁ"
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
            package,
            amount,
            "pending"
        ))

        conn.commit()

        headers = {
            "Authorization": f"Bearer {SEPAY_API_KEY}"
        }

        response = requests.get(
            "https://my.sepay.vn/userapi/bankaccounts/list",
            headers=headers
        )

        data_bank = response.json()

        bank = data_bank["data"][0]

        bank_name = bank["bank_name"]

        account_number = bank["account_number"]

        account_holder = bank[
            "account_holder_name"
        ]

        text = f"""
💰 SẢN PHẨM:
{product_code.upper()}

📦 GÓI:
{package.upper()}

💵 GIÁ:
{amount:,}đ

🏦 BANK:
{bank_name}

👤 CHỦ TK:
{account_holder}

💳 STK:
{account_number}

📌 NỘI DUNG:
{payment_code}

⚠️ BOT TỰ ĐỘNG GIAO KEY
"""

        bot.send_message(
            call.message.chat.id,
            text
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
            "✅ ĐÃ THÊM SẢN PHẨM"
        )

    except:

        bot.reply_to(
            message,
            "❌ Dùng:\n/addproduct code ten"
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
            f"✅ ĐÃ THÊM GÓI {package}"
        )

    except:

        bot.reply_to(
            message,
            "❌ Dùng:\n/addpackage code goi gia"
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
            "❌ Dùng:\n/changeprice code goi gia"
        )

# =========================================
# SET LINK
# =========================================

@bot.message_handler(commands=['setlink'])
def setlink(message):

    if message.from_user.id != ADMIN_ID:
        return

    try:

        split_text = message.text.split()

        product_code = split_text[1]

        package = split_text[2]

        link = split_text[3]

        cursor.execute("""
        DELETE FROM package_links
        WHERE product_code=?
        AND package=?
        """, (
            product_code,
            package
        ))

        cursor.execute("""
        INSERT INTO package_links
        VALUES (?, ?, ?)
        """, (
            product_code,
            package,
            link
        ))

        conn.commit()

        bot.reply_to(
            message,
            "✅ ĐÃ THÊM LINK"
        )

    except:

        bot.reply_to(
            message,
            "❌ Dùng:\n/setlink code goi link"
        )

# =========================================
# GET LINK
# =========================================

@bot.message_handler(commands=['getlink'])
def getlink(message):

    try:

        split_text = message.text.split()

        product_code = split_text[1]

        package = split_text[2]

        cursor.execute("""
        SELECT link
        FROM package_links
        WHERE product_code=?
        AND package=?
        """, (
            product_code,
            package
        ))

        result = cursor.fetchone()

        if not result:

            bot.reply_to(
                message,
                "❌ KHÔNG CÓ LINK"
            )

            return

        link = result[0]

        markup = InlineKeyboardMarkup()

        markup.add(
            InlineKeyboardButton(
                "📥 TẢI NGAY",
                url=link
            )
        )

        bot.send_message(
            message.chat.id,
            f"""
📦 {package.upper()}

🔗 {link}
""",
            reply_markup=markup
        )

    except:

        bot.reply_to(
            message,
            "❌ Dùng:\n/getlink code goi"
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
            "❌ Dùng:\n/addkey code goi key"
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
            "❌ Dùng:\n/delkey code goi key"
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
