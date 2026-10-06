import os
from datetime import datetime, timedelta

import telebot
from telebot import types

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "8536869508"))

if not TOKEN:
    raise RuntimeError("BOT_TOKEN bulunamadi")

bot = telebot.TeleBot(TOKEN, parse_mode=None)

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
            "general": False,
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
        types.InlineKeyboardButton(
            "18-20",
            callback_data="age_18_20",
        ),
        types.InlineKeyboardButton(
            "21-25",
            callback_data="age_21_25",
        ),
    )

    kb.row(
        types.InlineKeyboardButton(
            "26-30",
            callback_data="age_26_30",
        ),
        types.InlineKeyboardButton(
            "31+",
            callback_data="age_31_plus",
        ),
    )

    return kb


def gender_keyboard():
    kb = types.InlineKeyboardMarkup()

    kb.row(
        types.InlineKeyboardButton(
            "Erkek",
            callback_data="gender_erkek",
        ),
        types.InlineKeyboardButton(
            "Kadın",
            callback_data="gender_kadin",
        ),
    )

    kb.row(
        types.InlineKeyboardButton(
            "Belirtmek istemiyorum",
            callback_data="gender_none",
        )
    )

    return kb


def vip_menu():
    kb = types.InlineKeyboardMarkup()

    kb.row(
        types.InlineKeyboardButton(
            "500 ⭐ ile 30 Gün VIP",
            callback_data="buy_vip",
        )
    )

    return kb


def admin_menu():
    kb = types.InlineKeyboardMarkup()

    kb.row(
        types.InlineKeyboardButton(
            "İstatistik",
            callback_data="admin_stats",
        ),
        types.InlineKeyboardButton(
            "Duyuru",
            callback_data="admin_announce",
        ),
    )

    kb.row(
        types.InlineKeyboardButton(
            "VIP Ver",
            callback_data="admin_give_vip",
        ),
        types.InlineKeyboardButton(
            "Ban",
            callback_data="admin_ban",
        ),
    )

    kb.row(
        types.InlineKeyboardButton(
            "Ban Aç",
            callback_data="
