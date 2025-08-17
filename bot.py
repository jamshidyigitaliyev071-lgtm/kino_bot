
import telebot
import json
from telebot import types
from datetime import datetime

# ---------------------- BOT MA'LUMOTLARI ----------------------
TOKEN = "7637070362:AAGggUpvRRC9kzYQE6Q2A0YuSNXXIeahHPw"
ADMIN_ID = 6664532884
DATA_FILE = "kinolar.json"

bot = telebot.TeleBot(TOKEN)

# ---------------------- AD SESSIONS ----------------------
ad_sessions = {}

# ---------------------- DATA FUNKSIYALARI ----------------------
def load_data():
    try:
        with open(DATA_FILE, "r", encoding='utf-8') as f:
            return json.load(f)
    except:
        return {
            "statistika": {"foydalanuvchilar": 0, "qidiruvlar": 0},
            "kinolar": [],
            "janrlar": []
        }

def save_data():
    with open(DATA_FILE, "w", encoding='utf-8') as f:
        json.dump(kinolar, f, indent=4, ensure_ascii=False)

kinolar = load_data()

# ---------------------- HELPERLAR ----------------------
def get_movie_by_code(code):
    return next((k for k in kinolar["kinolar"] if k["kodi"].lower() == code.lower()), None)

def ensure_genre(name):
    if name not in kinolar["janrlar"]:
        kinolar["janrlar"].append(name)

def get_all_user_ids():
    """Barcha foydalanuvchilar ID sini qaytaradi"""
    # kinolar.json dan foydalanuvchilar ro'yxatini olish
    if "foydalanuvchilar_list" in kinolar:
        return kinolar["foydalanuvchilar_list"]
    return [ADMIN_ID]  # Agar ro'yxat bo'sh bo'lsa, faqat admin

def send_movie_card(chat_id, movie):
    """Poster bilan karta va 2 tugma: Yuklash / Ko'rish"""
    caption = f"🎬 <b>{movie['nomi']}</b>\n" \
              f"🔖 Kodi: <code>{movie['kodi']}</code>\n" \
              f"🎭 Janr: {movie.get('janri','-')}"
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("📥 Yuklash", callback_data=f"choosefmt_dl_{movie['kodi']}"),
        types.InlineKeyboardButton("▶ Ko'rish", callback_data=f"choosefmt_view_{movie['kodi']}")
    )
    poster_id = movie.get("poster_id")
    if poster_id:
        bot.send_photo(chat_id, poster_id, caption=caption, parse_mode="HTML", reply_markup=kb)
    else:
        bot.send_message(chat_id, caption, parse_mode="HTML", reply_markup=kb)

# ---------------------- START & MENU ----------------------
@bot.message_handler(commands=['start'])
def start(message):
    # Foydalanuvchini ro'yxatga qo'shish
    if "foydalanuvchilar_list" not in kinolar:
        kinolar["foydalanuvchilar_list"] = []
    
    user_id = message.from_user.id
    if user_id not in kinolar["foydalanuvchilar_list"]:
        kinolar["foydalanuvchilar_list"].append(user_id)
        kinolar["statistika"]["foydalanuvchilar"] += 1
        save_data()
    
    if message.from_user.id == ADMIN_ID:
        show_admin_menu(message)
    else:
        show_user_menu(message)

def show_admin_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🎬 Kino qo'shish", "❌ Kino o'chirish")
    markup.add("➕ Janr qo'shish", "🗑️ Janrni o'chirish")
    markup.add("📊 Statistika", "📋 Barcha kinolar")
    markup.add("🏆 Top 5 kinolar")
    markup.add("📣 Reklama tarqatish")
    bot.send_message(message.chat.id, "👑 Admin menyusiga xush kelibsiz!", reply_markup=markup)

def show_user_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔍 Kino qidirish", "🎬 Janr bo'yicha")
    markup.add("🏆 Top 5 kinolar")
    bot.send_message(message.chat.id, "🎥 Kino botga xush kelibsiz!", reply_markup=markup)

# ---------------------- ADMIN: KINO QO'SHISH (NOM → KOD → JANR → POSTER → FORMATLAR) ----------------------
@bot.message_handler(func=lambda m: m.text == "🎬 Kino qo'shish" and m.from_user.id == ADMIN_ID)
def add_kino_start(message):
    msg = bot.send_message(message.chat.id, "Kino nomini kiriting:", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, process_kino_name)

def process_kino_name(message):
    if message.text in ["/start", "/cancel"]:
        return start(message)
    kino_nomi = message.text.strip()
    msg = bot.send_message(message.chat.id, "Kino kodini kiriting:")
    bot.register_next_step_handler(msg, process_kino_code, kino_nomi)

def process_kino_code(message, kino_nomi):
    if message.text in ["/start", "/cancel"]:
        return start(message)
    kino_kodi = message.text.strip()
    if any(k["kodi"].lower() == kino_kodi.lower() for k in kinolar["kinolar"]):
        bot.send_message(message.chat.id, "⚠️ Bu kod allaqachon mavjud. Boshqa kod kiriting.")
        msg = bot.send_message(message.chat.id, "Kino kodini kiriting:")
        bot.register_next_step_handler(msg, process_kino_code, kino_nomi)
        return

    # Janr tanlash
    markup = types.InlineKeyboardMarkup()
    for janr in kinolar["janrlar"]:
        markup.add(types.InlineKeyboardButton(janr, callback_data=f"add_{janr}_{kino_kodi}_{kino_nomi}"))
    markup.add(types.InlineKeyboardButton("➕ Yangi janr", callback_data=f"newjanr_{kino_kodi}_{kino_nomi}"))
    bot.send_message(message.chat.id, "Janrni tanlang yoki yangi janr yarating:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("newjanr_"))
def add_new_genre(call):
    _, kino_kodi, kino_nomi = call.data.split("_", 2)
    msg = bot.send_message(call.message.chat.id, "Yangi janr nomini kiriting:")
    bot.register_next_step_handler(msg, process_new_genre, kino_kodi, kino_nomi)

def process_new_genre(message, kino_kodi, kino_nomi):
    yangi_janr = message.text.strip()
    if yangi_janr:
        ensure_genre(yangi_janr)

    yangi_kino = {
        "nomi": kino_nomi,
        "kodi": kino_kodi,
        "janri": yangi_janr if yangi_janr else "",
        "poster_id": None,
        "file_ids": {},           # format nomi -> file_id
        "views": 0,
        "qoshilgan_vaqti": str(datetime.now())
    }
    kinolar["kinolar"].append(yangi_kino)
    save_data()

    bot.send_message(message.chat.id, f"✅ Kino qo'shildi!\n\n📌 Nomi: {kino_nomi}\n🔖 Kodi: {kino_kodi}\n🎭 Janr: {yangi_janr or '-'}")
    bot.send_message(message.chat.id, "🖼 Endi kino posteri (rasmi)ni yuboring (Photo sifatida).")
    bot.register_next_step_handler(message, save_movie_poster, kino_kodi)

@bot.callback_query_handler(func=lambda call: call.data.startswith("add_"))
def add_kino_to_genre(call):
    _, janr, kino_kodi, kino_nomi = call.data.split("_", 3)
    ensure_genre(janr)
    yangi_kino = {
        "nomi": kino_nomi,
        "kodi": kino_kodi,
        "janri": janr,
        "poster_id": None,
        "file_ids": {},
        "views": 0,
        "qoshilgan_vaqti": str(datetime.now())
    }
    kinolar["kinolar"].append(yangi_kino)
    save_data()

    bot.send_message(call.message.chat.id, f"✅ Kino qo'shildi!\n\n📌 Nomi: {kino_nomi}\n🔖 Kodi: {kino_kodi}\n🎭 Janr: {janr}")
    bot.send_message(call.message.chat.id, "🖼 Endi kino posteri (rasmi)ni yuboring (Photo sifatida).")
    bot.register_next_step_handler(call.message, save_movie_poster, kino_kodi)

def save_movie_poster(message, kino_kodi):
    if not message.photo:
        bot.send_message(message.chat.id, "⚠️ Iltimos, rasm yuboring (Photo).")
        return show_admin_menu(message)
    photo = message.photo[-1]  # eng sifatlisi
    poster_id = photo.file_id

    kino = get_movie_by_code(kino_kodi)
    if not kino:
        bot.send_message(message.chat.id, "⚠️ Kino topilmadi.")
        return show_admin_menu(message)

    kino["poster_id"] = poster_id
    save_data()

    bot.send_message(message.chat.id, "✅ Poster saqlandi.\nEndi format nomini kiriting (masalan: 480p, 720p, 1080p):")
    bot.register_next_step_handler(message, upload_video_format, kino_kodi)

# --- Admin: video yuklash oqimi (format -> video) ---
def upload_video_format(message, kino_kodi):
    format_nomi = message.text.strip()
    if not format_nomi:
        bot.send_message(message.chat.id, "⚠️ Format nomini to'g'ri kiriting.")
        return show_admin_menu(message)
    bot.send_message(message.chat.id, f"{format_nomi} format uchun video yuboring (Telegram'ga VIDEO sifatida).")
    bot.register_next_step_handler(message, save_video_file, kino_kodi, format_nomi)

def save_video_file(message, kino_kodi, format_nomi):
    if not message.video:
        bot.send_message(message.chat.id, "⚠️ Video yuboring (galereyadan video).")
        return show_admin_menu(message)

    kino = get_movie_by_code(kino_kodi)
    if not kino:
        bot.send_message(message.chat.id, "⚠️ Kino topilmadi.")
        return show_admin_menu(message)

    kino.setdefault("file_ids", {})
    kino["file_ids"][format_nomi] = message.video.file_id
    save_data()

    bot.send_message(message.chat.id, f"✅ {format_nomi} format qo'shildi!")
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("➕ Yana format qo'shish", callback_data=f"morefmt_{kino_kodi}"))
    kb.add(types.InlineKeyboardButton("✅ Tamom", callback_data="donefmt"))
    bot.send_message(message.chat.id, "Davom etamizmi?", reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data.startswith("morefmt_") or call.data == "donefmt")
def more_formats(call):
    if call.data == "donefmt":
        bot.send_message(call.message.chat.id, "✅ Saqlandi.")
        return show_admin_menu(call.message)
    _, kino_kodi = call.data.split("_", 1)
    bot.send_message(call.message.chat.id, "Yangi format nomini kiriting:")
    bot.register_next_step_handler(call.message, upload_video_format, kino_kodi)

# ---------------------- ADMIN: JANR QO'SHISH / O'CHIRISH ----------------------
@bot.message_handler(func=lambda m: m.text == "➕ Janr qo'shish" and m.from_user.id == ADMIN_ID)
def add_genre(message):
    msg = bot.send_message(message.chat.id, "Yangi janr nomi:")
    bot.register_next_step_handler(msg, do_add_genre)

def do_add_genre(message):
    name = message.text.strip()
    if not name:
        bot.send_message(message.chat.id, "⚠️ Janr nomi bo'sh bo'lishi mumkin emas.")
        return show_admin_menu(message)
    ensure_genre(name)
    save_data()
    bot.send_message(message.chat.id, f"✅ '{name}' janri qo'shildi.")
    show_admin_menu(message)

@bot.message_handler(func=lambda m: m.text == "🗑️ Janrni o'chirish" and m.from_user.id == ADMIN_ID)
def delete_genre_start(message):
    if not kinolar["janrlar"]:
        bot.send_message(message.chat.id, "😕 Hozircha janrlar mavjud emas.")
        return show_admin_menu(message)
    kb = types.InlineKeyboardMarkup()
    for j in kinolar["janrlar"]:
        kb.add(types.InlineKeyboardButton(f"🗑️ {j}", callback_data=f"delgenre_{j}"))
    bot.send_message(message.chat.id, "Qaysi janrni o'chiramiz?", reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data.startswith("delgenre_"))
def do_delete_genre(call):
    _, j = call.data.split("_", 1)
    if j in kinolar["janrlar"]:
        kinolar["janrlar"].remove(j)
        # O'sha janrdagi filmlarni 'Boshqa'ga ko'chiramiz
        ensure_genre("Boshqa")
        for mv in kinolar["kinolar"]:
            if mv.get("janri","").lower() == j.lower():
                mv["janri"] = "Boshqa"
        save_data()
        bot.send_message(call.message.chat.id, f"✅ '{j}' janri o'chirildi. Unga tegishli kinolar 'Boshqa' janriga ko'chirildi.")
    else:
        bot.send_message(call.message.chat.id, "⚠️ Janr topilmadi.")
    show_admin_menu(call.message)

# ---------------------- ADMIN: KINO O'CHIRISH / STATISTIKA / BARCHA KINOLAR ----------------------
@bot.message_handler(func=lambda m: m.text == "❌ Kino o'chirish" and m.from_user.id == ADMIN_ID)
def delete_movie_start(message):
    if not kinolar["kinolar"]:
        bot.send_message(message.chat.id, "😕 Hozircha kinolar mavjud emas")
        return
    msg = bot.send_message(message.chat.id, "O'chirmoqchi bo'lgan kino KODINI kiriting:", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, delete_movie)

def delete_movie(message):
    kode = message.text.strip().lower()
    for k in kinolar["kinolar"]:
        if k["kodi"].lower() == kode:
            kinolar["kinolar"].remove(k)
            save_data()
            bot.send_message(message.chat.id, f"✅ {k['nomi']} muvaffaqiyatli o'chirildi!")
            show_admin_menu(message)
            return
    bot.send_message(message.chat.id, "⚠️ Bunday kod topilmadi. Qaytadan urinib ko'ring.")
    delete_movie_start(message)

@bot.message_handler(func=lambda m: m.text == "📊 Statistika" and m.from_user.id == ADMIN_ID)
def show_stats(message):
    stats = (
        "📊 Bot statistikasi:\n\n"
        f"👥 Foydalanuvchilar: {kinolar['statistika']['foydalanuvchilar']}\n"
        f"🔍 Qidiruvlar: {kinolar['statistika']['qidiruvlar']}\n"
        f"🎬 Jami kinolar: {len(kinolar['kinolar'])}\n"
        f"🗂️ Janrlar soni: {len(kinolar['janrlar'])}"
    )
    bot.send_message(message.chat.id, stats)

@bot.message_handler(func=lambda m: m.text == "📋 Barcha kinolar" and m.from_user.id == ADMIN_ID)
def list_all_movies(message):
    if not kinolar["kinolar"]:
        bot.send_message(message.chat.id, "😕 Hozircha kinolar mavjud emas")
        return
    for k in kinolar["kinolar"]:
        send_movie_card(message.chat.id, k)

# ---------------------- USER: QIDIRISH (NOM/KOD) ----------------------
@bot.message_handler(func=lambda m: m.text == "🔍 Kino qidirish")
def search_kino(message):
    msg = bot.send_message(message.chat.id, "Kino nomi yoki KODINI yuboring:", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, process_search)

def process_search(message):
    query = message.text.strip().lower()
    kinolar["statistika"]["qidiruvlar"] += 1
    save_data()

    results = [k for k in kinolar["kinolar"] if query in k["nomi"].lower() or query == k["kodi"].lower()]
    if results:
        for k in results:
            send_movie_card(message.chat.id, k)
    else:
        bot.send_message(message.chat.id, "😕 Hech narsa topilmadi. Boshqa kalit so'z bilan urinib ko'ring")

    show_user_menu(message)

# ---------------------- USER: JANR BO'YICHA ----------------------
@bot.message_handler(func=lambda m: m.text == "🎬 Janr bo'yicha")
def show_genres(message):
    if not kinolar["janrlar"]:
        bot.send_message(message.chat.id, "😕 Hozircha janrlar mavjud emas")
        return
    markup = types.InlineKeyboardMarkup()
    for janr in kinolar["janrlar"]:
        markup.add(types.InlineKeyboardButton(janr, callback_data=f"genre_{janr}"))
    bot.send_message(message.chat.id, "Janrni tanlang:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("genre_"))
def show_genre_movies(call):
    janr = call.data.split("_", 1)[1]
    movies = [k for k in kinolar["kinolar"] if k.get("janri","").lower() == janr.lower()]
    if movies:
        for m in movies:
            send_movie_card(call.message.chat.id, m)
    else:
        bot.send_message(call.message.chat.id, f"😕 {janr} janrida hali kinolar yo'q")

# ---------------------- FORMAT TANLASH: Ko'rish / Yuklash oqimi ----------------------
@bot.callback_query_handler(func=lambda call: call.data.startswith("choosefmt_"))
def choose_format(call):
    # choosefmt_{action}_{code}  action in [view, dl]
    _, action, code = call.data.split("_", 2)
    movie = get_movie_by_code(code)
    if not movie:
        return bot.send_message(call.message.chat.id, "⚠️ Kino topilmadi.")

    if not movie.get("file_ids"):
        return bot.send_message(call.message.chat.id, "⚠️ Hali formatlar qo'shilmagan.")

    kb = types.InlineKeyboardMarkup()
    for fmt in movie["file_ids"].keys():
        kb.add(types.InlineKeyboardButton(fmt, callback_data=f"fmt_{action}_{code}_{fmt}"))
    kb.add(types.InlineKeyboardButton("↩️ Orqaga", callback_data=f"back_{code}"))
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data.startswith("back_"))
def back_to_actions(call):
    # Orqaga: poster ostidagi ikki tugmani qayta chizamiz
    code = call.data.split("_", 1)[1]
    movie = get_movie_by_code(code)
    if not movie: 
        return
    # Yangidan karta yuborish (edit emas – soddaroq)
    send_movie_card(call.message.chat.id, movie)

@bot.callback_query_handler(func=lambda call: call.data.startswith("fmt_"))
def fmt_action(call):
    # fmt_{action}_{code}_{fmt}
    _, action, code, fmt = call.data.split("_", 3)
    movie = get_movie_by_code(code)
    if not movie:
        return bot.send_message(call.message.chat.id, "⚠️ Kino topilmadi.")
    file_id = movie.get("file_ids", {}).get(fmt)
    if not file_id:
        return bot.send_message(call.message.chat.id, "⚠️ Bu format topilmadi.")

    # Hisoblagich
    movie["views"] = movie.get("views", 0) + 1
    save_data()

    if action == "view":
        bot.send_video(call.message.chat.id, file_id, caption=f"{movie['nomi']} • {fmt}")
    else:  # action == "dl"
        bot.send_document(call.message.chat.id, file_id, caption=f"{movie['nomi']} • {fmt}")

# ---------------------- TOP 5 KINOLAR (ADMIN & USER) ----------------------
@bot.message_handler(func=lambda m: m.text == "🏆 Top 5 kinolar")
def top_movies(message):
    top_list = sorted(kinolar["kinolar"], key=lambda x: x.get("views", 0), reverse=True)[:5]
    if not top_list:
        bot.send_message(message.chat.id, "Hozircha ko'rilgan/yuklangan kinolar yo'q.")
        return
    text = "🏆 Top 5 ko'rilgan/yuklangan kinolar:\n\n"
    for i, k in enumerate(top_list, 1):
        text += f"{i}. {k['nomi']} — {k.get('views', 0)} marta\n"
    bot.send_message(message.chat.id, text)

# ---------------------- ADMIN: REKLAMA TURINI TANLASH (INLINE) ----------------------
@bot.message_handler(func=lambda m: m.text == "📣 Reklama tarqatish" and m.from_user.id == ADMIN_ID)
def choose_ad_type(message):
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("📝 Matn", callback_data="adtype_text"),
        types.InlineKeyboardButton("🖼 Rasm", callback_data="adtype_photo")
    )
    kb.add(
        types.InlineKeyboardButton("🎥 Video", callback_data="adtype_video"),
        types.InlineKeyboardButton("📄 Dokument", callback_data="adtype_document")
    )
    bot.send_message(message.chat.id, "📢 Reklama turini tanlang:", reply_markup=kb)

# ---------------------- ADMIN: INLINE TANLASH BO'YICHA KONTENT QABUL QILISH ----------------------
@bot.callback_query_handler(func=lambda call: call.data.startswith("adtype_"))
def get_ad_type(call):
    ad_type = call.data.split("_")[1]
    ad_sessions[call.message.chat.id] = {"ad_type": ad_type}

    if ad_type == "text":
        msg = bot.send_message(call.message.chat.id, "Reklama matnini yuboring:")
    elif ad_type == "photo":
        msg = bot.send_message(call.message.chat.id, "Reklama rasm yuboring (Photo sifatida):")
    elif ad_type == "video":
        msg = bot.send_message(call.message.chat.id, "Reklama video yuboring (Video sifatida):")
    elif ad_type == "document":
        msg = bot.send_message(call.message.chat.id, "Reklama dokument yuboring (Document sifatida):")
    
    bot.register_next_step_handler(msg, confirm_ad_inline)

# ---------------------- ADMIN: REKLAMA TASDIQLASH ----------------------
def confirm_ad_inline(message):
    if message.chat.id not in ad_sessions:
        bot.send_message(message.chat.id, "⚠️ Xatolik yuz berdi.")
        return show_admin_menu(message)
    
    ad_type = ad_sessions[message.chat.id]["ad_type"]
    ad_sessions[message.chat.id]["ad_content"] = message

    # Kontent turini tekshirish
    valid_content = False
    if ad_type == "text" and message.content_type == 'text':
        valid_content = True
    elif ad_type == "photo" and message.content_type == 'photo':
        valid_content = True
    elif ad_type == "video" and message.content_type == 'video':
        valid_content = True
    elif ad_type == "document" and message.content_type == 'document':
        valid_content = True
    
    if not valid_content:
        bot.send_message(message.chat.id, f"⚠️ Noto'g'ri kontent turi. {ad_type} yuborishingiz kerak edi.")
        return show_admin_menu(message)

    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("✅ Ha", callback_data=f"sendad_yes_{message.chat.id}"),
        types.InlineKeyboardButton("❌ Yo'q", callback_data=f"sendad_no_{message.chat.id}")
    )
    bot.send_message(message.chat.id, "📢 Reklamani barcha foydalanuvchilarga yuborilsinmi?", reply_markup=kb)

# ---------------------- FOYDALANUVCHILARGA REKLAMA YUBORISH ----------------------
@bot.callback_query_handler(func=lambda call: call.data.startswith("sendad_"))
def send_ad_to_users(call):
    action, _, chat_id_str = call.data.split("_")
    chat_id = int(chat_id_str)
    
    if chat_id not in ad_sessions:
        bot.send_message(call.message.chat.id, "⚠️ Xatolik yuz berdi.")
        return show_admin_menu(call.message)

    if action == "sendad_no":
        bot.send_message(call.message.chat.id, "❌ Reklama bekor qilindi.")
        ad_sessions.pop(chat_id, None)
        return show_admin_menu(call.message)

    ad_msg = ad_sessions[chat_id]["ad_content"]
    users_sent = 0
    users_failed = 0

    for user_id in get_all_user_ids():
        try:
            if ad_msg.content_type == 'text':
                bot.send_message(user_id, ad_msg.text)
            elif ad_msg.content_type == 'photo':
                bot.send_photo(user_id, ad_msg.photo[-1].file_id, caption=ad_msg.caption or "")
            elif ad_msg.content_type == 'video':
                bot.send_video(user_id, ad_msg.video.file_id, caption=ad_msg.caption or "")
            elif ad_msg.content_type == 'document':
                bot.send_document(user_id, ad_msg.document.file_id, caption=ad_msg.caption or "")
            users_sent += 1
        except Exception as e:
            users_failed += 1
            print(f"Failed to send ad to {user_id}: {e}")

    bot.send_message(call.message.chat.id, f"✅ Reklama yuborildi!\n📤 Yuborildi: {users_sent}\n❌ Xatolik: {users_failed}")
    ad_sessions.pop(chat_id, None)
    show_admin_menu(call.message)

def start_bot():
    print("✅ Bot ishga tushdi...")
    bot.polling(none_stop=True)


import os
from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

def keep_alive():
    t = Thread(target=run)
    t.start()

# 🚀 Botni ishga tushirishdan oldin serverni yoqamiz
keep_alive()

# ====== BOT QISMI ======
import telebot

TOKEN = "YOUR_BOT_TOKEN"  # shu yerga tokeningni yoz
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Salom! Bot ishlayapti ✅")

bot.polling(none_stop=True)
