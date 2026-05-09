# REQUIRE:
# pip install pytelegrambotapi flask requests

from flask import Flask
from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

import sqlite3
import threading
import random
import string
import requests
import os
import time

# =========================================
# CONFIG
# =========================================

BOT_TOKEN = "8664092084:AAHQdWBZQCp-RDRvgqt4eX9ODSXtE8kVF24"

SEPAY_API_KEY = "UMRLQBWEP5ZMBIJDTWR0KUCFRLUMFXGWGZUSIP9DVND3LJCP6SZ2DESJY19HVTAK"

ADMIN_ID = 8126773907

BANK_NAME = "MSB"

BANK_NUMBER = "80003122324"

BANK_OWNER = "TRAN MINH CHIEN"

CHECK_TIME = 10

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

# DEVICES

cursor.execute("""
CREATE TABLE IF NOT EXISTS devices(
    product_code TEXT,
    device TEXT
)
""")

# VERSIONS

cursor.execute("""
CREATE TABLE IF NOT EXISTS versions(
    product_code TEXT,
    device TEXT,
    version TEXT
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
    key_value TEXT
)
""")

# LINKS

cursor.execute("""
CREATE TABLE IF NOT EXISTS links(
    product_code TEXT,
    package TEXT,
    link TEXT
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

        markup.row(
            InlineKeyboardButton(
                product[1],
                callback_data=f"product_{product[0]}"
            )
        )

    bot.send_message(
        message.chat.id,
        """
🛒 DIGITAL SHOP

💳 THANH TOÁN QR
🔑 GIAO KEY TỰ ĐỘNG
📦 TẢI FILE TỰ ĐỘNG
""",
        reply_markup=markup
    )

# =========================================
# CALLBACK
# =========================================

@bot.callback_query_handler(func=lambda call: True)
def callback(call):

    data = call.data

    # PRODUCT

    if data.startswith("product_"):

        product_code = data.replace(
            "product_",
            ""
        )

        markup = InlineKeyboardMarkup()

        cursor.execute("""
        SELECT device
        FROM devices
        WHERE product_code=?
        """, (product_code,))

        devices = cursor.fetchall()

        for device_data in devices:

            device = device_data[0]

            markup.row(
                InlineKeyboardButton(
                    device.upper(),
                    callback_data=f"device_{product_code}_{device}"
                )
            )

        bot.send_message(
            call.message.chat.id,
            "📱 CHỌN HỆ",
            reply_markup=markup
        )

    # DEVICE

    elif data.startswith("device_"):

        split_data = data.split("_")

        product_code = split_data[1]

        device = split_data[2]

        markup = InlineKeyboardMarkup()

        cursor.execute("""
        SELECT version
        FROM versions
        WHERE product_code=?
        AND device=?
        """, (
            product_code,
            device
        ))

        versions = cursor.fetchall()

        for version_data in versions:

            version = version_data[0]

            markup.row(
                InlineKeyboardButton(
                    version.upper(),
                    callback_data=f"version_{product_code}_{device}_{version}"
                )
            )

        bot.send_message(
            call.message.chat.id,
            "📦 CHỌN GÓI",
            reply_markup=markup
        )

    # VERSION

    elif data.startswith("version_"):

        split_data = data.split("_")

        product_code = split_data[1]

        device = split_data[2]

        version = split_data[3]

        markup = InlineKeyboardMarkup()

        time_list = [
            "gio",
            "ngay",
            "tuan",
            "thang"
        ]

        for time_name in time_list:

            full_package = f"{device}_{version}_{time_name}"

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

            if result:

                price = result[0]

                markup.row(
                    InlineKeyboardButton(
                        f"{time_name.upper()} - {price:,}đ",
                        callback_data=f"buy_{product_code}_{device}_{version}_{time_name}"
                    )
                )

        bot.send_message(
            call.message.chat.id,
            "⏰ CHỌN THỜI GIAN",
            reply_markup=markup
        )

    # BUY

    elif data.startswith("buy_"):

        split_data = data.split("_")

        product_code = split_data[1]

        device = split_data[2]

        version = split_data[3]

        time_name = split_data[4]

        full_package = f"{device}_{version}_{time_name}"

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
            full_package,
            amount,
            "pending"
        ))

        conn.commit()

        qr_url = f"https://img.vietqr.io/image/{BANK_NAME}-{BANK_NUMBER}-compact2.png?amount={amount}&addInfo={payment_code}&accountName={BANK_OWNER}"

        markup = InlineKeyboardMarkup()

        markup.row(
            InlineKeyboardButton(
                "🧾 CHECK THANH TOÁN",
                callback_data=f"check_{payment_code}"
            )
        )

        bot.send_photo(
            call.message.chat.id,
            qr_url,
            caption=f"""
📦 SẢN PHẨM: {product_code.upper()}

📱 HỆ: {device.upper()}

🎁 GÓI: {version.upper()}

⏰ THỜI GIAN: {time_name.upper()}

💰 GIÁ: {amount:,}đ

🏦 BANK: {BANK_NAME}

💳 STK: {BANK_NUMBER}

👤 CHỦ TK: {BANK_OWNER}

📌 NỘI DUNG:
{payment_code}
""",
            reply_markup=markup
        )

    # CHECK PAYMENT

    elif data.startswith("check_"):

        payment_code = data.replace(
            "check_",
            ""
        )

        check_payment(
            payment_code,
            call.message.chat.id
        )

# =========================================
# CHECK PAYMENT FUNCTION
# =========================================

def check_payment(payment_code, chat_id):

    headers = {
        "Authorization": f"Bearer {SEPAY_API_KEY}"
    }

    try:

        response = requests.get(
            "https://my.sepay.vn/userapi/transactions/list",
            headers=headers
        )

        data_json = response.json()

        for trans in data_json["data"]:

            content = str(
                trans.get(
                    "transaction_content",
                    ""
                )
            )

            if payment_code in content:

                cursor.execute("""
                SELECT *
                FROM orders
                WHERE payment_code=?
                """, (payment_code,))

                order = cursor.fetchone()

                if not order:
                    return

                if order[5] == "paid":
                    return

                amount = order[4]

                money = int(
                    trans.get(
                        "amount_in",
                        0
                    )
                )

                if money < amount:

                    bot.send_message(
                        chat_id,
                        "❌ THANH TOÁN THIẾU TIỀN"
                    )

                    return

                product_code = order[2]

                package = order[3]

                cursor.execute("""
                SELECT id, key_value
                FROM keys_data
                WHERE product_code=?
                AND package=?
                LIMIT 1
                """, (
                    product_code,
                    package
                ))

                key_data = cursor.fetchone()

                if not key_data:

                    bot.send_message(
                        chat_id,
                        "❌ HẾT KEY"
                    )

                    return

                key_id = key_data[0]

                key_value = key_data[1]

                # DELETE SOLD KEY

                cursor.execute("""
                DELETE FROM keys_data
                WHERE id=?
                """, (key_id,))

                # UPDATE ORDER

                cursor.execute("""
                UPDATE orders
                SET status='paid'
                WHERE payment_code=?
                """, (payment_code,))

                conn.commit()

                # GET LINK

                cursor.execute("""
                SELECT link
                FROM links
                WHERE product_code=?
                AND package=?
                """, (
                    product_code,
                    package
                ))

                link_data = cursor.fetchone()

                download_link = "Không có link"

                if link_data:
                    download_link = link_data[0]

                bot.send_message(
                    chat_id,
                    f"""
✅ THANH TOÁN THÀNH CÔNG

🔑 KEY:
{key_value}

🔗 LINK:
{download_link}
"""
                )

                return

        bot.send_message(
            chat_id,
            "❌ CHƯA THANH TOÁN"
        )

    except Exception as e:

        bot.send_message(
            chat_id,
            f"❌ LỖI:\n{e}"
        )

# =========================================
# AUTO CHECK PAYMENT
# =========================================

def auto_check_payment():

    while True:

        try:

            cursor.execute("""
            SELECT payment_code, chat_id
            FROM orders
            WHERE status='pending'
            """)

            orders = cursor.fetchall()

            for order in orders:

                payment_code = order[0]

                chat_id = order[1]

                check_payment(
                    payment_code,
                    chat_id
                )

        except:
            pass

        time.sleep(CHECK_TIME)

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

        device = split_text[2]

        version = split_text[3]

        time_name = split_text[4]

        key_value = split_text[5]

        full_package = f"{device}_{version}_{time_name}"

        cursor.execute("""
        DELETE FROM keys_data
        WHERE product_code=?
        AND package=?
        AND key_value=?
        """, (
            product_code,
            full_package,
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
            "❌ /delkey game device version time key"
        )

# =========================================
# COUNT KEY
# =========================================

@bot.message_handler(commands=['keycount'])
def keycount(message):

    if message.from_user.id != ADMIN_ID:
        return

    try:

        split_text = message.text.split()

        product_code = split_text[1]

        device = split_text[2]

        version = split_text[3]

        time_name = split_text[4]

        full_package = f"{device}_{version}_{time_name}"

        cursor.execute("""
        SELECT COUNT(*)
        FROM keys_data
        WHERE product_code=?
        AND package=?
        """, (
            product_code,
            full_package
        ))

        count = cursor.fetchone()[0]

        bot.reply_to(
            message,
            f"🔑 SỐ KEY: {count}"
        )

    except:

        bot.reply_to(
            message,
            "❌ /keycount game device version time"
        )

# =========================================
# GET ID
# =========================================

@bot.message_handler(commands=['id'])
def getid(message):

    bot.reply_to(
        message,
        f"🆔 ID: {message.chat.id}"
    )

# =========================================
# RUN BOT
# =========================================

threading.Thread(
    target=lambda: bot.infinity_polling(
        skip_pending=True
    )
).start()

threading.Thread(
    target=auto_check_payment
).start()

# =========================================
# FLASK
# =========================================

@app.route("/")
def home():
    return "BOT ONLINE"

PORT = int(
    os.environ.get(
        "PORT",
        3000
    )
)

app.run(
    host="0.0.0.0",
    port=PORT
)
