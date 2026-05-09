# =========================================================
# REQUIRE:
# pip install pytelegrambotapi flask requests
# =========================================================

from flask import Flask
from telebot import TeleBot
from telebot.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

import sqlite3
import threading
import random
import string
import requests
import time

# =========================================================
# CONFIG
# =========================================================

_TOKEN = "8712999576:AAGpRyiWBvzrqNPVSfoT9em9rtNJv9nuA4k"

SEPAY_API_KEY = "UMRLQBWEP5ZMBIJDTWR0KUCFRLUMFXGWGZUSIP9DVND3LJCP6SZ2DESJY19HVTAK"

ADMIN_ID = 8126773907

BANK_NAME = "MSB"

BANK_NUMBER = "80003122324"

BANK_OWNER = "TRAN MINH CHIEN"

CHECK_TIME = 10

# =========================================================
# BOT + FLASK
# =========================================================

bot = TeleBot(BOT_TOKEN)

app = Flask(__name__)

# =========================================================
# DATABASE
# =========================================================

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

# =========================================================
# FUNCTIONS
# =========================================================

def create_payment_code():

    return "PAY" + ''.join(
        random.choices(
            string.digits,
            k=6
        )
    )


def get_key(product_code, package):

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

    result = cursor.fetchone()

    if not result:
        return None

    key_id = result[0]

    key_value = result[1]

    cursor.execute("""
    DELETE FROM keys_data
    WHERE id=?
    """, (key_id,))

    conn.commit()

    return key_value


def get_link(product_code, package):

    cursor.execute("""
    SELECT link
    FROM links
    WHERE product_code=?
    AND package=?
    """, (
        product_code,
        package
    ))

    result = cursor.fetchone()

    if result:
        return result[0]

    return None


def payment_success(payment_code):

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

    chat_id = order[1]

    product_code = order[2]

    package = order[3]

    amount = order[4]

    cursor.execute("""
    UPDATE orders
    SET status='paid'
    WHERE payment_code=?
    """, (payment_code,))

    conn.commit()

    key_data = get_key(
        product_code,
        package
    )

    download_link = get_link(
        product_code,
        package
    )

    text = f"""
✅ THANH TOÁN THÀNH CÔNG

📦 SẢN PHẨM:
{product_code.upper()}

💰 SỐ TIỀN:
{amount:,}đ

📌 MÃ ĐƠN:
{payment_code}
"""

    if key_data:

        text += f"""

🔑 KEY:
{key_data}
"""

    if download_link:

        text += f"""

📥 LINK TẢI:
{download_link}
"""

    bot.send_message(
        chat_id,
        text
    )

    bot.send_message(
        ADMIN_ID,
        f"""
💸 CÓ THANH TOÁN MỚI

👤 USER:
{chat_id}

📦 PRODUCT:
{product_code}

💰:
{amount:,}đ
"""
    )

# =========================================================
# START
# =========================================================

@bot.message_handler(commands=['start'])
def start(message):

    markup = InlineKeyboardMarkup()

    cursor.execute("""
    SELECT *
    FROM products
    WHERE status=1
    """)

    products = cursor.fetchall()

    if not products:

        bot.send_message(
            message.chat.id,
            "❌ CHƯA CÓ SẢN PHẨM"
        )

        return

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
📥 GIAO FILE TỰ ĐỘNG
""",
        reply_markup=markup
    )

# =========================================================
# CALLBACK
# =========================================================

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

        payment_code = create_payment_code()

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

        qr_url = (
            f"https://img.vietqr.io/image/"
            f"{BANK_NAME}-{BANK_NUMBER}-compact2.png"
            f"?amount={amount}"
            f"&addInfo={payment_code}"
            f"&accountName={BANK_OWNER}"
        )

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
📦 SẢN PHẨM:
{product_code.upper()}

📱 HỆ:
{device.upper()}

🎁 GÓI:
{version.upper()}

⏰ THỜI GIAN:
{time_name.upper()}

💰 GIÁ:
{amount:,}đ

🏦 BANK:
{BANK_NAME}

💳 STK:
{BANK_NUMBER}

👤 CHỦ TK:
{BANK_OWNER}

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

        try:

            headers = {
                "Authorization": f"Bearer {SEPAY_API_KEY}"
            }

            response = requests.get(
                "https://my.sepay.vn/userapi/transactions/list?limit=20",
                headers=headers,
                timeout=20
            )

            if response.status_code != 200:

                bot.answer_callback_query(
                    call.id,
                    "❌ API ERROR"
                )

                return

            data_json = response.json()

            transactions = data_json.get(
                "transactions",
                []
            )

            paid = False

            for trans in transactions:

                content = str(
                    trans.get(
                        "transaction_content",
                        ""
                    )
                ).strip()

                amount_in = int(
                    trans.get(
                        "amount_in",
                        0
                    )
                )

                cursor.execute("""
                SELECT amount, status
                FROM orders
                WHERE payment_code=?
                """, (payment_code,))

                order = cursor.fetchone()

                if not order:
                    break

                order_amount = order[0]

                order_status = order[1]

                if order_status == "paid":

                    bot.answer_callback_query(
                        call.id,
                        "✅ ĐÃ THANH TOÁN"
                    )

                    return

                if (
                    payment_code in content
                    and amount_in >= order_amount
                ):

                    payment_success(payment_code)

                    bot.answer_callback_query(
                        call.id,
                        "✅ THANH TOÁN THÀNH CÔNG"
                    )

                    paid = True

                    break

            if not paid:

                bot.answer_callback_query(
                    call.id,
                    "❌ CHƯA THANH TOÁN"
                )

        except Exception as e:

            print(e)

            bot.answer_callback_query(
                call.id,
                "❌ LỖI CHECK"
            )

# =========================================================
# ADMIN COMMAND
# =========================================================

@bot.message_handler(commands=['addproduct'])
def add_product(message):

    if message.chat.id != ADMIN_ID:
        return

    try:

        split_data = message.text.split("|")

        product_code = split_data[1]

        display_name = split_data[2]

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
            "✅ ĐÃ THÊM PRODUCT"
        )

    except:

        bot.reply_to(
            message,
            "/addproduct|code|name"
        )

# =========================================================
# ADD KEY
# =========================================================

@bot.message_handler(commands=['addkey'])
def add_key(message):

    if message.chat.id != ADMIN_ID:
        return

    try:

        split_data = message.text.split("|")

        product_code = split_data[1]

        package = split_data[2]

        key_value = split_data[3]

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
            "/addkey|product|package|key"
        )

# =========================================================
# DELETE KEY
# =========================================================

@bot.message_handler(commands=['delkey'])
def delete_key(message):

    if message.chat.id != ADMIN_ID:
        return

    try:

        split_data = message.text.split("|")

        product_code = split_data[1]

        package = split_data[2]

        key_value = split_data[3]

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

        if cursor.rowcount > 0:

            bot.reply_to(
                message,
                "✅ ĐÃ XÓA KEY"
            )

        else:

            bot.reply_to(
                message,
                "❌ KHÔNG TÌM THẤY KEY"
            )

    except:

        bot.reply_to(
            message,
            "/delkey|product|package|key"
        )

# =========================================================
# DELETE ALL KEY
# =========================================================

@bot.message_handler(commands=['delallkey'])
def delete_all_key(message):

    if message.chat.id != ADMIN_ID:
        return

    try:

        split_data = message.text.split("|")

        product_code = split_data[1]

        package = split_data[2]

        cursor.execute("""
        DELETE FROM keys_data
        WHERE product_code=?
        AND package=?
        """, (
            product_code,
            package
        ))

        conn.commit()

        bot.reply_to(
            message,
            "✅ ĐÃ XÓA TOÀN BỘ KEY"
        )

    except:

        bot.reply_to(
            message,
            "/delallkey|product|package"
        )

# =========================================================
# KEY COUNT
# =========================================================

@bot.message_handler(commands=['keycount'])
def key_count(message):

    if message.chat.id != ADMIN_ID:
        return

    try:

        split_data = message.text.split("|")

        product_code = split_data[1]

        package = split_data[2]

        cursor.execute("""
        SELECT COUNT(*)
        FROM keys_data
        WHERE product_code=?
        AND package=?
        """, (
            product_code,
            package
        ))

        count = cursor.fetchone()[0]

        bot.reply_to(
            message,
            f"🔑 SỐ KEY: {count}"
        )

    except:

        bot.reply_to(
            message,
            "/keycount|product|package"
        )

# =========================================================
# FLASK
# =========================================================

@app.route("/")
def home():
    return "BOT ONLINE"

# =========================================================
# AUTO CHECK PAYMENT
# =========================================================

def auto_check_payment():

    while True:

        try:

            headers = {
                "Authorization": f"Bearer {SEPAY_API_KEY}"
            }

            response = requests.get(
                "https://my.sepay.vn/userapi/transactions/list?limit=20",
                headers=headers,
                timeout=20
            )

            if response.status_code == 200:

                data_json = response.json()

                transactions = data_json.get(
                    "transactions",
                    []
                )

                cursor.execute("""
                SELECT payment_code, amount
                FROM orders
                WHERE status='pending'
                """)

                orders = cursor.fetchall()

                for order in orders:

                    payment_code = order[0]

                    order_amount = order[1]

                    for trans in transactions:

                        content = str(
                            trans.get(
                                "transaction_content",
                                ""
                            )
                        )

                        amount_in = int(
                            trans.get(
                                "amount_in",
                                0
                            )
                        )

                        if (
                            payment_code in content
                            and amount_in >= order_amount
                        ):

                            payment_success(
                                payment_code
                            )

        except Exception as e:

            print(e)

        time.sleep(CHECK_TIME)

# =========================================================
# RUN
# =========================================================

threading.Thread(
    target=lambda: bot.infinity_polling(
        skip_pending=True
    )
).start()

threading.Thread(
    target=auto_check_payment
).start()

app.run(
    host="0.0.0.0",
    port=3000
)
