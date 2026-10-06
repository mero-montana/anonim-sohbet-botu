import os
from datetime import datetime, timedelta

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

pending_announcement = set()
pending_vip = set()
pending_ban = set()
pending_unban = set()


VIP_DAYS = 30
VIP_STARS = 500
REFERRAL_REQUIRED = 10
REFERRAL_VIP_DAYS = 7


def get_user(user_id):
    if user_id not in users:
        users[user_id] = {
            "confirmed": False,
            "gender": None,
            "age": None,
        }

    return users[user_id]


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


def remove_waiting(user_id):
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


def menu(user_id):
    keyboard = types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    keyboard.row("Eşleş", "Sonraki")
    keyboard.row("Eşleşmeyi Bitir", "Son Eşleşmem")
    keyboard.row("Engelle", "Genel Sohbet")
    keyboard.row("VIP", "Profil")
    keyboard.row("Davet Et")

    if is_admin(user_id):
        keyboard.row("Admin Paneli")

    return keyboard


def gender_keyboard():
    keyboard = types.InlineKeyboardMarkup()

    keyboard.row(
        types.InlineKeyboardButton(
            "Erkek",
            callback_data="gender_erkek"
        ),
        types.InlineKeyboardButton(
            "Kadın",
            callback_data="gender_kadin"
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "Belirtmek istemiyorum",
            callback_data="gender_none"
        )
    )

    return keyboard


def age_keyboard():
    keyboard = types.InlineKeyboardMarkup()

    keyboard.row(
        types.InlineKeyboardButton(
            "18-20",
            callback_data="age_18_20"
        ),
        types.InlineKeyboardButton(
            "21-25",
            callback_data="age_21_25"
        )
    )

    keyboard.row(
        types.InlineKeyboardButton(
            "26-30",
            callback_data="age_26_30"
        ),
        types.InlineKeyboardButton(
            "31+",
            callback_data="age_31_plus"
        )
    )

    return keyboard


def vip_menu():
    keyboard = types.InlineKeyboardMarkup()

    keyboard.add(
        types.InlineKeyboardButton(
            "500 ⭐ ile 30 Gün VIP",
            callback_data="buy_vip"
        )
    )

    return keyboard


def admin_menu():
    keyboard = types.InlineKeyboardMarkup()

    keyboard.row(
        types.InlineKeyboardButton(
            "İstatistik",
            callback_data="admin_stats"
        )
    )

    keyboard.row(
        types.InlineKeyboardButton(
            "Duyuru",
            callback_data="admin_announce"
        )
    )

    keyboard.row(
        types.InlineKeyboardButton(
            "VIP Ver",
            callback_data="admin_give_vip"
        )
    )

    keyboard.row(
        types.InlineKeyboardButton(
            "Ban",
            callback_data="admin_ban"
        ),
        types.InlineKeyboardButton(
            "Ban Aç",
            callback_data="admin_unban"
        )
    )

    return keyboard


def find_partner(user_id):
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
            "Önce 18+ onayını vermelisin."
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

    remove_waiting(user_id)

    partner = find_partner(user_id)

    if partner is None:
        waiting.append(user_id)

        bot.send_message(
            user_id,
            "Eşleşme aranıyor..."
        )
        return

    remove_waiting(partner)

    matches[user_id] = partner
    matches[partner] = user_id

    bot.send_message(
        user_id,
        "Eşleşme bulundu.\nArtık anonim konuşabilirsiniz.",
        reply_markup=menu(user_id)
    )

    bot.send_message(
        partner,
        "Eşleşme bulundu.\nArtık anonim konuşabilirsiniz.",
        reply_markup=menu(partner)
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

    new_user = user_id not in users

    get_user(user_id)

    if new_user:
        vip_users[user_id] = datetime.now() + timedelta(
            days=VIP_DAYS
        ) if is_admin(user_id) else vip_users.get(user_id)

    if get_user(user_id)["confirmed"]:
        bot.send_message(
            user_id,
            "Tekrar hoş geldin.\n\nMenüden bir işlem seç.",
            reply_markup=menu(user_id)
        )
        return

    keyboard = types.InlineKeyboardMarkup()

    keyboard.add(
        types.InlineKeyboardButton(
            "18+ Onaylıyorum",
            callback_data="confirm_18"
        )
    )

    bot.send_message(
        user_id,
        "Anonim Sohbet Botuna hoş geldin.\n\n"
        "Devam etmek için 18 yaşından büyük olduğunu onayla.",
        reply_markup=keyboard
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
        "Kaydedildi"
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
        "Kaydedildi"
    )

    bot.send_message(
        user_id,
        "Profilin hazır.",
        reply_markup=menu(user_id)
    )


@bot.message_handler(
    func=lambda message: message.text == "Eşleş"
)
def match_button(message):
    start_matching(message.from_user.id)


@bot.message_handler(
    func=lambda message: message.text == "Sonraki"
)
def next_button(message):
    user_id = message.from_user.id

    partner = end_match(user_id)

    if partner:
        bot.send_message(
            partner,
            "Karşı taraf sonraki eşleşmeye geçti."
        )

    start_matching(user_id)


@bot.message_handler(
    func=lambda message: message.text == "Eşleşmeyi Bitir"
)
def finish_button(message):
    user_id = message.from_user.id

    partner = end_match(user_id)

    if partner:
        bot.send_message(
            partner,
            "Karşı taraf eşleşmeyi bitirdi.",
            reply_markup=menu(partner)
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
def general_chat_button(message):
    user_id = message.from_user.id

    if user_id in banned:
        return

    general_chat.add(user_id)

    bot.send_message(
        user_id,
        "Genel sohbete katıldın.\n"
        "Buraya yazdığın mesajlar genel sohbetteki kullanıcılara gönderilir.",
        reply_markup=menu(user_id)
    )


@bot.message_handler(
    func=lambda message: message.text == "VIP"
)
def vip_button(message):
    user_id = message.from_user.id

    status = "Aktif" if is_vip(user_id) else "Aktif değil"

    bot.send_message(
        user_id,
        f"VIP Durumu: {status}\n\n"
        "VIP üyelik 500 ⭐\n"
        "30 gün geçerlidir.",
        reply_markup=vip_menu()
    )


@bot.message_handler(
    func=lambda message: message.text == "Profil"
)
def profile_button(message):
    user_id = message.from_user.id
    user = get_user(user_id)

    vip = "Aktif" if is_vip(user_id) else "Aktif değil"

    bot.send_message(
        user_id,
        f"PROFİL\n\n"
        f"Yaş: {user['age']}\n"
        f"Cinsiyet: {user['gender']}\n"
        f"VIP: {vip}",
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

    try:
        username = bot.get_me().username

        link = (
            f"https://t.me/{username}"
            f"?start=ref_{user_id}"
        )

        bot.send_message(
            user_id,
            f"DAVET SİSTEMİ\n\n"
            f"Davet edilen: {count}\n"
            f"Hedef: {REFERRAL_REQUIRED}\n\n"
            f"10 kişi davet edersen 7 gün VIP kazanırsın.\n\n"
            f"Davet linkin:\n{link}"
        )

    except Exception:
        bot.send_message(
            user_id,
            "Davet linki oluşturulamadı."
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
        "Ödeme başarılı.\n"
        "30 günlük VIP aktif edildi.",
        reply_markup=menu(user_id)
    )


@bot.message_handler(
    func=lambda message: message.text == "Admin Paneli"
)
def admin_panel(message):
    user_id = message.from_user.id

    if not is_admin(user_id):
        return

    bot.send_message(
        user_id,
        "ADMIN PANELİ",
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
        f"İSTATİSTİKLER\n\n"
        f"Kullanıcı: {len(users)}\n"
        f"Bekleyen: {len(waiting)}\n"
        f"Aktif eşleşme: {len(matches) // 2}\n"
        f"VIP: {len(vip_users)}\n"
        f"Banlı: {len(banned)}\n"
        f"Genel sohbet: {len(general_chat)}"
    )


@bot.callback_query_handler(
    func=lambda call: call.data == "admin_announce"
)
def admin_announce(call):
    if not is_admin(call.from_user.id):
        return

    pending_announcement.add(
        call.from_user.id
    )

    bot.answer_callback_query(call.id)

    bot.send_message(
        call.from_user.id,
        "Duyuru metnini şimdi gönder."
    )


@bot.callback_query_handler(
    func=lambda call: call.data == "admin_give_vip"
)
def admin_give_vip(call):
    if not is_admin(call.from_user.id):
        return

    pending_vip.add(
        call.from_user.id
    )

    bot.answer_callback_query(call.id)

    bot.send_message(
        call.from_user.id,
        "VIP vereceğin kullanıcının Telegram ID'sini gönder."
    )


@bot.callback_query_handler(
    func=lambda call: call.data == "admin_ban"
)
def admin_ban(call):
    if not is_admin(call.from_user.id):
        return

    pending_ban.add(
        call.from_user.id
    )

    bot.answer_callback_query(call.id)

    bot.send_message(
        call.from_user.id,
        "Banlayacağın kullanıcının Telegram ID'sini gönder."
    )


@bot.callback_query_handler(
    func=lambda call: call.data == "admin_unban"
)
def admin_unban(call):
    if not is_admin(call.from_user.id):
        return

    pending_unban.add(
        call.from_user.id
    )

    bot.answer_callback_query(call.id)

    bot.send_message(
        call.from_user.id,
        "Banını kaldıracağın kullanıcının Telegram ID'sini gönder."
    )


@bot.message_handler(
    content_types=["text"]
)
def text_handler(message):
    user_id = message.from_user.id
    text = message.text

    if is_admin(user_id):

        if user_id in pending_announcement:
            pending_announcement.remove(user_id)

            sent = 0

            for target in list(users.keys()):
                try:
                    bot.send_message(
                        target,
                        "📢 DUYURU\n\n" + text
                    )
                    sent += 1
                except Exception:
                    pass

            bot.send_message(
                user_id,
                f"Duyuru gönderildi.\n"
                f"Başarılı: {sent}",
                reply_markup=admin_menu()
            )

            return

        if user_id in pending_vip:
            pending_vip.remove(user_id)

            try:
                target = int(text)

                vip_users[target] = (
                    datetime.now()
                    + timedelta(days=VIP_DAYS)
                )

                bot.send_message(
                    user_id,
                    f"{target} ID'li kullanıcıya "
                    f"{VIP_DAYS} günlük VIP verildi.",
                    reply_markup=admin_menu()
                )

                try:
                    bot.send_message(
                        target,
                        "Admin tarafından 30 günlük VIP verildi."
                    )
                except Exception:
                    pass

            except ValueError:
                bot.send_message(
                    user_id,
                    "Geçerli bir Telegram ID gönder."
                )

            return

        if user_id in pending_ban:
            pending_ban.remove(user_id)

            try:
                target = int(text)

                banned.add(target)
                remove_waiting(target)

                partner = end_match(target)

                if partner:
                    bot.send_message(
                        partner,
                        "Eşleşmen sonlandırıldı."
                    )

                bot.send_message(
                    user_id,
                    f"{target} ID'li kullanıcı banlandı.",
                    reply_markup=admin_menu()
                )

            except ValueError:
                bot.send_message(
                    user_id,
                    "Geçerli bir Telegram ID gönder."
                )

            return

        if user_id in pending_unban:
            pending_unban.remove(user_id)

            try:
                target = int(text)

                banned.discard(target)

                bot.send_message(
                    user_id,
                    f"{target} ID'li kullanıcının banı açıldı.",
                    reply_markup=admin_menu()
                )

            except ValueError:
                bot.send_message(
                    user_id,
                    "Geçerli bir Telegram ID gönder."
                )

            return


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

    if user_id in banned:
        return

    if user_id in muted:
        return

    partner = matches.get(user_id)

    if partner:
        try:
            bot.copy_message(
                partner,
                user_id,
                message.message_id
            )
        except Exception as error:
            print(
                "Mesaj aktarım hatası:",
                error
            )

        return

    if user_id in general_chat:
        for target in list(general_chat):

            if target == user_id:
                continue

            if target in banned:
                continue

            try:
                bot.copy_message(
                    target,
                    user_id,
                    message.message_id
                )
            except Exception as error:
                print(
                    "Genel sohbet aktarım hatası:",
                    error
                )


print("Bot çalışıyor...")

bot.infinity_polling(
    skip_pending=True,
    timeout=30,
    long_polling_timeout=30
        )
