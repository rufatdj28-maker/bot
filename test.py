"""
==================================================================
TEST BOTI — Telegram tomoni
==================================================================

Bu fayl endi juda sodda: faqat Mini App'ni ochish tugmasini beradi
va reytingni ko'rsatadi. Savollar, natijalar, admin panel — hammasi
backend (app.py) serverida joylashgan.

BU FAYLNI ISHGA TUSHIRISHDAN OLDIN TO'LDIRING:
    1) BOT_TOKEN   — @BotFather'dan olgan token
    2) WEBAPP_URL  — backend'ni Render.com'ga joylashtirgach olgan
                      manzil (masalan: https://test-bot-backend.onrender.com)
                      DEPLOY_YORIQNOMA.txt faylida to'liq ko'rsatma bor

O'RNATISH:
    pip install python-telegram-bot requests --upgrade

ISHGA TUSHIRISH:
    python test_bot.py

BUYRUQLAR:
    /start         — testni ochish tugmasini beradi
    /test          — testni ochish tugmasini beradi
    /reyting       — eng yaxshi 10 ta natija
    /natijalarim   — sizning oxirgi natijalaringiz
    /admin         — admin panel havolasini beradi
"""

import logging

import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ==================================================================
# SOZLASH — FAQAT SHU 2 QATORNI TO'LDIRING
# ==================================================================
BOT_TOKEN = "8959834004:AAEk4ZNUw21Kez7rlDqv87PpE2qF3qyFz_I"      # <-- @BotFather'dan olgan tokenni qo'ying
WEBAPP_URL = "https://bot-ot19.onrender.com/"     # <-- backend manzilingiz, masalan: "https://test-bot-backend.onrender.com"

# ==================================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def webapp_keyboard():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🚀 Testni boshlash", web_app=WebAppInfo(url=WEBAPP_URL))]]
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not WEBAPP_URL:
        await update.message.reply_text(
            "⚠️ WEBAPP_URL hali sozlanmagan. Fayl boshidagi yo'riqnomaga qarang."
        )
        return
    await update.message.reply_text(
        "👋 Assalomu alaykum!\n\n"
        "Bu — bilim testi boti.\n"
        "Testni boshlash uchun quyidagi tugmani bosing.\n\n"
        "Reytingni ko'rish uchun /reyting.\n"
        "O'z natijalaringizni ko'rish uchun /natijalarim.",
        reply_markup=webapp_keyboard(),
    )


async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not WEBAPP_URL:
        await update.message.reply_text(
            "⚠️ WEBAPP_URL hali sozlanmagan. Fayl boshidagi yo'riqnomaga qarang."
        )
        return
    await update.message.reply_text(
        "Testni boshlash uchun tugmani bosing 👇",
        reply_markup=webapp_keyboard(),
    )


async def reyting_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not WEBAPP_URL:
        await update.message.reply_text("⚠️ WEBAPP_URL hali sozlanmagan.")
        return
    try:
        resp = requests.get(f"{WEBAPP_URL}/api/leaderboard", timeout=10)
        rows = resp.json()
    except Exception as e:
        logger.error("Reytingni olishda xatolik: %s", e)
        await update.message.reply_text("Reytingni yuklab bo'lmadi. Birozdan keyin qayta urinib ko'ring.")
        return

    if not rows:
        await update.message.reply_text("Hozircha hech kim test ishlamagan.")
        return

    medals = ["🥇", "🥈", "🥉"]
    lines = ["🏆 Eng yaxshi natijalar:\n"]
    for i, row in enumerate(rows):
        prefix = medals[i] if i < 3 else f"{i + 1}."
        lines.append(
            f"{prefix} {row['username']} — {row['best_score']} ball ({row['correct']}/{row['total']} to'g'ri)"
        )

    await update.message.reply_text("\n".join(lines))


async def natijalarim_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not WEBAPP_URL:
        await update.message.reply_text("⚠️ WEBAPP_URL hali sozlanmagan.")
        return
    try:
        resp = requests.get(
            f"{WEBAPP_URL}/api/user_results",
            params={"user_id": update.effective_user.id},
            timeout=10,
        )
        rows = resp.json()
    except Exception as e:
        logger.error("Natijalarni olishda xatolik: %s", e)
        await update.message.reply_text("Natijalarni yuklab bo'lmadi. Birozdan keyin qayta urinib ko'ring.")
        return

    if not rows:
        await update.message.reply_text("Siz hali test ishlamagansiz. /test buyrug'i bilan boshlang.")
        return

    lines = ["📊 Sizning so'nggi natijalaringiz:\n"]
    for row in rows:
        date_str = row["created_at"].split("T")[0]
        m, s = divmod(row["elapsed_seconds"], 60)
        lines.append(
            f"• {date_str}: {row['score']} ball, {row['correct']}/{row['total']} to'g'ri, {m}:{s:02d}"
        )

    await update.message.reply_text("\n".join(lines))


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not WEBAPP_URL:
        await update.message.reply_text("⚠️ WEBAPP_URL hali sozlanmagan.")
        return
    await update.message.reply_text(
        f"👑 Admin panel:\n{WEBAPP_URL}/admin\n\n"
        f"U yerda yangi savol qo'shish, savollarni o'chirish va barcha "
        f"natijalarni ko'rishingiz mumkin. Kirish uchun backend'da "
        f"o'rnatgan ADMIN_PASSWORD'dan foydalaning."
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Xatolik yuz berdi: %s", context.error)


def main():
    if not BOT_TOKEN:
        print("XATOLIK: BOT_TOKEN bo'sh! Faylning yuqori qismida to'ldiring.")
        return
    if not WEBAPP_URL:
        print("OGOHLANTIRISH: WEBAPP_URL bo'sh! Avval backend'ni deploy qiling (DEPLOY_YORIQNOMA.txt).")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("test", test_command))
    app.add_handler(CommandHandler("reyting", reyting_command))
    app.add_handler(CommandHandler("natijalarim", natijalarim_command))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_error_handler(error_handler)

    logger.info("Test bot ishga tushdi...")
    app.run_polling()


if __name__ == "__main__":
    main()
