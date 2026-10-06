import os
from datetime import datetime, timedelta

import telebot
from telebot import types

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 8536869508

if not TOKEN:
    raise RuntimeError("BOT_TOKEN bulunamadı.")

bot = telebot.TeleBot(TOKEN)

users = {}
waiting = []
matches = {}
general_chat = set()

banned = set()
muted = set()
blocked = {}

vip_users = {}


def is_admin(uid):
    return uid == ADMIN_ID


def is_vip(uid):
    expiry = vip_users.get(uid)

    if not expiry:
        return False

    if datetime.now() >= expiry:
        del vip_users[uid]
        return False

    return True


def get_user(uid):
    if uid not in users:
        users[uid] = {
            "age": False,
            "gender": None,
            "preference": "any",
            "age_preference": None,
            "hide_username": False,
            "status": ""
        }

    return users[uid]


def menu(uid):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)

    kb.row("🔎 Eşleşme Ara", "⭐ VIP Eşleşme")
    kb.row("🌍 Genel Sohbet", "⏭️ Sonraki")
    kb.row("❌ Eşleşmeyi Bitir")
    kb.row("👤 Profil", "⭐ VIP Ol")

    if is_admin(uid):
        kb.row("🛠 Admin Paneli")

    return kb


def admin_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)

    kb.row("👥 İstatistikler", "📢 Duyuru")
    kb.row("🚫 Ban", "🔓 Unban")
    kb.row("🔇 Mute", "🔊 Unmute")
    kb.row("⭐ VIP Ver", "❌ VIP Al")
    kb.row("👢 Eşleşmeden At")
    kb.row("⬅️ Ana Menü")

    return kb


def remove_waiting(uid):
    while uid in waiting:
        waiting.remove(uid)


def is_blocked(a, b):
    return (
        b in blocked.get(a, set())
        or a in blocked.get(b, set())
    )


def compatible(a, b):
    ua = get_user(a)
    ub = get_user(b)

    if is_blocked(a, b):
        return False

    if ua["preference"] != "any":
        if ub["gender"] != ua["preference"]:
            return False

    if ub["preference"] != "any":
        if ua["gender"] != ub["preference"]:
            return False

    return True


@bot.message_handler(commands=["start"])
def start(message):
    uid = message.from_user.id

    if uid in banned:
        bot.send_message(uid, "🚫 Hesabın yasaklı.")
        return

    get_user(uid)

    if not users[uid]["age"]:
        kb = types.InlineKeyboardMarkup()

        kb.add(
            types.InlineKeyboardButton(
                "18 yaşından büyüğüm",
                callback_data="age_yes"
            )
        )

        bot.send_message(
            uid,
            "🔞 Bu bot 18 yaş ve üzeri kullanıcılar içindir.\n\n"
            "Devam ederek 18 yaşından büyük olduğunu onaylıyorsun.",
            reply_markup=kb
        )
        return

    if not users[uid]["gender"]:
        gender_menu(uid)
        return

    bot.send_message(
        uid,
        "Ana menüye hoş geldin.",
        reply_markup=menu(uid)
    )


def gender_menu(uid):
    kb = types.InlineKeyboardMarkup()

    kb.row(
        types.InlineKeyboardButton(
            "👨 Erkek",
            callback_data="gender_erkek"
        ),
        types.InlineKeyboardButton(
            "👩 Kadın",
            callback_data="gender_kadin"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "Diğer",
            callback_data="gender_diger"
        )
    )

    bot.send_message(
        uid,
        "Cinsiyetini seç:",
        reply_markup=kb
    )


@bot.callback_query_handler(
    func=lambda call: call.data == "age_yes"
)
def age_confirm(call):
    uid = call.from_user.id

    get_user(uid)["age"] = True

    bot.answer_callback_query(
        call.id,
        "Yaş onaylandı."
    )

    bot.edit_message_text(
        "Yaş onaylandı.\n\nŞimdi cinsiyetini seç:",
        uid,
        call.message.message_id
    )

    gender_menu(uid)


@bot.callback_query_handler(
    func=lambda call: call.data.startswith("gender_")
)
def gender_select(call):
    uid = call.from_user.id

    gender = call.data.replace(
        "gender_",
        ""
    )

    get_user(uid)["gender"] = gender

    bot.answer_callback_query(
        call.id,
        "Cinsiyet seçildi."
    )

    bot.send_message(
        uid,
        "Cinsiyet seçimin kaydedildi.",
        reply_markup=menu(uid)
    )


def preference_menu(uid):
    kb = types.InlineKeyboardMarkup()

    kb.row(
        types.InlineKeyboardButton(
            "👩 Kadın",
            callback_data="pref_kadin"
        ),
        types.InlineKeyboardButton(
            "👨 Erkek",
            callback_data="pref_erkek"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "👥 Fark etmez",
            callback_data="pref_any"
        )
    )

    bot.send_message(
        uid,
        "Kimlerle eşleşmek istiyorsun?",
        reply_markup=kb
    )


@bot.message_handler(
    func=lambda m: m.text == "🔎 Eşleşme Ara"
)
def find_match(message):
    uid = message.from_user.id

    if uid in banned:
        return

    if uid in matches:
        bot.send_message(
            uid,
            "Zaten bir eşleşmen var."
        )
        return

    if is_vip(uid):
        preference_menu(uid)
    else:
        start_matching(uid)


@bot.message_handler(
    func=lambda m: m.text == "
