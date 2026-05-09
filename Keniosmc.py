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

# =========================================
# CHECK PAYMENT
# =========================================

elif data.startswith("check_"):

    payment_code = data.replace(
        "check_",
        ""
    )

    headers = {
        "Authorization": f"Bearer {SEPAY_API_KEY}"
    }

    try:

        response = requests.get(
            "https://my.sepay.vn/userapi/transactions/list",
            headers=headers,
            timeout=30
        )

        print(response.text)

        data_json = response.json()

        found = False

        transactions = data_json.get("transactions", [])

        # Nếu transactions rỗng
        # thử data

        if not transactions:

            transactions = data_json.get("data", [])

        for trans in transactions:

            content = str(
                trans.get(
                    "transaction_content",
                    ""
                )
            )

            print(content)

            if payment_code in content:

                found = True

                cursor.execute("""
                SELECT *
                FROM orders
                WHERE payment_code=?
                """, (payment_code,))

                order = cursor.fetchone()

                if not order:

                    bot.answer_callback_query(
                        call.id,
                        "❌ KHÔNG TÌM THẤY ĐƠN"
                    )

                    return

                product_code = order[2]

                package = order[3]

                # GET KEY

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
                        call.message.chat.id,
                        "❌ HẾT KEY"
                    )

                    return

                key_id = key_data[0]

                key_value = key_data[1]

                # XOÁ KEY ĐÃ BÁN

                cursor.execute("""
                DELETE FROM keys_data
                WHERE id=?
                """, (key_id,))

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

                bot.answer_callback_query(
                    call.id,
                    "✅ THANH TOÁN THÀNH CÔNG"
                )

                bot.send_message(
                    call.message.chat.id,
                    f"""
✅ THANH TOÁN THÀNH CÔNG

🔑 KEY:
{key_value}

🔗 LINK:
{download_link}
"""
                )

                return

        if not found:

            bot.answer_callback_query(
                call.id,
                "❌ CHƯA THANH TOÁN"
            )

    except Exception as e:

        print(e)

        bot.answer_callback_query(
            call.id,
            f"LỖI: {e}"
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
# ADD DEVICE
# =========================================

@bot.message_handler(commands=['adddevice'])
def adddevice(message):

    if message.from_user.id != ADMIN_ID:
        return

    try:

        split_text = message.text.split()

        product_code = split_text[1]

        device = split_text[2]

        cursor.execute("""
        INSERT INTO devices
        VALUES (?, ?)
        """, (
            product_code,
            device
        ))

        conn.commit()

        bot.reply_to(
            message,
            "✅ ĐÃ THÊM HỆ"
        )

    except:

        bot.reply_to(
            message,
            "❌ /adddevice game device"
        )

# =========================================
# ADD VERSION
# =========================================

@bot.message_handler(commands=['addversion'])
def addversion(message):

    if message.from_user.id != ADMIN_ID:
        return

    try:

        split_text = message.text.split()

        product_code = split_text[1]

        device = split_text[2]

        version = split_text[3]

        cursor.execute("""
        INSERT INTO versions
        VALUES (?, ?, ?)
        """, (
            product_code,
            device,
            version
        ))

        conn.commit()

        bot.reply_to(
            message,
            "✅ ĐÃ THÊM GÓI"
        )

    except:

        bot.reply_to(
            message,
            "❌ /addversion game device version"
        )

# =========================================
# SET PRICE
# =========================================

@bot.message_handler(commands=['setprice'])
def setprice(message):

    if message.from_user.id != ADMIN_ID:
        return

    try:

        split_text = message.text.split()

        product_code = split_text[1]

        device = split_text[2]

        version = split_text[3]

        time_name = split_text[4]

        price = int(split_text[5])

        full_package = f"{device}_{version}_{time_name}"

        cursor.execute("""
        DELETE FROM prices
        WHERE product_code=?
        AND package=?
        """, (
            product_code,
            full_package
        ))

        cursor.execute("""
        INSERT INTO prices
        VALUES (?, ?, ?)
        """, (
            product_code,
            full_package,
            price
        ))

        conn.commit()

        bot.reply_to(
            message,
            "✅ ĐÃ SET GIÁ"
        )

    except:

        bot.reply_to(
            message,
            "❌ /setprice game device version time gia"
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

        device = split_text[2]

        version = split_text[3]

        time_name = split_text[4]

        key_value = split_text[5]

        full_package = f"{device}_{version}_{time_name}"

        cursor.execute("""
        INSERT INTO keys_data(
            product_code,
            package,
            key_value
        )
        VALUES (?, ?, ?)
        """, (
            product_code,
            full_package,
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
            "❌ /addkey game device version time key"
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

        device = split_text[2]

        version = split_text[3]

        time_name = split_text[4]

        link = split_text[5]

        full_package = f"{device}_{version}_{time_name}"

        cursor.execute("""
        DELETE FROM links
        WHERE product_code=?
        AND package=?
        """, (
            product_code,
            full_package
        ))

        cursor.execute("""
        INSERT INTO links
        VALUES (?, ?, ?)
        """, (
            product_code,
            full_package,
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
            "❌ /setlink game device version time link"
        )

# =========================================
# RENAME VERSION
# =========================================

@bot.message_handler(commands=['renameversion'])
def renameversion(message):

    if message.from_user.id != ADMIN_ID:
        return

    try:

        split_text = message.text.split()

        old_version = split_text[1]

        new_version = split_text[2]

        cursor.execute("""
        UPDATE versions
        SET version=?
        WHERE version=?
        """, (
            new_version,
            old_version
        ))

        conn.commit()

        bot.reply_to(
            message,
            "✅ ĐÃ ĐỔI TÊN GÓI"
        )

    except:

        bot.reply_to(
            message,
            "❌ /renameversion old new"
        )

# =========================================
# DELETE VERSION
# =========================================

@bot.message_handler(commands=['delversion'])
def delversion(message):

    if message.from_user.id != ADMIN_ID:
        return

    try:

        split_text = message.text.split()

        version = split_text[1].lower()

        cursor.execute("""
        DELETE FROM versions
        WHERE LOWER(version)=?
        """, (version,))

        cursor.execute("""
        DELETE FROM prices
        WHERE LOWER(package) LIKE ?
        """, (
            f"%_{version}_%",
        ))

        cursor.execute("""
        DELETE FROM keys_data
        WHERE LOWER(package) LIKE ?
        """, (
            f"%_{version}_%",
        ))

        cursor.execute("""
        DELETE FROM links
        WHERE LOWER(package) LIKE ?
        """, (
            f"%_{version}_%",
        ))

        conn.commit()

        bot.reply_to(
            message,
            "✅ ĐÃ XOÁ GÓI"
        )

    except Exception as e:

        bot.reply_to(
            message,
            f"❌ LỖI:\n{e}"
        )
        
# =========================================
# DELETE KEY
# =========================================

@bot.message_handler(commands=['delkey'])
def delkey(message):

    # CHECK ADMIN

    if message.from_user.id != ADMIN_ID:

        bot.reply_to(
            message,
            "❌ KHÔNG CÓ QUYỀN"
        )

        return

    try:

        split_text = message.text.split()

        # /delkey pubg ios vipgold thang VIP123

        product_code = split_text[1]

        device = split_text[2]

        version = split_text[3]

        time_name = split_text[4]

        key_value = split_text[5]

        # PACKAGE

        full_package = f"{device}_{version}_{time_name}"

        # CHECK KEY

        cursor.execute("""
        SELECT *
        FROM keys_data
        WHERE product_code=?
        AND package=?
        AND key_value=?
        """, (
            product_code,
            full_package,
            key_value
        ))

        result = cursor.fetchone()

        # NOT FOUND

        if not result:

            bot.reply_to(
                message,
                "❌ KHÔNG TÌM THẤY KEY"
            )

            return

        # DELETE KEY

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
            f"""
✅ ĐÃ XOÁ KEY

🎮 GAME:
{product_code}

📱 HỆ:
{device}

📦 GÓI:
{version}

⏰ THỜI GIAN:
{time_name}

🔑 KEY:
{key_value}
"""
        )

    except Exception as e:

        bot.reply_to(
            message,
            f"""
❌ LỖI XOÁ KEY

{e}
"""
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
