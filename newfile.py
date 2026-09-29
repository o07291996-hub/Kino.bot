import sqlite3
import logging
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# =========================
# SOZLAMALAR
# =========================

BOT_TOKEN = "8280467806:AAGCUKMoQL0c72I1bVV6XGZBfU5m0hz4r0g"

ADMIN_ID = 8630306390

CHANNEL = "@Uz1000XilElon"

DB = "kinolar.db"


# =========================
# DATABASE
# =========================

db = sqlite3.connect(DB, check_same_thread=False)        
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS movies (
    code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    file_id TEXT NOT NULL,
    views INTEGER DEFAULT 0,
    created_at TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY
)
""")

db.commit()


# =========================
# USER SAQLASH
# =========================

def save_user(user_id):
    cur.execute(
        "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
        (user_id,)
    )
    db.commit()


# =========================
# OBUNA
# =========================

async def is_subscribed(user_id, context):

    try:
        member = await context.bot.get_chat_member(
            chat_id=CHANNEL,
            user_id=user_id
        )

        return member.status not in ("left", "kicked")

    except Exception as e:
        print("OBUNA XATOSI:", e)
        return False


def sub_buttons():

    keyboard = [
        [
            InlineKeyboardButton(
                "📢 Kanalga obuna bo‘lish",
                url="https://t.me/Uz1000XilElon"
            )
        ],
        [
            InlineKeyboardButton(
                "✅ Tekshirish",
                callback_data="check"
            )
        ]
    ]

    return InlineKeyboardMarkup(keyboard)


# =========================
# KINO YUBORISH
# =========================

async def send_movie(message, code):

    cur.execute(
        "SELECT name, file_id FROM movies WHERE code = ?",
        (code,)
    )

    movie = cur.fetchone()

    if movie is None:

        await message.reply_text(
            "❌ Bunday kino topilmadi.\n\n"
            "🔢 Kino kodini tekshiring."
        )

        return

    name, file_id = movie

    cur.execute(
        """
        UPDATE movies
        SET views = views + 1
        WHERE code = ?
        """,
        (code,)
    )

    db.commit()

    await message.reply_video(
        video=file_id,
        caption=(
            f"🎬 {name}\n\n"
            f"🔢 Kod: {code}"
        )
    )


# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    save_user(user_id)

    # /start 101
    if context.args:

        code = context.args[0]

        if not await is_subscribed(user_id, context):

            await update.message.reply_text(
                "🎬 Kino olish uchun kanalga obuna bo‘ling.",
                reply_markup=sub_buttons()
            )

            return

        await send_movie(
            update.message,
            code
        )

        return

    # ADMIN
    if user_id == ADMIN_ID:

        await update.message.reply_text(
            "👑 ADMIN PANEL\n\n"
            "🎬 Kino qo‘shish uchun VIDEO yuboring.\n\n"
            "Keyin bot nomini va kodini so‘raydi.\n\n"
            "📌 Buyruqlar:\n"
            "/list - kinolar\n"
            "/stats - statistika\n"
            "/delete 101 - o‘chirish\n"
            "/rename 101 - nomini o‘zgartirish\n"
            "/code 101 202 - kodni almashtirish\n"
            "/backup - baza nusxasi\n"
            "/cancel - bekor qilish"
        )

        return

    # ODDIY USER

    if not await is_subscribed(user_id, context):

        await update.message.reply_text(
            "🎬 Kino botiga xush kelibsiz!\n\n"
            "Avval kanalga obuna bo‘ling 👇",
            reply_markup=sub_buttons()
        )

        return

    await update.message.reply_text(
        "🔢 Kino kodini yuboring.\n\n"
        "Masalan: 101"
    )


# =========================
# OBUNANI TEKSHIRISH
# =========================

async def check_subscription(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id

    if not await is_subscribed(user_id, context):

        await query.message.reply_text(
            "❌ Siz hali kanalga obuna bo‘lmagansiz.",
            reply_markup=sub_buttons()
        )

        return

    await query.message.reply_text(
        "✅ Obuna tasdiqlandi!\n\n"
        "🔢 Kino kodini yuboring."
    )


# =========================
# ADMIN VIDEO
# =========================

async def admin_video(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.effective_user.id != ADMIN_ID:
        return

    file_id = update.message.video.file_id

    context.user_data["file_id"] = file_id
    context.user_data["step"] = "name"

    await update.message.reply_text(
        "🎬 VIDEO QABUL QILINDI!\n\n"
        "📝 Kino nomini yozing."
    )


# =========================
# ADMIN MATN
# =========================

async def text_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.message is None:
        return

    text = update.message.text.strip()

    user_id = update.effective_user.id

    save_user(user_id)

    # =====================
    # ADMIN
    # =====================

    if user_id == ADMIN_ID:

        step = context.user_data.get("step")

        # KINO NOMI
        if step == "name":

            context.user_data["name"] = text
            context.user_data["step"] = "code"

            await update.message.reply_text(
                "📝 Nom qabul qilindi.\n\n"
                "🔢 Endi kino kodini yozing.\n\n"
                "Masalan: 101"
            )

            return

        # KINO KODI
        if step == "code":

            if not text.isdigit():

                await update.message.reply_text(
                    "❌ Kod faqat raqam bo‘lishi kerak.\n\n"
                    "Masalan: 101"
                )

                return

            file_id = context.user_data.get("file_id")
            name = context.user_data.get("name")

            if file_id is None or name is None:

                context.user_data.clear()

                await update.message.reply_text(
                    "❌ Ma'lumot yo‘qoldi.\n"
                    "Iltimos, videoni qaytadan yuboring."
                )

                return

            now = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            cur.execute(
                """
                INSERT OR REPLACE INTO movies
                (code, name, file_id, views, created_at)
                VALUES (?, ?, ?, 0, ?)
                """,
                (
                    text,
                    name,
                    file_id,
                    now
                )
            )

            db.commit()

            context.user_data.clear()

            await update.message.reply_text(
                "✅ KINO SAQLANDI!\n\n"
                f"🎬 {name}\n"
                f"🔢 Kod: {text}\n\n"
                "Boshqa akkauntdan shu kodni yuborib "
                "videoni olishingiz mumkin."
            )

            return

        # NOMNI O‘ZGARTIRISH
        rename_code = context.user_data.get("rename")

        if rename_code:

            cur.execute(
                """
                UPDATE movies
                SET name = ?
                WHERE code = ?
                """,
                (
                    text,
                    rename_code
                )
            )

            db.commit()

            context.user_data.clear()

            await update.message.reply_text(
                "✅ Kino nomi o‘zgartirildi."
            )

            return

    # =====================
    # USER
    # =====================

    if not await is_subscribed(user_id, context):

        await update.message.reply_text(
            "❌ Avval kanalga obuna bo‘ling.",
            reply_markup=sub_buttons()
        )

        return

    await send_movie(
        update.message,
        text
    )


# =========================
# DELETE
# =========================

async def delete_movie(update, context):

    if update.effective_user.id != ADMIN_ID:
        return

    if len(context.args) != 1:

        await update.message.reply_text(
            "Masalan:\n"
            "/delete 101"
        )

        return

    code = context.args[0]

    cur.execute(
        "DELETE FROM movies WHERE code = ?",
        (code,)
    )

    db.commit()

    await update.message.reply_text(
        "🗑️ Kino o‘chirildi: " + code
    )


# =========================
# LIST
# =========================

async def movie_list(update, context):

    if update.effective_user.id != ADMIN_ID:
        return

    cur.execute(
        """
        SELECT code, name, views
        FROM movies
        ORDER BY created_at DESC
        """
    )

    rows = cur.fetchall()

    if not rows:

        await update.message.reply_text(
            "📭 Hozircha kino yo‘q."
        )

        return

    text = "📋 KINOLAR:\n\n"

    for code, name, views in rows:

        text += (
            f"🔢 {code}\n"
            f"🎬 {name}\n"
            f"👁 {views}\n\n"
        )

    await update.message.reply_text(text)


# =========================
# STATS
# =========================

async def stats(update, context):

    if update.effective_user.id != ADMIN_ID:
        return

    cur.execute(
        "SELECT COUNT(*) FROM users"
    )

    users = cur.fetchone()[0]

    cur.execute(
        "SELECT COUNT(*) FROM movies"
    )

    movies = cur.fetchone()[0]

    cur.execute(
        "SELECT SUM(views) FROM movies"
    )

    views = cur.fetchone()[0] or 0

    await update.message.reply_text(
        "📊 STATISTIKA\n\n"
        f"👥 Foydalanuvchilar: {users}\n"
        f"🎬 Kinolar: {movies}\n"
        f"👁 Ko‘rishlar: {views}"
    )


# =========================
# RENAME
# =========================

async def rename_movie(update, context):

    if update.effective_user.id != ADMIN_ID:
        return

    if len(context.args) != 1:

        await update.message.reply_text(
            "Masalan:\n"
            "/rename 101"
        )

        return

    code = context.args[0]

    cur.execute(
        "SELECT name FROM movies WHERE code = ?",
        (code,)
    )

    result = cur.fetchone()

    if result is None:

        await update.message.reply_text(
            "❌ Kino topilmadi."
        )

        return

    context.user_data["rename"] = code

    await update.message.reply_text(
        "📝 Yangi kino nomini yozing."
    )


# =========================
# CODE O‘ZGARTIRISH
# =========================

async def change_code(update, context):

    if update.effective_user.id != ADMIN_ID:
        return

    if len(context.args) != 2:

        await update.message.reply_text(
            "Masalan:\n"
            "/code 101 202"
        )

        return

    old = context.args[0]
    new = context.args[1]

    cur.execute(
        """
        UPDATE movies
        SET code = ?
        WHERE code = ?
        """,
        (
            new,
            old
        )
    )

    db.commit()

    await update.message.reply_text(
        "✅ Kod o‘zgartirildi."
    )


# =========================
# BACKUP
# =========================

async def backup(update, context):

    if update.effective_user.id != ADMIN_ID:
        return

    with open(DB, "rb") as f:

        await update.message.reply_document(
            document=f,
            caption="💾 Kino bazasi"
        )


# =========================
# CANCEL
# =========================

async def cancel(update, context):

    if update.effective_user.id != ADMIN_ID:
        return

    context.user_data.clear()

    await update.message.reply_text(
        "❌ Bekor qilindi."
    )


# =========================
# ERROR
# =========================

async def error_handler(update, context):

    print(
        "XATO:",
        context.error
    )


# =========================
# MAIN
# =========================

def main():

    logging.basicConfig(
        level=logging.INFO
    )

    app = Application.builder().token(
        BOT_TOKEN
    ).build()

    # START
    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    # ADMIN BUYRUQLARI
    app.add_handler(
        CommandHandler(
            "delete",
            delete_movie
        )
    )

    app.add_handler(
        CommandHandler(
            "list",
            movie_list
        )
    )

    app.add_handler(
        CommandHandler(
            "stats",
            stats
        )
    )

    app.add_handler(
        CommandHandler(
            "rename",
            rename_movie
        )
    )

    app.add_handler(
        CommandHandler(
            "code",
            change_code
        )
    )

    app.add_handler(
        CommandHandler(
            "backup",
            backup
        )
    )

    app.add_handler(
        CommandHandler(
            "cancel",
            cancel
        )
    )

    # OBUNA
    app.add_handler(
        CallbackQueryHandler(
            check_subscription,
            pattern="^check$"
        )
    )

    # ADMIN VIDEO
    app.add_handler(
        MessageHandler(
            filters.VIDEO,
            admin_video
        )
    )

    # MATN
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_handler
        )
    )

    app.add_error_handler(
        error_handler
    )

    print("🤖 BOT ISHLAYAPTI!")

    app.run_polling()


if __name__ == "__main__":
    main()