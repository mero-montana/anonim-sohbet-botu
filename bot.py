import os
import time
from datetime import datetime, timedelta

import telebot
from telebot import types


TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "8536869508"))

if not TOKEN:
    raise RuntimeError("BOT_TOKEN bulunamadı")

bot = telebot.TeleBot(TOKEN)


# =========================
# VERİLER
# =========================

users = {}
waiting = []
matches = {}
general_chat = set()

banned = set()
muted = set()
blocked = {}
vip_users = {}

VIP_DAYS = 30
VIP_STARS = 500


# =========================
# YARDIMCI FONKSİYONLAR
# =========================

def is_admin(uid):
    return uid == ADMIN_ID


def is_vip(uid):
    if uid not in vip_users:
        return False

    if datetime.now() >= vip_users[uid]:
        del vip_users[uid]
        return False

    return True


def get_user(uid):
    if uid not in users:
        users[uid] = {
            "age": None,
            "gender": None,
            "vip_female": False,
            "age_filter": None,
            "status": "",
            "last_partner": None,
            "started": True
        }

    return users[uid]


def is_blocked(a, b):
    return b in blocked.get(a, set()) or a in blocked.get(b, set())


def remove_from_waiting(uid):
    while uid in waiting:
        waiting.remove(uid)


def remove_match(uid):
    partner = matches.pop(uid, None)

    if partner is not None:
        matches.pop(partner, None)

        users.setdefault(uid, {})["last_partner"] = partner
        users.setdefault(partner, {})["last_partner"] = uid

        return partner

    return None


def add_match(a, b):
    matches[a] = b
    matches[b] = a


def gender_text(gender):
    if gender == "erkek":
        return "Erkek"
    if gender == "kadin":
        return "Kadın"
    return "Diğer"


def menu(uid):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)

    kb.row("🔎 Eşleşme Ara")

    if is_vip(uid):
        kb.row("⭐ VIP Menü", "💬 Genel Sohbet")
    else:
        kb.row("⭐ VIP Satın Al", "💬 Genel Sohbet")

    kb.row("⏭️ Sonraki", "❌ Eşleşmeyi Bitir")
    kb.row("🚫 Engelle", "♻️ Son Eşleşmeyi Bul")

    if is_admin(uid):
        kb.row("🛠 Admin Panel")

    return kb


def admin_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)

    kb.row("👥 Kullanıcı Sayısı", "🟢 Aktif Eşleşmeler")
    kb.row("🚫 Ban", "✅ Ban Aç")
    kb.row("🔇 Sustur", "🔊 Susturma Aç")
    kb.row("⭐ VIP Ver", "❌ VIP Al")
    kb.row("📢 Duyuru")
    kb.row("🔙 Ana Menü")

    return kb


def vip_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)

    kb.row("👩 Kadın Önceliği")
    kb.row("🎂 Yaş Filtresi")
    kb.row("⚡ Anında Eşleş")
    kb.row("🔒 VIP Odası")
    kb.row("👤 VIP Profil")
    kb.row("🙈 Kullanıcı Adımı Gizle")
    kb.row("🔄 Tek Tıkla Değiştir")
    kb.row("🔔 Eşleşme Bildirimi")
    kb.row("🚫 Engellenenle Eşleşme")
    kb.row("⭐ VIP Durumu")
    kb.row("🔙 Ana Menü")

    return kb


def find_partner(uid):
    me = get_user(uid)

    # VIP kullanıcılar önce değerlendirilir
    candidates = list(waiting)

    if uid in candidates:
        candidates.remove(uid)

    # Engelli kişiler çıkar
    candidates = [
        x for x in candidates
        if x in users and not is_blocked(uid, x)
    ]

    # Yaş filtresi
    if is_vip(uid) and me.get("age_filter"):
        minimum, maximum = me["age_filter"]

        candidates = [
            x for x in candidates
            if users.get(x, {}).get("age") is not None
            and minimum <= users[x]["age"] <= maximum
        ]

    # Kadın önceliği
    if is_vip(uid) and me.get("vip_female"):
        women = [
            x for x in candidates
            if users.get(x, {}).get("gender") == "kadin"
        ]

        if women:
            candidates = women

    # VIP kullanıcıları önceliklendir
    candidates.sort(
        key=lambda x: 0 if is_vip(x) else 1
    )

    for partner in candidates:
        if partner == uid:
            continue

        if partner in matches:
            continue

        if is_blocked(uid, partner):
            continue

        return partner

    return None


def start_matching(uid):
    if uid in banned:
        bot.send_message(uid, "Hesabınız engellenmiş.")
        return

    if uid in matches:
        bot.send_message(
            uid,
            "Zaten bir eşleşmen var.",
            reply_markup=menu(uid)
        )
        return

    remove_from_waiting(uid)

    partner = find_partner(uid)

    if partner:
        remove_from_waiting(partner)
        add_match(uid, partner)

        bot.send_message(
            uid,
            "🎉 Eşleşme bulundu.\n\nMesajını gönder.",
            reply_markup=menu(uid)
        )

        bot.send_message(
            partner,
            "🎉 Eşleşme bulundu.\n\nMesajını gönder.",
            reply_markup=menu(partner)
        )

        if is_vip(uid):
            bot.send_message(uid, "⭐ VIP eşleşme önceliğin aktif.")

        if is_vip(partner):
            bot.send_message(partner, "⭐ VIP eşleşme önceliğin aktif.")

    else:
        waiting.append(uid)

        bot.send_message(
            uid,
            "🔎 Eşleşme aranıyor...\n\nSeni uygun bir kullanıcıyla eşleştireceğim.",
            reply_markup=menu(uid)
        )


def send_general_message(message):
    uid = message.from_user.id

    if uid not in general_chat:
        return

    if uid in banned or uid in muted:
        return

    for target in list(general_chat):
        if target == uid:
            continue

        try:
            bot.copy_message(
                target,
                message.chat.id,
                message.message_id,
                protect_content=True
            )
        except Exception:
            pass


# =========================
# BAŞLANGIÇ
# =========================

@bot.message_handler(commands=["start"])
def start(message):
    uid = message.from_user.id

    if uid in banned:
        bot.send_message(uid, "Bu botu kullanmanız engellenmiş.")
        return

    get_user(uid)

    kb = types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        one_time_keyboard=True
    )

    kb.row("18+ Onaylıyorum")
    kb.row("18+ Değilim")

    bot.send_message(
        uid,
        "Anonim Sohbet Botuna hoş geldin.\n\n"
        "Devam etmek için 18 yaşından büyük olduğunu onaylaman gerekiyor.",
        reply_markup=kb
    )


# =========================
# 18+ ONAY
# =========================

@bot.message_handler(func=lambda m: m.text == "18+ Onaylıyorum")
def age_confirm(message):
    uid = message.from_user.id

    get_user(uid)

    kb = types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        one_time_keyboard=True
    )

    kb.row("👨 Erkek", "👩 Kadın")
    kb.row("⚪ Diğer")

    bot.send_message(
        uid,
        "Cinsiyetini seç:",
        reply_markup=kb
    )


@bot.message_handler(func=lambda m: m.text == "18+ Değilim")
def underage(message):
    bot.send_message(
        message.chat.id,
        "Bu bot 18 yaş ve üzeri kullanıcılar içindir."
    )


# =========================
# CİNSİYET
# =========================

@bot.message_handler(func=lambda m: m.text in ["👨 Erkek", "👩 Kadın", "⚪ Diğer"])
def gender_select(message):
    uid = message.from_user.id
    user = get_user(uid)

    if message.text == "👨 Erkek":
        user["gender"] = "erkek"

    elif message.text == "👩 Kadın":
        user["gender"] = "kadin"

    else:
        user["gender"] = "diger"

    bot.send_message(
        uid,
        "Kaç yaşındasın? Sadece yaşını sayı olarak yaz.\nÖrnek: 20"
    )


# =========================
# YAŞ
# =========================

@bot.message_handler(
    func=lambda m: (
        m.from_user.id in users
        and users[m.from_user.id].get("gender") is not None
        and users[m.from_user.id].get("age") is None
        and m.text
        and m.text.isdigit()
    )
)
def age_select(message):
    uid = message.from_user.id
    age = int(message.text)

    if age < 18:
        bot.send_message(
            uid,
            "Bu bot 18 yaş ve üzeri kullanıcılar içindir."
        )
        return

    if age > 100:
        bot.send_message(
            uid,
            "Geçerli bir yaş gir."
        )
        return

    users[uid]["age"] = age

    bot.send_message(
        uid,
        "Kayıt tamamlandı.",
        reply_markup=menu(uid)
    )


# =========================
# EŞLEŞME
# =========================

@bot.message_handler(func=lambda m: m.text == "🔎 Eşleşme Ara")
def find_match(message):
    uid = message.from_user.id

    if uid in banned:
        return

    if uid not in users or users[uid].get("age") is None:
        bot.send_message(
            uid,
            "Önce /start ile kayıt ol."
        )
        return

    start_matching(uid)


@bot.message_handler(func=lambda m: m.text == "⏭️ Sonraki")
def next_match(message):
    uid = message.from_user.id

    if uid in matches:
        remove_match(uid)

    remove_from_waiting(uid)

    bot.send_message(
        uid,
        "Yeni eşleşme aranıyor..."
    )

    start_matching(uid)


@bot.message_handler(func=lambda m: m.text == "❌ Eşleşmeyi Bitir")
def end_match(message):
    uid = message.from_user.id

    partner = remove_match(uid)

    remove_from_waiting(uid)

    if partner:
        bot.send_message(
            partner,
            "Karşı taraf eşleşmeyi bitirdi.",
            reply_markup=menu(partner)
        )

    bot.send_message(
        uid,
        "Eşleşme bitirildi.",
        reply_markup=menu(uid)
    )


# =========================
# ENGELLE
# =========================

@bot.message_handler(func=lambda m: m.text == "🚫 Engelle")
def block_user(message):
    uid = message.from_user.id

    partner = matches.get(uid)

    if not partner:
        bot.send_message(
            uid,
            "Şu anda eşleştiğin biri yok."
        )
        return

    blocked.setdefault(uid, set()).add(partner)

    remove_match(uid)

    bot.send_message(
        uid,
        "Kullanıcı engellendi.",
        reply_markup=menu(uid)
    )

    bot.send_message(
        partner,
        "Eşleşme sona erdi.",
        reply_markup=menu(partner)
    )


# =========================
# SON EŞLEŞME
# =========================

@bot.message_handler(func=lambda m: m.text == "♻️ Son Eşleşmeyi Bul")
def recover_match(message):
    uid = message.from_user.id

    if not is_vip(uid):
        bot.send_message(
            uid,
            "♻️ Son eşleşmeyi geri getirme özelliği VIP'e özeldir."
        )
        return

    last = users.get(uid, {}).get("last_partner")

    if not last:
        bot.send_message(
            uid,
            "Geri getirilebilecek bir eşleşme yok."
        )
        return

    if last in banned:
        bot.send_message(
            uid,
            "Bu kullanıcı artık kullanılamıyor."
        )
        return

    if is_blocked(uid, last):
        bot.send_message(
            uid,
            "Bu kullanıcı engellenmiş."
        )
        return

    if last in matches:
        bot.send_message(
            uid,
            "Bu kullanıcı şu anda başka biriyle eşleşmiş."
        )
        return

    add_match(uid, last)

    bot.send_message(
        uid,
        "♻️ Son eşleşmen geri getirildi.",
        reply_markup=menu(uid)
    )

    bot.send_message(
        last,
        "♻️ Önceki VIP eşleşmen yeniden bağlandı.",
        reply_markup=menu(last)
    )


# =========================
# GENEL SOHBET
# =========================

@bot.message_handler(func=lambda m: m.text == "💬 Genel Sohbet")
def general_menu(message):
    uid = message.from_user.id

    general_chat.add(uid)

    bot.send_message(
        uid,
        "💬 Genel sohbete katıldın.\n\n"
        "Buraya yazdığın mesajlar genel sohbetteki diğer kullanıcılara gönderilir.\n\n"
        "Çıkmak için tekrar Genel Sohbet butonuna bas.",
        reply_markup=menu(uid)
    )


# =========================
# VIP SATIN AL
# =========================

@bot.message_handler(func=lambda m: m.text == "⭐ VIP Satın Al")
def buy_vip(message):
    uid = message.from_user.id

    if is_vip(uid):
        bot.send_message(
            uid,
            "Zaten VIP üyeliğin aktif."
        )
        return

    prices = [
        types.LabeledPrice(
            label="30 Gün VIP",
            amount=VIP_STARS
        )
    ]

    bot.send_invoice(
        uid,
        title="⭐ VIP Üyelik",
        description="30 günlük VIP üyelik",
        invoice_payload=f"vip_{uid}_{int(time.time())}",
        provider_token="",
        currency="XTR",
        prices=prices
    )


@bot.pre_checkout_query_handler(func=lambda query: True)
def pre_checkout(query):
    bot.answer_pre_checkout_query(
        query.id,
        ok=True
    )


@bot.message_handler(content_types=["successful_payment"])
def successful_payment(message):
    uid = message.from_user.id

    vip_users[uid] = datetime.now() + timedelta(days=VIP_DAYS)

    bot.send_message(
        uid,
        "⭐ VIP üyeliğin aktif edildi.\n\n"
        "30 gün boyunca VIP özelliklerini kullanabilirsin.",
        reply_markup=menu(uid)
    )


# =========================
# VIP MENÜ
# =========================

@bot.message_handler(func=lambda m: m.text == "⭐ VIP Menü")
def vip_menu_handler(message):
    uid = message.from_user.id

    if not is_vip(uid):
        bot.send_message(
            uid,
            "VIP üyeliğin bulunmuyor."
        )
        return

    bot.send_message(
        uid,
        "⭐ VIP özellikleri",
        reply_markup=vip_menu()
    )


@bot.message_handler(func=lambda m: m.text == "👩 Kadın Önceliği")
def vip_female(message):
    uid = message.from_user.id

    if not is_vip(uid):
        return

    users[uid]["vip_female"] = not users[uid]["vip_female"]

    durum = "açıldı" if users[uid]["vip_female"] else "kapatıldı"

    bot.send_message(
        uid,
        f"Kadın önceliği {durum}."
    )


@bot.message_handler(func=lambda m: m.text == "🎂 Yaş Filtresi")
def age_filter(message):
    uid = message.from_user.id

    if not is_vip(uid):
        return

    bot.send_message(
        uid,
        "Yaş aralığını şu şekilde yaz:\n\n18-25"
    )

    users[uid]["waiting_age_filter"] = True


@bot.message_handler(
    func=lambda m: (
        m.from_user.id in users
        and users[m.from_user.id].get("waiting_age_filter") is True
        and m.text
        and "-" in m.text
    )
)
def save_age_filter(message):
    uid = message.from_user.id

    try:
        minimum, maximum = map(
            int,
            message.text.split("-", 1)
        )

        if minimum < 18:
            minimum = 18

        if maximum < minimum:
            raise ValueError

        users[uid]["age_filter"] = (minimum, maximum)
        users[uid]["waiting_age_filter"] = False

        bot.send_message(
            uid,
            f"Yaş filtresi {minimum}-{maximum} olarak ayarlandı."
        )

    except Exception:
        bot.send_message(
            uid,
            "Format yanlış.\nÖrnek: 18-25"
        )


@bot.message_handler(func=lambda m: m.text == "⚡ Anında Eşleş")
def instant_match(message):
    uid = message.from_user.id

    if not is_vip(uid):
        return

    if uid in matches:
        remove_match(uid)

    remove_from_waiting(uid)

    start_matching(uid)


@bot.message_handler(func=lambda m: m.text == "🔒 VIP Odası")
def vip_room(message):
    uid = message.from_user.id

    if not is_vip(uid):
        return

    bot.send_message(
        uid,
        "🔒 VIP odası aktif.\n\n"
        "Burada yalnızca VIP kullanıcılarla eşleşme önceliği uygulanır."
    )


@bot.message_handler(func=lambda m: m.text == "👤 VIP Profil")
def vip_profile(message):
    uid = message.from_user.id

    if not is_vip(uid):
        return

    user = get_user(uid)

    bot.send_message(
        uid,
        "⭐ VIP Profil\n\n"
        f"Yaş: {user.get('age')}\n"
        f"Cinsiyet: {gender_text(user.get('gender'))}\n"
        f"Durum: {user.get('status') or 'Belirlenmedi'}"
    )


@bot.message_handler(func=lambda m: m.text == "🙈 Kullanıcı Adımı Gizle")
def hide_username(message):
    uid = message.from_user.id

    if not is_vip(uid):
        return

    bot.send_message(
        uid,
        "🙈 Kullanıcı adın eşleştiğin kişiye gösterilmez.\n"
        "Bot zaten mesajları anonim olarak iletiyor."
    )


@bot.message_handler(func=lambda m: m.text == "🔄 Tek Tıkla Değiştir")
def one_tap_change(message):
    uid = message.from_user.id

    if not is_vip(uid):
        return

    if uid in matches:
        remove_match(uid)

    remove_from_waiting(uid)

    start_matching(uid)


@bot.message_handler(func=lambda m: m.text == "🔔 Eşleşme Bildirimi")
def match_notifications(message):
    uid = message.from_user.id

    if not is_vip(uid):
        return

    bot.send_message(
        uid,
        "🔔 VIP eşleşme bildirimleri aktif."
    )


@bot.message_handler(func=lambda m: m.text == "🚫 Engellenenle Eşleşme")
def blocked_setting(message):
    uid = message.from_user.id

    if not is_vip(uid):
        return

    bot.send_message(
        uid,
        "🚫 Engellediğin kullanıcılarla tekrar eşleşmezsin."
    )


@bot.message_handler(func=lambda m: m.text == "⭐ VIP Durumu")
def vip_status(message):
    uid = message.from_user.id

    if not is_vip(uid):
        bot.send_message(
            uid,
            "VIP üyeliğin bulunmuyor."
        )
        return

    expiry = vip_users[uid]

    bot.send_message(
        uid,
        "⭐ VIP aktif\n\n"
        f"Bitiş: {expiry.strftime('%d.%m.%Y %H:%M')}"
    )


# =========================
# ADMIN PANELİ
# =========================

@bot.message_handler(func=lambda m: m.text == "🛠 Admin Panel")
def admin_panel(message):
    uid = message.from_user.id

    if not is_admin(uid):
        return

    bot.send_message(
        uid,
        "🛠 Admin Panel",
        reply_markup=admin_menu()
    )


@bot.message_handler(func=lambda m: m.text == "👥 Kullanıcı Sayısı")
def admin_users(message):
    if not is_admin(message.from_user.id):
        return

    bot.send_message(
        message.chat.id,
        f"👥 Toplam kullanıcı: {len(users)}\n"
        f"⭐ VIP kullanıcı: {len(vip_users)}\n"
        f"⏳ Bekleyen: {len(waiting)}\n"
        f"💬 Genel sohbet: {len(general_chat)}"
    )


@bot.message_handler(func=lambda m: m.text == "🟢 Aktif Eşleşmeler")
def admin_matches(message):
    if not is_admin(message.from_user.id):
        return

    count = len(matches) // 2

    bot.send_message(
        message.chat.id,
        f"🟢 Aktif eşleşme: {count}"
    )


@bot.message_handler(func=lambda m: m.text == "🚫 Ban")
def admin_ban(message):
    if not is_admin(message.from_user.id):
        return

    bot.send_message(
        message.chat.id,
        "Banlamak istediğin kullanıcının Telegram ID'sini gönder."
    )

    users[ADMIN_ID]["admin_action"] = "ban"


@bot.message_handler(func=lambda m: m.text == "✅ Ban Aç")
def admin_unban(message):
    if not is_admin(message.from_user.id):
        return

    bot.send_message(
        message.chat.id,
        "Banı kaldırılacak kullanıcının ID'sini gönder."
    )

    users[ADMIN_ID]["admin_action"] = "unban"


@bot.message_handler(func=lambda m: m.text == "🔇 Sustur")
def admin_mute(message):
    if not is_admin(message.from_user.id):
        return

    bot.send_message(
        message.chat.id,
        "Susturulacak kullanıcının ID'sini gönder."
    )

    users[ADMIN_ID]["admin_action"] = "mute"


@bot.message_handler(func=lambda m: m.text == "🔊 Susturma Aç")
def admin_unmute(message):
    if not is_admin(message.from_user.id):
        return

    bot.send_message(
        message.chat.id,
        "Susturması kaldırılacak kullanıcının ID'sini gönder."
    )

    users[ADMIN_ID]["admin_action"] = "unmute"


@bot.message_handler(func=lambda m: m.text == "⭐ VIP Ver")
def admin_give_vip(message):
    if not is_admin(message.from_user.id):
        return

    bot.send_message(
        message.chat.id,
       
