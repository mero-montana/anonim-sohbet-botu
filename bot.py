from datetime import datetime, timedelta
import os

import telebot
from telebot import types

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 8536869508

if not TOKEN:
    raise RuntimeError("BOT_TOKEN bulunamadi")

bot = telebot.TeleBot(TOKEN)

users = {}
waiting = []
matches = {}
last_matches = {}
blocked = {}
banned = set()
muted = set()
vip_users = {}
general_chat = set()
referrals = {}
referral_rewards = set()

VIP_DAYS = 30
VIP_STARS = 500
REFERRAL_REQUIRED = 10
REFERRAL_VIP_DAYS = 7


def is_admin(user_id):
    return user_id == ADMIN_ID


def is_vip(user_id):
    if is_admin(user_id):
        return True

    expires = vip_users.get(user_id)

    if not expires:
        return False

    if datetime.now() >= expires:
        vip_users.pop(user_id, None)
        return False

    return True


def get_user(user_id):
    if user_id not in users:
        users[user_id] = {
            "age": None,
            "gender": None,
            "confirmed": False,
        }

    return users[user_id]


def is_blocked(a, b):
    return b in blocked.get(a, set()) or a in blocked.get(b, set())


def remove_from_waiting(user_id):
    while user_id in waiting:
        waiting.remove(user_id)


def end_match(user_id):
    partner = matches.pop(user_id, None)

    if partner is not None:
        matches.pop(partner, None)

        last_matches[user_id] = partner
        last_matches[partner] = user_id

        return partner

    return None


def add_match(a, b):
    remove_from_waiting(a)
    remove_from_waiting(b)

    matches[a] = b
    matches[b] = a


def menu(user_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)

    kb.row("Eşleş", "Sonraki")
    kb.row("Eşleşmeyi Bitir", "Son Eşleşmem")
    kb.row("Engelle", "Genel Sohbet")
    kb.row("VIP", "Profil")
    kb.row("Davet Et")

    if is_admin(user_id):
        kb.row("Admin Paneli")

    return kb


def age_keyboard():
    kb = types.InlineKeyboardMarkup()

    kb.row(
        types.InlineKeyboardButton("18-20", callback_data="age_18_20"),
        types.InlineKeyboardButton("21-25", callback_data="age_21_25"),
    )

    kb.row(
        types.InlineKeyboardButton("26-30", callback_data="age_26_30"),
        types.InlineKeyboardButton("31+", callback_data="age_31_plus"),
    )

    return kb


def gender_keyboard():
    kb = types.InlineKeyboardMarkup()

    kb.row(
        types.InlineKeyboardButton("Erkek", callback_data="gender_erkek"),
        types.InlineKeyboardButton("Kadın", callback_data="gender_kadin"),
    )

    kb.add(
        types.InlineKeyboardButton(
            "Belirtmek istemiyorum", callback_data="gender_none"
        )
    )

    return kb


def vip_menu():
    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton("500 ⭐ ile 30 Gün VIP", callback_data="buy_vip")
    )

    return kb


def admin_menu():
    kb = types.InlineKeyboardMarkup()

    kb.row(
        types.InlineKeyboardButton("İstatistik", callback_data="admin_stats"),
        types.InlineKeyboardButton("Duyuru", callback_data="admin_announce"),
    )

    kb.row(
        types.InlineKeyboardButton("VIP Ver", callback_data="admin_give_vip"),
        types.InlineKeyboardButton("Ban", callback_data="admin_ban"),
    )

    kb.add(types.InlineKeyboardButton("Ban Aç", callback_data="admin_unban"))

    return kb


def find_partner(user_id):
    me = get_user(user_id)

    candidates = []

    for candidate in waiting:
        if candidate == user_id:
            continue

        if candidate in matches:
            continue

        if candidate in banned:
            continue

        if is_blocked(user_id, candidate):
            continue

        candidates.append(candidate)

    if is_vip(user_id):
        candidates.sort(key=lambda x: 0 if is_vip(x) else 1)

    for candidate in candidates:
        other = get_user(candidate)

        if me["age"] and other["age"]:
            if me["age"] != other["age"]:
                continue

        return candidate

    return None


def start_matching(user_id):
    if user_id in banned:
        bot.send_message(user_id, "Hesabın banlı.")
        return

    if user_id in muted:
        bot.send_message(user_id, "Susturulmuş durumdasın.")
        return

    if not get_user(user_id)["confirmed"]:
        bot.send_message(user_id, "Önce 18 yaşından büyük olduğunu onayla.")
        return

    if user_id in matches:
        bot.send_message(user_id, "Zaten bir eşleşmen var.")
        return

    remove_from_waiting(user_id)

    partner = find_partner(user_id)

    if partner is None:
        waiting.append(user_id)

        bot.send_message(user_id, "Eşleşme aranıyor...")
        return

    add_match(user_id, partner)

    bot.send_message(user_id, "Eşleşme bulundu. Artık anonim konuşabilirsiniz.")

    bot.send_message(partner, "Eşleşme bulundu. Artık anonim konuşabilirsiniz.")


def add_referral(new_user_id, inviter_id):
    if new_user_id == inviter_id:
        return

    if inviter_id not in users:
        return

    if new_user_id in referrals:
        return

    referrals[new_user_id] = inviter_id

    count = sum(1 for value in referrals.values() if value == inviter_id)

    if count >= REFERRAL_REQUIRED:
        if inviter_id not in referral_rewards:
            referral_rewards.add(inviter_id)

            vip_users[inviter_id] = datetime.now() + timedelta(
                days=REFERRAL_VIP_DAYS
            )

            try:
                bot.send_message(
                    inviter_id,
                    "Tebrikler!\n\n"
                    "10 kişi davet ettin.\n"
                    "7 günlük VIP ödülün aktif edildi.",
                    reply_markup=menu(inviter_id),
                )
            except Exception:
                pass


def referral_info(user_id):
    count = sum(1 for value in referrals.values() if value == user_id)

    remaining = max(0, REFERRAL_REQUIRED - count)

    try:
        username = bot.get_me().username

        link = f"https://t.me/{username}?start=ref_{user_id}"

        bot.send_message(
            user_id,
            "DAVET SİSTEMİ\n\n"
            "Arkadaşlarını davet et.\n"
            "10 kişi katılırsa 7 gün VIP kazanırsın.\n\n"
            f"Davet edilen kişi: {count}\n"
            f"Kalan: {remaining}\n\n"
            f"Davet linkin:\n{link}",
        )

    except Exception as exc:
        bot.send_message(user_id, f"Davet linki oluşturulamadı.\n{exc}")


@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.from_user.id

    if user_id in banned:
        bot.send_message(user_id, "Hesabın banlı.")
        return

    is_new_user = user_id not in users
    referral_id = None

    parts = message.text.split()

    if len(parts) > 1:
        if parts[1].startswith("ref_"):
            try:
                referral_id = int(parts[1][4:])
            except ValueError:
                referral_id = None

    get_user(user_id)

    if is_new_user and referral_id is not None:
        add_referral(user_id, referral_id)

    if get_user(user_id)["confirmed"]:
        bot.send_message(
            user_id,
            "Tekrar hoş geldin.\n\nMenüden bir işlem seç.",
            reply_markup=menu(user_id),
        )
        return

    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton("18+ Onaylıyorum", callback_data="confirm_18")
    )

    bot.send_message(
        user_id,
        "Anonim Sohbet Botuna hoş geldin.\n\n"
        "Devam etmek için 18 yaşından büyük olduğunu onayla.",
        reply_markup=kb,
    )


@bot.callback_query_handler(func=lambda call: call.data == "confirm_18")
def confirm_18(call):
    user_id = call.from_user.id

    get_user(user_id)["confirmed"] = True

    bot.answer_callback_query(call.id, "Onaylandı")

    bot.send_message(user_id, "Cinsiyetini seç.", reply_markup=gender_keyboard())


@bot.callback_query_handler(func=lambda call: call.data.startswith("gender_"))
def choose_gender(call):
    user_id = call.from_user.id

    value
    

