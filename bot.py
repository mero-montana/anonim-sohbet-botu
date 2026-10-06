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
    return (
        b in blocked.get(a, set())
        or a in blocked.get(b, set())
    )


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

    kb.add(
        types.InlineKeyboardButton(
            "Belirtmek istemiyorum",
            callback_data="gender_none",
        )
    )

    return kb


def vip_menu():
    kb = types.InlineKeyboardMarkup()

    kb.add(
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

    kb.add(
        types.InlineKeyboardButton(
            "Ban Aç",
            callback_data="admin_unban",
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
            "Hesabın banlı.",
        )
        return

    if user_id in muted:
        bot.send_message(
            user_id,
            "Susturulmuş durumdasın.",
        )
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


def add_referral(new_user_id, inviter_id):
    if new_user_id == inviter_id:
        return

    if inviter_id not in users:
        return

    if new_user_id in referrals:
        return

    referrals[new_user_id] = inviter_id

    count = sum(
        1
        for value in referrals.values()
        if value == inviter_id
    )

    if count >= REFERRAL_REQUIRED:
        if inviter_id not in referral_rewards:
            referral_rewards.add(inviter_id)

            vip_users[inviter_id] = (
                datetime.now()
                + timedelta(days=REFERRAL_VIP_DAYS)
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
    count = sum(
        1
        for value in referrals.values()
        if value == user_id
    )

    remaining = max(
        0,
        REFERRAL_REQUIRED - count,
    )

    try:
        username = bot.get_me().username

        link = (
            f"https://t.me/{username}"
            f"?start=ref_{user_id}"
        )

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
        bot.send_message(
            user_id,
            f"Davet linki oluşturulamadı.\n{exc}",
        )


@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.from_user.id

    if user_id in banned:
        bot.send_message(
            user_id,
            "Hesabın banlı.",
        )
        return

    is_new_user = user_id not in users
    referral_id = None

    parts = message.text.split()

    if len(parts) > 1 and parts[1].startswith("ref_"):
        try:
            referral_id = int(parts[1][4:])
        except ValueError:
            referral_id = None

    get_user(user_id)

    if is_new_user and referral_id is not None:
        add_referral(
            user_id,
            referral_id,
        )

    if get_user(user_id)["confirmed"]:
        bot.send_message(
            user_id,
            "Tekrar hoş geldin.\n\n"
            "Menüden bir işlem seç.",
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


def show_vip(user_id):
    if is_vip(user_id):
        if is_admin(user_id):
            bot.send_message(
                user_id,
                "VIP aktif.\n"
                "Admin hesabı olduğu için süresiz VIP.",
                reply_markup=vip_menu(),
            )
            return

        expires = vip_users[user_id].strftime(
            "%d.%m.%Y %H:%M"
        )

        bot.send_message(
            user_id,
            f"VIP aktif.\nBitiş: {expires}",
            reply_markup=vip_menu(),
        )
        return

    bot.send_message(
        user_id,
        "VIP özellikleri\n\n"
        "Öncelikli eşleşme\n"
        "Medya gönderme\n"
        "500 ⭐ karşılığında 30 gün",
        reply_markup=vip_menu(),
    )


@bot.message_handler(commands=["vip"])
def vip_command(message):
    show_vip(message.from_user.id)


@bot.callback_query_handler(
    func=lambda call: call.data == "buy_vip"
)
def buy_vip(call):
    user_id = call.from_user.id

    if is_admin(user_id):
        bot.answer_callback_query(
            call.id,
            "Admin zaten süresiz VIP.",
        )
        return

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
            "Ödeme oluşturulamadı.",
        )

        bot.send_message(
            user_id,
            f"Ödeme hatası: {exc}",
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
    start_matching(message.from_user.id)


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

    remove_from_waiting(user_id)

    bot.send_message(
        user_id,
        "Eşleşme sonlandırıldı.",
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

    add_match(user_id, partner)

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
    show_vip(message.from_user.id)


@bot.message_handler(
    func=lambda message: message.text == "Davet Et"
)
def referral_button(message):
    referral_info(message.from_user.id)


@bot.message_handler(
    func=lambda message: message.text == "Profil"
)
def profile_button(message):
    user_id = message.from_user.id
    data = get_user(user_id)

    vip_text = "Aktif" if is_vip(user_id) else "Pasif"

    bot.send_message(
        user_id,
        f"Profil\n\n"
        f"Yaş: {data['age']}\n"
        f"Cinsiyet: {data['gender']}\n"
        f"VIP: {vip_text}",
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

    vip_count = sum(
        1
        for user_id in users
        if is_vip(user_id)
    )

    bot.send_message(
        call.from_user.id,
        f"İstatistik\n\n"
        f"Kullanıcı: {len(users)}\n"
        f"Bekleyen: {len(waiting)}\n"
        f"Aktif eşleşme: {len(matches) // 2}\n"
        f"VIP: {vip_count}\n"
        f"Davet edilen: {len(referrals)}\n"
        f"Banlı: {len(banned)}",
    )


@bot.callback_query_handler(
    func=lambda call: call.data == "admin_give_vip"
)
def admin_give_vip(call):
    if not is_admin(call.from_user.id):
        return

    bot.answer_callback_query(call.id)

    msg = bot.send_message(
        call.from_user.id,
        "VIP yapılacak kullanıcının Telegram ID'sini yaz.",
    )

    bot.register_next_step_handler(
        msg,
        process_give_vip,
    )


def process_give_vip(message):
    if not is_admin(message.from_user.id):
        return

    try:
        target = int(message.text.strip())
    except (ValueError, AttributeError):
        bot.send_message(
            message.from_user.id,
            "Geçerli bir kullanıcı ID'si yaz.",
        )
        return

    vip_users[target] = (
        datetime.now()
        + timedelta(days=VIP_DAYS)
    )

    expires = vip_users[target].strftime(
        "%d.%m.%Y %H:%M"
    )

    bot.send_message(
        message.from_user.id,
        f"Kullanıcı VIP yapıldı.\n"
        f"ID: {target}\n"
        f"Bitiş: {expires}",
    )

    try:
        bot.send_message(
            target,
            f"Yönetici tarafından VIP yapıldın.\n"
            f"VIP bitiş tarihi: {expires}",
            reply_markup=menu(target),
        )
    except Exception:
        pass


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
                f"Yönetici duyurusu\n\n{message.text}",
            )
            sent += 1
        except Exception:
            pass

    bot.send_message(
        message.from_user.id,
        f"Duyuru gönderildi: {sent}",
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
    except (ValueError, AttributeError):
        bot.send_message(
            message.from_user.id,
            "Geçerli bir kullanıcı ID'si yaz.",
        )
        return

    if target == ADMIN_ID:
        bot.send_message(
            message.from_user.id,
            "Admin hesabı banlanamaz.",
        )
        return

    banned.add(target)
    end_match(target)
    remove_from_waiting(target)

    bot.send_message(
        message.from_user.id,
        f"Kullanıcı banlandı.\nID: {target}",
    )

    try:
        bot.send_message(
            target,
            "Hesabın yönetici tarafından banlandı.",
        )
    except Exception:
        pass


@bot.callback_query_handler(
    func=lambda call
