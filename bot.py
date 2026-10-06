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

VIP_DAYS = 30
VIP_STARS = 500


def is_admin(user_id):
    return user_id == ADMIN_ID


def is_vip(user_id):
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
            "Ban",
            callback_data="admin_ban",
        ),
        types.InlineKeyboardButton(
            "Ban Aç",
            callback_data="admin_unban",
        ),
    )

    return kb


def find_partner(user_id):
    me = get_user(user_id)

    candidates = list(waiting)

    if is_vip(user_id):
        candidates.sort(
            key=lambda x: 0 if is_vip(x) else 1
        )

    for candidate in candidates:
        if candidate == user_id:
            continue

        if candidate in matches:
            continue

        if is_blocked(user_id, candidate):
            continue

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
        bot.send_message(
            user_id,
            "Önce 18 yaşından büyük olduğunu onayla.",
        )
        return

    if user_id in matches:
        bot.send_message(
            user_id,
            "Zaten bir eşleşmen var.",
        )
        return

    remove_from_waiting(user_id)

    partner = find_partner(user_id)

    if partner is None:
        waiting.append(user_id)

        bot.send_message(
            user_id,
            "Eşleşme aranıyor...",
        )

        return

    add_match(user_id, partner)

    bot.send_message(
        user_id,
        "Eşleşme bulundu. Artık anonim konuşabilirsiniz.",
    )

    bot.send_message(
        partner,
        "Eşleşme bulundu. Artık anonim konuşabilirsiniz.",
    )


def send_general_message(sender_id, message):
    for user_id in list(general_chat):
        if user_id == sender_id:
            continue

        if user_id in banned or user_id in muted:
            continue

        try:
            bot.send_message(
                user_id,
                message,
            )
        except Exception:
            pass


@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.from_user.id

    if user_id in banned:
        bot.send_message(
            user_id,
            "Hesabın banlı.",
        )
        return

    get_user(user_id)

    if get_user(user_id)["confirmed"]:
        bot.send_message(
            user_id,
            "Tekrar hoş geldin.\n\nMenüden bir işlem seç.",
            reply_markup=menu(user_id),
        )
        return

    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton(
            "18+ Onaylıyorum",
            callback_data="confirm_18",
        )
    )

    bot.send_message(
        user_id,
        "Anonim Sohbet Botuna hoş geldin.\n\n"
        "Devam etmek için 18 yaşından büyük olduğunu onayla.",
        reply_markup=kb,
    )


@bot.callback_query_handler(
    func=lambda call: call.data == "confirm_18"
)
def confirm_18(call):
    user_id = call.from_user.id

    get_user(user_id)["confirmed"] = True

    bot.answer_callback_query(
        call.id,
        "Onaylandı",
    )

    bot.send_message(
        user_id,
        "Cinsiyetini seç.",
        reply_markup=gender_keyboard(),
    )


@bot.callback_query_handler(
    func=lambda call: call.data.startswith("gender_")
)
def choose_gender(call):
    user_id = call.from_user.id
    value = call.data.replace(
        "gender_",
        "",
        1,
    )

    get_user(user_id)["gender"] = value

    bot.answer_callback_query(
        call.id,
        "Kaydedildi",
    )

    bot.send_message(
        user_id,
        "Yaş aralığını seç.",
        reply_markup=age_keyboard(),
    )


@bot.callback_query_handler(
    func=lambda call: call.data.startswith("age_")
)
def choose_age(call):
    user_id = call.from_user.id
    value = call.data.replace(
        "age_",
        "",
        1,
    )

    get_user(user_id)["age"] = value

    bot.answer_callback_query(
        call.id,
        "Kaydedildi",
    )

    bot.send_message(
        user_id,
        "Profilin hazır.\n\n"
        "Eşleşmek için Eşleş butonuna bas.",
        reply_markup=menu(user_id),
    )


@bot.message_handler(commands=["vip"])
def vip_command(message):
    show_vip(message.chat.id)


def show_vip(user_id):
    if is_vip(user_id):
        expires = vip_users[user_id].strftime(
            "%d.%m.%Y %H:%M"
        )

        bot.send_message(
            user_id,
            "VIP aktif.\n"
            "Bitiş: " + expires,
            reply_markup=vip_menu(),
        )
    else:
        bot.send_message(
            user_id,
            "VIP özellikleri\n\n"
            "Öncelikli eşleşme\n"
            "VIP rozet\n"
            "VIP oda\n"
            "500 ⭐ karşılığında 30 gün",
            reply_markup=vip_menu(),
        )


@bot.callback_query_handler(
    func=lambda call: call.data == "buy_vip"
)
def buy_vip(call):
    user_id = call.from_user.id

    try:
        bot.send_invoice(
            user_id,
            "30 Gün VIP",
            "Anonim Sohbet Botu VIP üyeliği",
            "vip_30_days",
            "",
            "XTR",
            [
                types.LabeledPrice(
                    "30 Gün VIP",
                    VIP_STARS,
                )
            ],
        )

        bot.answer_callback_query(call.id)

    except Exception as exc:
        bot.answer_callback_query(
            call.id,
            "Ödeme oluşturulamadı",
        )

        bot.send_message(
            user_id,
            "Ödeme hatası: " + str(exc),
        )


@bot.pre_checkout_query_handler(
    func=lambda query: True
)
def pre_checkout(pre_checkout_query):
    bot.answer_pre_checkout_query(
        pre_checkout_query.id,
        ok=True,
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
        "VIP aktif edildi.\n"
        "30 gün boyunca VIP özelliklerini kullanabilirsin.",
        reply_markup=menu(user_id),
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

    if user_id in matches:
        partner = end_match(user_id)

        if partner:
            bot.send_message(
                partner,
                "Karşı taraf yeni eşleşmeye geçti.",
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
            "Eşleşme sonlandırıldı.",
        )

        bot.send_message(
            user_id,
            "Eşleşme sonlandırıldı.",
            reply_markup=menu(user_id),
        )
    else:
        remove_from_waiting(user_id)

        bot.send_message(
            user_id,
            "Aktif eşleşmen yok.",
            reply_markup=menu(user_id),
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
            "Şu anda eşleştiğin biri yok.",
        )
        return

    blocked.setdefault(
        user_id,
        set(),
    ).add(partner)

    end_match(user_id)

    bot.send_message(
        user_id,
        "Kullanıcı engellendi.",
        reply_markup=menu(user_id),
    )

    bot.send_message(
        partner,
        "Eşleşme sonlandırıldı.",
    )


@bot.message_handler(
    func=lambda message: message.text == "Son Eşleşmem"
)
def recover_button(message):
    user_id = message.from_user.id
    partner = last_matches.get(user_id)

    if not partner or partner in banned:
        bot.send_message(
            user_id,
            "Kayıtlı son eşleşme bulunamadı.",
        )
        return

    if user_id in matches or partner in matches:
        bot.send_message(
            user_id,
            "Şu anda başka bir eşleşme var.",
        )
        return

    if is_blocked(user_id, partner):
        bot.send_message(
            user_id,
            "Bu kullanıcı engelli.",
        )
        return

    add_match(
        user_id,
        partner,
    )

    bot.send_message(
        user_id,
        "Son eşleşmen geri getirildi.",
    )

    bot.send_message(
        partner,
        "Son eşleşmen geri getirildi.",
    )


@bot.message_handler(
    func=lambda message: message.text == "Genel Sohbet"
)
def general_button(message):
    user_id = message.from_user.id

    if user_id in general_chat:
        general_chat.remove(user_id)

        bot.send_message(
            user_id,
            "Genel sohbetten çıktın.",
        )
    else:
        general_chat.add(user_id)

        bot.send_message(
            user_id,
            "Genel sohbete katıldın.",
        )


@bot.message_handler(
    func=lambda message: message.text == "VIP"
)
def vip_button(message):
    show_vip(
        message.from_user.id
    )


@bot.message_handler(
    func=lambda message: message.text == "Profil"
)
def profile_button(message):
    user_id = message.from_user.id
    data = get_user(user_id)

    vip_text = (
        "Aktif"
        if is_vip(user_id)
        else "Pasif"
    )

    bot.send_message(
        user_id,
        "Profil\n\n"
        "Yaş: " + str(data["age"]) + "\n"
        "Cinsiyet: " + str(data["gender"]) + "\n"
        "VIP: " + vip_text,
    )


@bot.message_handler(
    func=lambda message: message.text == "Admin Paneli"
)
def admin_panel_button(message):
    if not is_admin(message.from_user.id):
        return

    bot.send_message(
        message.from_user.id,
        "Admin Paneli",
        reply_markup=admin_menu(),
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
        "İstatistik\n\n"
        "Kullanıcı: " + str(len(users)) + "\n"
        "Bekleyen: " + str(len(waiting)) + "\n"
        "Aktif eşleşme: " + str(len(matches) // 2) + "\n"
        "VIP: " + str(len(vip_users)) + "\n"
        "Banlı: " + str(len(banned)),
    )


@bot.callback_query_handler(
    func=lambda call: call.data == "admin_announce"
)
def admin_announce(call):
    if not is_admin(call.from_user.id):
        return

    bot.answer_callback_query(call.id)

    msg = bot.send_message(
        call.from_user.id,
        "Duyuru metnini yaz.",
    )

    bot.register_next_step_handler(
        msg,
        process_announcement,
    )


def process_announcement(message):
    if not is_admin(message.from_user.id):
        return

    sent = 0

    for user_id in list(users):
        try:
            bot.send_message(
                user_id,
                "Yönetici duyurusu\n\n"
                + message.text,
            )
            sent += 1
        except Exception:
            pass

    bot.send_message(
        message.from_user.id,
        "Duyuru gönderildi: " + str(sent),
    )


@bot.callback_query_handler(
    func=lambda call: call.data == "admin_ban"
)
def admin_ban(call):
    if not is_admin(call.from_user.id):
        return

    bot.answer_callback_query(call.id)

    msg = bot.send_message(
        call.from_user.id,
        "Banlanacak kullanıcı ID'sini yaz.",
    )

    bot.register_next_step_handler(
        msg,
        process_ban,
    )


def process_ban(message):
    if not is_admin(message.from_user.id):
        return

    try:
        target = int(message.text.strip())

        banned.add(target)
        end_match(target)
        remove_from_waiting(target)

        bot.send_message(
            message.from_user.id,
            "Banlandı: " + str(target),
        )

    except ValueError:
        bot.send_message(
            message.from_user.id,
            "Geçerli bir kullanıcı ID'si yaz.",
        )


@bot.callback_query_handler(
    func=lambda call: call.data == "admin_unban"
)
def admin_unban(call):
    if not is_admin(call.from_user.id):
        return

    bot.answer_callback_query(call.id)

    msg = bot.send_message(
        call.from_user.id,
        "Banı açılacak kullanıcı ID'sini yaz.",
    )

    bot.register_next_step_handler(
        msg,
        process_unban,
    )


def process_unban(message):
    if not is_admin(message.from_user.id):
        return

    try:
        target = int(message.text.strip())

        banned.discard(target)

        bot.send_message(
            message.from_user.id,
            "Ban açıldı: " + str(target),
        )

    except ValueError:
        bot.send_message(
            message.from_user.id,
            "Geçerli bir kullanıcı ID'si yaz.",
        )


@bot.message_handler(
    content_types=[
        "text",
        "photo",
        "video",
        "voice",
        "audio",
        "document",
        "sticker",
        "animation",
    ]
)
def relay_message(message):
    user_id = message.from_user.id

    if user_id in banned or user_id in muted:
        return

    if message.text in [
        "Eşleş",
        "Sonraki",
        "Eşleşmeyi Bitir",
        "Son Eşleşmem",
        "Engelle",
        "Genel Sohbet",
        "VIP",
        "Profil",
        "Admin Paneli",
    ]:
        return

    if user_id in matches:
        partner = matches[user_id]

        if (
            message.content_type != "text"
            and not is_vip(user_id)
        ):
            bot.send_message(
                user_id,
                "Medya göndermek için VIP olmalısın.",
            )
            return

        try:
            bot.copy_message(
                partner,
                message.chat.id,
                message.message_id,
            )
        except Exception:
            bot.send_message(
                user_id,
                "Mesaj gönderilemedi.",
            )

        return

    if user_id in general_chat:
        if (
            message.content_type != "text"
            and not is_vip(user_id)
        ):
            bot.send_message(
                user_id,
                "Genel sohbette medya için VIP olmalısın.",
            )
            return

        if message.content_type == "text":
            send_general_message(
                user_id,
                message.text,
            )
        else:
            for target in list(general_chat):
                if target == user_id:
                    continue

                try:
                    bot.copy_message(
                        target,
                        message.chat.id,
                        message.message_id,
                    )
                except Exception:
                    pass

        return

    bot.send_message(
        user_id,
        "Önce Eşleş butonuna bas.",
        reply_markup=menu(user_id),
    )


print("Bot baslatiliyor...")

bot.infinity_polling(
    skip_pending=True,
    timeout=30,
    long_polling_timeout=30,
                 )
       
