"""
==================================================================
TEST BOTI BACKEND — Flask server
==================================================================

BU SERVER NIMA QILADI:
    1) Testni (Mini App) veb-sahifa sifatida ko'rsatadi
    2) Savollarni ma'lumotlar bazasida saqlaydi — admin panel orqali
       istalgancha yangi savol qo'shish yoki o'chirish mumkin
    3) Test natijalarini qabul qilib saqlaydi (kim, qachon, necha ball)
    4) Admin panel: /admin manzilida — parol bilan himoyalangan,
       barcha natijalarni va savollarni boshqarish mumkin

BU SERVERNI QAYERDA ISHGA TUSHIRISH KERAK:
    Bu oddiy kompyuteringizda emas, balki INTERNETDA (hosting'da)
    ishlashi kerak — aks holda Telegram undan foydalana olmaydi.
    Bepul RENDER.COM xizmatidan foydalanish tavsiya etiladi.
    To'liq yo'riqnoma alohida DEPLOY_YORIQNOMA.txt faylida.

SOZLASH (pastdagi "SOZLASH" qismida):
    ADMIN_PASSWORD — admin panelga kirish uchun o'zingiz o'ylab topgan parol
    BOT_TOKEN      — @BotFather'dan olgan tokeningiz (Telegram
                     foydalanuvchisini xavfsiz tekshirish uchun kerak)
"""

import hashlib
import hmac
import json
import os
import sqlite3
import time
from datetime import datetime
from urllib.parse import parse_qsl

from flask import (
    Flask, request, jsonify, render_template,
    redirect, url_for, session, g
)

# ==================================================================
# SOZLASH
# ==================================================================
# Ishlab chiqarishda bu qiymatlarni Render.com sozlamalarida
# "Environment Variables" orqali kiritasiz (pastdagi yo'riqnomaga qarang).
# Shu yerdagilar faqat kompyuteringizda sinab ko'rish uchun zaxira qiymat.
ADMIN_PASSWORD = os.environ.get("2014", "admin")
BOT_TOKEN = os.environ.get("8959834004:AAEk4ZNUw21Kez7rlDqv87PpE2qF3qyFz_I", "")
SECRET_KEY = os.environ.get("mening_maxfiy_kalitim_2026_xyzabc123", "shu-yerga-tasodifiy-matn-yozing")

SCORE_PER_QUESTION = 5
TOTAL_TIME_SECONDS = 15 * 60
DB_PATH = os.environ.get("DB_PATH", "test_bot.db")

# ==================================================================

app = Flask(__name__)
app.secret_key = SECRET_KEY

DEFAULT_QUESTIONS = [
    {"q": "HTML nima uchun ishlatiladi?",
     "opts": ["Veb-sahifaning tuzilishini yaratish uchun", "Veb-sahifaga stil berish uchun",
              "Server bilan ishlash uchun", "Ma'lumotlar bazasini boshqarish uchun"],
     "correct": 0, "exp": "HTML veb-sahifaning tarkibi va tuzilishini belgilaydi."},
    {"q": "CSS qaysi so'zning qisqartmasi?",
     "opts": ["Colorful Style Sheets", "Cascading Style Sheets", "Computer Style Sheets", "Creative Style System"],
     "correct": 1, "exp": "CSS — Cascading Style Sheets."},
    {"q": "Eng katta sarlavha uchun qaysi teg ishlatiladi?",
     "opts": ["<title>", "<head>", "<h1>", "<header>"],
     "correct": 2, "exp": "<h1> eng katta va eng muhim sarlavha tegidir."},
    {"q": "Fon rangini o'zgartirish uchun qaysi CSS xususiyati ishlatiladi?",
     "opts": ["color", "background-color", "font-color", "border-color"],
     "correct": 1, "exp": "background-color elementning fon rangini belgilaydi."},
    {"q": "Rasm qo'yish uchun qaysi teg ishlatiladi?",
     "opts": ["<picture>", "<image>", "<img>", "<src>"],
     "correct": 2, "exp": "<img> tegi src atributi bilan rasm chiqaradi."},
    {"q": "Havola (link) yaratish uchun qaysi teg ishlatiladi?",
     "opts": ["<link>", "<a>", "<href>", "<url>"],
     "correct": 1, "exp": "<a> tegi href atributi bilan havola yaratadi."},
    {"q": "CSS faylini HTML sahifasiga ulash uchun qaysi teg ishlatiladi?",
     "opts": ["<style>", "<css>", "<link>", "<script>"],
     "correct": 2, "exp": "<link rel=\"stylesheet\"> tashqi CSS faylini ulaydi."},
    {"q": "Matn o'lchamini o'zgartirish uchun qaysi CSS xususiyati ishlatiladi?",
     "opts": ["text-size", "font-size", "text-style", "font-style"],
     "correct": 1, "exp": "font-size matn hajmini belgilaydi."},
    {"q": "HTML da tartibsiz ro'yxat uchun qaysi teg ishlatiladi?",
     "opts": ["<ol>", "<list>", "<ul>", "<li>"],
     "correct": 2, "exp": "<ul> tartibsiz ro'yxat, <li> uning ichidagi elementlar uchun."},
    {"q": "CSS selektorlarida class qanday belgilanadi?",
     "opts": ["# bilan", ". bilan", "@ bilan", "& bilan"],
     "correct": 1, "exp": "Class nuqta (.) bilan, id esa # bilan belgilanadi."},
    {"q": "CSS da id selektori qanday belgilanadi?",
     "opts": ["# bilan", ". bilan", "* bilan", "~ bilan"],
     "correct": 0, "exp": "id selektori # belgisi bilan yoziladi."},
    {"q": "Flexbox layout uchun display xususiyatiga qaysi qiymat beriladi?",
     "opts": ["flex", "block", "inline", "grid-flex"],
     "correct": 0, "exp": "display: flex; flexbox tizimini yoqadi."},
    {"q": "HTML jadval yaratish uchun asosiy teg qaysi?",
     "opts": ["<grid>", "<table>", "<tab>", "<list>"],
     "correct": 1, "exp": "<table> jadval yaratish uchun asosiy teg."},
    {"q": "CSS box modelida ichki bo'shliq qaysi xususiyat bilan belgilanadi?",
     "opts": ["margin", "padding", "border", "gap"],
     "correct": 1, "exp": "padding element ichidagi bo'shliqni, margin esa tashqi bo'shliqni belgilaydi."},
    {"q": "Elementlar orasidagi tashqi bo'shliq qaysi xususiyat bilan belgilanadi?",
     "opts": ["padding", "spacing", "margin", "outline"],
     "correct": 2, "exp": "margin elementning tashqi bo'shlig'ini belgilaydi."},
    {"q": "HTML formada matn kiritish maydoni qaysi teg orqali yaratiladi?",
     "opts": ["<textbox>", "<input>", "<field>", "<text>"],
     "correct": 1, "exp": "<input type=\"text\"> matn kiritish maydoni yaratadi."},
    {"q": "Elementni markazlashtirish uchun ko'p ishlatiladigan xususiyat qaysi?",
     "opts": ["align: center", "margin: auto", "center: true", "position: center"],
     "correct": 1, "exp": "margin: auto; blok elementni gorizontal markazlashtiradi."},
    {"q": "HTML sahifaning meta-ma'lumotlari qaysi teg ichida joylashadi?",
     "opts": ["<body>", "<head>", "<meta>", "<info>"],
     "correct": 1, "exp": "<head> ichida sarlavha, meta va CSS ulanishlari joylashadi."},
    {"q": "CSS da elementni yashirish uchun qaysi xususiyat ishlatiladi?",
     "opts": ["visible: false", "display: none", "hide: true", "opacity: hide"],
     "correct": 1, "exp": "display: none; elementni sahifadan butunlay olib tashlaydi."},
    {"q": "Responsiv dizayn uchun CSS da qaysi qoida ishlatiladi?",
     "opts": ["@responsive", "@media", "@screen", "@adapt"],
     "correct": 1, "exp": "@media so'rovlari ekran o'lchamiga qarab stillarni moslashtiradi."},
    {"q": "HTML sahifasining eng tashqi asosiy tegi qaysi?",
     "opts": ["<page>", "<html>", "<doc>", "<web>"],
     "correct": 1, "exp": "<html> butun sahifani o'rab turuvchi asosiy teg."},
    {"q": "CSS da matnni qalin qilish uchun qaysi xususiyat ishlatiladi?",
     "opts": ["font-weight: bold", "text-bold: true", "font-thick", "bold: yes"],
     "correct": 0, "exp": "font-weight: bold; matnni qalinlashtiradi."},
    {"q": "HTML da izoh (comment) qanday yoziladi?",
     "opts": ["// izoh", "<!-- izoh -->", "/* izoh */", "# izoh"],
     "correct": 1, "exp": "HTML izohlari <!-- --> orasida yoziladi."},
    {"q": "CSS Grid layout uchun display xususiyatiga qaysi qiymat beriladi?",
     "opts": ["grid", "table", "flex", "block-grid"],
     "correct": 0, "exp": "display: grid; grid tizimini yoqadi."},
    {"q": "HTML formada tugma yaratish uchun qaysi teg ishlatiladi?",
     "opts": ["<btn>", "<button>", "<submit>", "<click>"],
     "correct": 1, "exp": "<button> tugma yaratish uchun standart teg."},
]


# ------------------------------------------------------------------
# MA'LUMOTLAR BAZASI
# ------------------------------------------------------------------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            options_json TEXT NOT NULL,
            correct_index INTEGER NOT NULL,
            explanation TEXT,
            active INTEGER DEFAULT 1,
            created_at TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            score INTEGER,
            correct INTEGER,
            total INTEGER,
            elapsed_seconds INTEGER,
            created_at TEXT
        )
        """
    )
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM questions")
    count = cur.fetchone()[0]
    if count == 0:
        now = datetime.now().isoformat(timespec="seconds")
        for item in DEFAULT_QUESTIONS:
            cur.execute(
                "INSERT INTO questions (question, options_json, correct_index, explanation, active, created_at) "
                "VALUES (?, ?, ?, ?, 1, ?)",
                (item["q"], json.dumps(item["opts"], ensure_ascii=False), item["correct"], item["exp"], now),
            )
        conn.commit()

    conn.close()


# ------------------------------------------------------------------
# TELEGRAM initData TEKShIRUVI (foydalanuvchi haqiqatan Telegram
# orqali kirganini tasdiqlash uchun)
# ------------------------------------------------------------------
def verify_telegram_init_data(init_data: str, bot_token: str, max_age_seconds: int = 3600):
    """Telegram hujjatlashtirilgan algoritmi bo'yicha initData'ni tekshiradi.
    Muvaffaqiyatli bo'lsa foydalanuvchi ma'lumotini (dict) qaytaradi, aks holda None."""
    if not init_data or not bot_token:
        return None
    try:
        pairs = dict(parse_qsl(init_data, strict_parsing=True))
    except ValueError:
        return None

    received_hash = pairs.pop("hash", None)
    if not received_hash:
        return None

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        return None

    auth_date = int(pairs.get("auth_date", "0"))
    if max_age_seconds and (time.time() - auth_date) > max_age_seconds:
        return None

    user_raw = pairs.get("user")
    if not user_raw:
        return None
    try:
        return json.loads(user_raw)
    except json.JSONDecodeError:
        return None


# ------------------------------------------------------------------
# YORDAMCHI
# ------------------------------------------------------------------
def get_active_questions():
    db = get_db()
    rows = db.execute(
        "SELECT id, question, options_json, correct_index, explanation "
        "FROM questions WHERE active = 1 ORDER BY id"
    ).fetchall()
    result = []
    for r in rows:
        result.append({
            "id": r["id"],
            "q": r["question"],
            "opts": json.loads(r["options_json"]),
            "correct": r["correct_index"],
            "exp": r["explanation"] or "",
        })
    return result


def require_admin():
    return session.get("is_admin") is True


# ------------------------------------------------------------------
# JAMOAT (PUBLIC) YO'NALISHLAR
# ------------------------------------------------------------------
@app.route("/")
def mini_app():
    return render_template(
        "index.html",
        score_per_question=SCORE_PER_QUESTION,
        total_time_seconds=TOTAL_TIME_SECONDS,
    )


@app.route("/api/questions")
def api_questions():
    questions = get_active_questions()
    # to'g'ri javob va tushuntirishni ham yuboramiz — sodda arxitektura,
    # ball mijoz(browser)da hisoblanadi
    max_score = len(questions) * SCORE_PER_QUESTION
    return jsonify({
        "questions": questions,
        "score_per_question": SCORE_PER_QUESTION,
        "total_time_seconds": TOTAL_TIME_SECONDS,
        "max_score": max_score,
    })


@app.route("/api/submit", methods=["POST"])
def api_submit():
    data = request.get_json(silent=True) or {}
    init_data = data.get("initData", "")

    user = verify_telegram_init_data(init_data, BOT_TOKEN)
    if user is None:
        return jsonify({"ok": False, "error": "invalid_init_data"}), 400

    try:
        score = int(data["score"])
        correct = int(data["correct"])
        total = int(data["total"])
        elapsed = int(data["elapsed"])
    except (KeyError, ValueError, TypeError):
        return jsonify({"ok": False, "error": "invalid_payload"}), 400

    user_id = user.get("id")
    username = user.get("username") or user.get("first_name") or str(user_id)

    db = get_db()
    db.execute(
        "INSERT INTO results (user_id, username, score, correct, total, elapsed_seconds, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, username, score, correct, total, elapsed, datetime.now().isoformat(timespec="seconds")),
    )
    db.commit()
    return jsonify({"ok": True})


@app.route("/api/leaderboard")
def api_leaderboard():
    db = get_db()
    rows = db.execute(
        """
        SELECT username, MAX(score) as best_score, correct, total
        FROM results GROUP BY user_id ORDER BY best_score DESC LIMIT 10
        """
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/user_results")
def api_user_results():
    user_id = request.args.get("user_id", type=int)
    if not user_id:
        return jsonify({"ok": False, "error": "user_id kerak"}), 400
    db = get_db()
    rows = db.execute(
        "SELECT score, correct, total, elapsed_seconds, created_at FROM results "
        "WHERE user_id = ? ORDER BY created_at DESC LIMIT 5",
        (user_id,),
    ).fetchall()
    return jsonify([dict(r) for r in rows])


# ------------------------------------------------------------------
# ADMIN PANEL
# ------------------------------------------------------------------
@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if require_admin():
        return redirect(url_for("admin_dashboard"))

    error = None
    if request.method == "POST":
        password = request.form.get("password", "")
        if password == ADMIN_PASSWORD:
            session["is_admin"] = True
            return redirect(url_for("admin_dashboard"))
        error = "Parol noto'g'ri."

    return render_template("admin_login.html", error=error)


@app.route("/admin/logout")
def admin_logout():
    session.pop("is_admin", None)
    return redirect(url_for("admin_login"))


@app.route("/admin/dashboard")
def admin_dashboard():
    if not require_admin():
        return redirect(url_for("admin_login"))

    db = get_db()
    questions = db.execute(
        "SELECT id, question, active FROM questions ORDER BY id DESC"
    ).fetchall()
    results = db.execute(
        "SELECT username, score, correct, total, elapsed_seconds, created_at "
        "FROM results ORDER BY created_at DESC LIMIT 100"
    ).fetchall()
    leaderboard = db.execute(
        """
        SELECT username, MAX(score) as best_score, correct, total
        FROM results GROUP BY user_id ORDER BY best_score DESC LIMIT 10
        """
    ).fetchall()
    total_attempts = db.execute("SELECT COUNT(*) FROM results").fetchone()[0]
    total_users = db.execute("SELECT COUNT(DISTINCT user_id) FROM results").fetchone()[0]

    return render_template(
        "admin_dashboard.html",
        questions=questions,
        results=results,
        leaderboard=leaderboard,
        total_attempts=total_attempts,
        total_users=total_users,
    )


@app.route("/admin/questions/add", methods=["POST"])
def admin_add_question():
    if not require_admin():
        return redirect(url_for("admin_login"))

    question = request.form.get("question", "").strip()
    opt_a = request.form.get("opt_a", "").strip()
    opt_b = request.form.get("opt_b", "").strip()
    opt_c = request.form.get("opt_c", "").strip()
    opt_d = request.form.get("opt_d", "").strip()
    correct_index = request.form.get("correct_index", "0")
    explanation = request.form.get("explanation", "").strip()

    if question and opt_a and opt_b and opt_c and opt_d:
        options = [opt_a, opt_b, opt_c, opt_d]
        db = get_db()
        db.execute(
            "INSERT INTO questions (question, options_json, correct_index, explanation, active, created_at) "
            "VALUES (?, ?, ?, ?, 1, ?)",
            (question, json.dumps(options, ensure_ascii=False), int(correct_index), explanation,
             datetime.now().isoformat(timespec="seconds")),
        )
        db.commit()

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/questions/toggle/<int:qid>", methods=["POST"])
def admin_toggle_question(qid):
    if not require_admin():
        return redirect(url_for("admin_login"))
    db = get_db()
    db.execute("UPDATE questions SET active = 1 - active WHERE id = ?", (qid,))
    db.commit()
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/questions/delete/<int:qid>", methods=["POST"])
def admin_delete_question(qid):
    if not require_admin():
        return redirect(url_for("admin_login"))
    db = get_db()
    db.execute("DELETE FROM questions WHERE id = ?", (qid,))
    db.commit()
    return redirect(url_for("admin_dashboard"))


# ------------------------------------------------------------------
init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
