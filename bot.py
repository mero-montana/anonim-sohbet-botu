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
        types.InlineKeyboardButton(
            "18-20",
            callback_data="age_18_20"
        ),
        types.InlineKeyboardButton(
            "21-25",
            callback_data="age_21_25"
        ),
    )

    kb.row(
        types.InlineKeyboardButton(
            "26-30",
            callback_data="age_26_30"
        ),
        types.InlineKeyboardButton(
            "31+",
            callback_data="age_31_plus"
        ),
    )

    return kb


def gender_keyboard():
    kb = types.InlineKeyboardMarkup()

    kb.row(
        types.InlineKeyboardButton(
            "Erkek",
            callback_data="gender_erkek"
        ),
        types.InlineKeyboardButton(
            "Kadın",
            callback_data="gender_kadin"
        ),
    )

    kb.add(
        types.InlineKeyboardButton(
            "Belirtmek istemiyorum",
            callback_data="gender_none"
        )
    )

    return kb


def vip_menu():
    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton(
            "500 ⭐ ile 30 Gün VIP",
            callback_data="buy_vip"
        )
    )

    return kb


def admin_menu():
    kb = types.InlineKeyboardMarkup()

    kb.row(
        types.InlineKeyboardButton(
            "İstatistik",
            callback_data="admin_stats"
        )
    )

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
        candidates.sort(
            key=lambda x: 0 if is_vip(x) else 1
        )

    for candidate in candidates:
        other = get_user(candidate)

        if me["age"] and other["age"]:
            if me["age"] != other["age"]:
                continue

        return candidate

    return None


def start_matching(user_id):
    if user_id in banned:
        bot.send_message(
            user_id,
            "Hesabın banlı."
        )
        return

    if user_id in muted:
        bot.send_message(
            user_id,
            "Susturulmuş durumdasın."
        )
        return

    user = get_user(user_id)

    if not user["confirmed"]:
        bot.send_message(
            user_id,
            "Önce 18 yaşından büyük olduğunu onayla."
        )
        return

    if not user["gender"]:
        bot.send_message(
            user_id,
            "Önce cinsiyetini seç.",
            reply_markup=gender_keyboard()
        )
        return

    if not user["age"]:
        bot.send_message(
            user_id,
            "Önce yaş aralığını seç.",
            reply_markup=age_keyboard()
        )
        return

    if user_id in matches:
        bot.send_message(
            user_id,
            "Zaten bir eşleşmen var."
        )
        return

    remove_from_waiting(user_id)

    partner = find_partner(user_id)

    if partner is None:
        waiting.append(user_id)

        bot.send_message(
            user_id,
            "Eşleşme aranıyor..."
        )
        return

    add_match(user_id, partner)

    bot.send_message(
        user_id,
        "Eşleşme bulundu. Artık anonim konuşabilirsiniz."
    )

    bot.send_message(
        partner,
        "Eşleşme bulundu. Artık anonim konuşabilirsiniz."
    )


@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.from_user.id

    if user_id in banned:
        bot.send_message(
            user_id,
            "Hesabın banlı."
        )
        return

    is_new_user = user_id not in users

    get_user(user_id)

    if get_user(user_id)["confirmed"]:
        bot.send_message(
            user_id,
            "Tekrar hoş geldin.\n\nMenüden bir işlem seç.",
            reply_markup=menu(user_id)
        )
        return

    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton(
            "18+ Onaylıyorum",
            callback_data="confirm_18"
        )
    )

    bot.send_message(
        user_id,
        "Anonim Sohbet Botuna hoş geldin.\n\n"
        "Devam etmek için 18 yaşından büyük olduğunu onayla.",
        reply_markup=kb
    )


@bot.callback_query_handler(
    func=lambda call: call.data == "confirm_18"
)
def confirm_18(call):
    user_id = call.from_user.id

    get_user(user_id)["confirmed"] = True

    bot.answer_callback_query(
        call.id,
        "Onaylandı"
    )

    bot.send_message(
        user_id,
        "Cinsiyetini seç.",
        reply_markup=gender_keyboard()
    )


@bot.callback_query_handler(
    func=lambda call: call.data.startswith("gender_")
)
def choose_gender(call):
    user_id = call.from_user.id

    value = call.data.replace(
        "gender_",
        ""
    )

    get_user(user_id)["gender"] = value

    bot.answer_callback_query(
        call.id,
        "Seçimin kaydedildi"
    )

    bot.send_message(
        user_id,
        "Yaş aralığını seç.",
        reply_markup=age_keyboard()
    )


@bot.callback_query_handler(
    func=lambda call: call.data.startswith("age_")
)
def choose_age(call):
    user_id = call.from_user.id

    value = call.data.replace(
        "age_",
        ""
    )

    get_user(user_id)["age"] = value

    bot.answer_callback_query(
        call.id,
        "Yaş aralığın kaydedildi"
    )

    bot.send_message(
        user_id,
        "Profilin hazır. Menüden eşleşmeye başlayabilirsin.",
        reply_markup=menu(user_id)
    )


@bot.message_handler(
    func=lambda message: message.text == "Eşleş"
)
def match_button(message):
    start_matching(
        message.from_user.id
    )


@bot.message_handler(
    func=lambda message: message.text == "Sonraki"
)
def next_button(message):
    user_id = message.from_user.id

    partner = end_match(user_id)

    if partner:
        bot.send_message(
            partner,
            "Eşleşme sonlandırıldı."
        )

    start_matching(user_id)


@bot.message_handler(
    func=lambda message: message.text == "Eşleşmeyi Bitir"
)
def end_button(message):
    user_id = message.from_user.id

    partner = end_match(user_id)

    if partner:
        bot.send_message(
            partner,
            "Karşı taraf eşleşmeyi bitirdi."
        )

    bot.send_message(
        user_id,
        "Eşleşme bitirildi.",
        reply_markup=menu(user_id)
    )


@bot.message_handler(
    func=lambda message: message.text == "Son Eşleşmem"
)
def last_match_button(message):
    user_id = message.from_user.id

    partner = last_matches.get(user_id)

    if partner:
        bot.send_message(
            user_id,
            "Son eşleşmen bulundu."
        )
    else:
        bot.send_message(
            user_id,
            "Henüz son eşleşmen yok."
        )


@bot.message_handler(
    func=lambda message: message.text == "Engelle"
)
def block_button(message):
    user_id = message.from_user.id
    partner = matches.get(user_id)

    if not partner:
        bot.send_message(
            user_id,
            "Şu anda bir eşleşmen yok."
        )
        return

    blocked.setdefault(
        user_id,
        set()
    ).add(partner)

    end_match(user_id)

    bot.send_message(
        user_id,
        "Kullanıcı engellendi.",
        reply_markup=menu(user_id)
    )


@bot.message_handler(
    func=lambda message: message.text == "Genel Sohbet"
)
def general_button(message):
    user_id = message.from_user.id

    general_chat.add(user_id)

    bot.send_message(
        user_id,
        "Genel sohbete katıldın.",
        reply_markup=menu(user_id)
    )


@bot.message_handler(
    func=lambda message: message.text == "VIP"
)
def vip_button(message):
    bot.send_message(
        message.from_user.id,
        "VIP üyelik\n\n500 ⭐ karşılığında 30 gün VIP.",
        reply_markup=vip_menu()
    )


@bot.message_handler(
    func=lambda message: message.text == "Profil"
)
def profile_button(message):
    user_id = message.from_user.id
    user = get_user(user_id)

    vip_text = (
        "Aktif"
        if is_vip(user_id)
        else "Aktif değil"
    )

    bot.send_message(
        user_id,
        f"Profil\n\n"
        f"Yaş: {user['age']}\n"
        f"Cinsiyet: {user['gender']}\n"
        f"VIP: {vip_text}",
        reply_markup=menu(user_id)
    )


@bot.message_handler(
    func=lambda message: message.text == "Davet Et"
)
def referral_button(message):
    user_id = message.from_user.id

    count = sum(
        1
        for value in referrals.values()
        if value == user_id
    )

    bot.send_message(
        user_id,
        f"Davet edilen kişi: {count}\n"
        f"10 kişi davet edersen 7 gün VIP kazanırsın."
    )


@bot.message_handler(
    func=lambda message: message.text == "Admin Paneli"
)
def admin_button(message):
    user_id = message.from_user.id

    if not is_admin(user_id):
        return

    bot.send_message(
        user_id,
        "Admin Paneli",
        reply_markup=admin_menu()
    )


@bot.callback_query_handler(
    func=lambda call: call.data == "admin_stats"
)
def admin_stats(call):
    if not is_admin(call.from_user.id):
        return

    bot.answer_callback_query(call.id)

    bot.send_message(
        call.from_user.id,
        f"İstatistikler\n\n"
        f"Kullanıcı: {len(users)}\n"
        f"Bekleyen: {len(waiting)}\n"
        f"Eşleşme: {len(matches) // 2}\n"
        f"VIP: {len(vip_users)}\n"
        f"Banlı: {len(banned)}"
    )


@bot.callback_query_handler(
    func=lambda call: call.data == "buy_vip"
)
def buy_vip(call):
    user_id = call.from_user.id

    bot.answer_callback_query(call.id)

    bot.send_invoice(
        user_id,
        "VIP Üyelik",
        "30 günlük VIP üyelik",
        "vip_30_days",
        "",
        "XTR",
        [
            types.LabeledPrice(
                "30 Gün VIP",
                VIP_STARS
            )
        ]
    )


@bot.pre_checkout_query_handler(
    func=lambda query: True
)
def pre_checkout(query):
    bot.answer_pre_checkout_query(
        query.id,
        ok=True
    )


@bot.message_handler(
    content_types=["successful_payment"]
)
def successful_payment(message):
    user_id = message.from_user.id

    vip_users[user_id] = (
        datetime.now()
        + timedelta(days=VIP_DAYS)
    )

    bot.send_message(
        user_id,
        "Ödeme başarılı.\n30 günlük VIP aktif edildi.",
        reply_markup=menu(user_id)
    )


@bot.message_handler(
    content_types=[
        "text",
        "photo",
        "video",
        "audio",
        "document",
        "voice",
        "sticker"
    ]
)
def relay_message(message):
    user_id = message.from_user.id

    if user_id in banned or user_id in muted:
        return

    partner = matches.get(user_id)

    if partner:
        try:
            bot.copy_message(
                partner,
                user_id,
                message.message_id
            )
        except Exception:
            pass

        return

    if user_id in general_chat:
        for target in list(general_chat):
            if target == user_id:
                continue

            try:
                bot.copy_message(
                    target,
                    user_id,
                    message.message_id
                )
            except Exception:
                pass


print("Bot çalışıyor...")

bot.infinity_polling(
    skip_pending=True,
    timeout=30,
    long_polling_timeout=30
    )

