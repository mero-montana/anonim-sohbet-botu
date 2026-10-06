import os
import telebot
from telebot import types

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

bot = telebot.TeleBot(TOKEN)

users = {}
waiting = []
matches = {}

def menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🔎 Eşleşme Ara")
    kb.row("⏭️ Sonraki", "❌ Eşleşmeyi Bitir")
    return kb

@bot.message_handler(commands=["start"])
def start(message):
    uid = message.from_user.id

    if uid not in users:
        users[uid] = {"age": False, "gender": None}

    if not users[uid]["age"]:
        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton(
                "18 yaşından büyüğüm", callback_data="age_yes"
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
        "Ana menüye hoş geldin.\n\n"
        "🔎 Eşleşme Ara butonuna basarak anonim sohbet başlatabilirsin.",
        reply_markup=menu()
    )

def gender_menu(uid):
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton("Erkek", callback_data="gender_erkek"),
        types.InlineKeyboardButton("Kadın", callback_data="gender_kadin")
    )
    kb.row(
        types.InlineKeyboardButton("Diğer", callback_data="gender_diger")
    )

    bot.send_message(
        uid,
        "Cinsiyetini seç:",
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda call: call.data == "age_yes")
def age_confirm(call):
    uid = call.from_user.id
    users[uid]["age"] = True

    bot.answer_callback_query(call.id, "Yaş onaylandı.")
    bot.edit_message_text(
        "Yaş onaylandı.\n\nŞimdi cinsiyetini seç:",
        uid,
        call.message.message_id
    )
    gender_menu(uid)

@bot.callback_query_handler(func=lambda call: call.data.startswith("gender_"))
def gender_select(call):
    uid = call.from_user.id
    gender = call.data.replace("gender_", "")

    users[uid]["gender"] = gender

    bot.answer_callback_query(call.id, "Cinsiyet seçildi.")
    bot.send_message(
        uid,
        "Cinsiyet seçimin kaydedildi.\n\n"
        "Artık anonim eşleşme yapabilirsin.",
        reply_markup=menu()
    )

@bot.message_handler(func=lambda m: m.text == "🔎 Eşleşme Ara")
def find_match(message):
    uid = message.from_user.id

    if uid in matches:
        bot.send_message(uid, "Zaten bir eşleşmen var.")
        return

    if uid in waiting:
        bot.send_message(uid, "Şu anda eşleşme bekliyorsun.")
        return

    if waiting:
        partner = waiting.pop(0)

        matches[uid] = partner
        matches[partner] = uid

        bot.send_message(
            uid,
            "🎉 Bir eşleşme bulundu!\n\n"
            "Artık anonim olarak sohbet edebilirsiniz.",
            reply_markup=menu()
        )

        bot.send_message(
            partner,
            "🎉 Bir eşleşme bulundu!\n\n"
            "Artık anonim olarak sohbet edebilirsiniz.",
            reply_markup=menu()
        )
    else:
        waiting.append(uid)
        bot.send_message(
            uid,
            "⏳ Eşleşme aranıyor...\n\n"
            "Bir kullanıcı bulunduğunda sana haber vereceğim.",
            reply_markup=menu()
        )

@bot.message_handler(func=lambda m: m.text == "❌ Eşleşmeyi Bitir")
def end_match(message):
    uid = message.from_user.id

    if uid in matches:
        partner = matches[uid]

        del matches[uid]
        if partner in matches:
            del matches[partner]

        bot.send_message(
            uid,
            "❌ Eşleşme bitirildi.",
            reply_markup=menu()
        )

        bot.send_message(
            partner,
            "❌ Karşı taraf sohbeti bitirdi.",
            reply_markup=menu()
        )
    else:
        if uid in waiting:
            waiting.remove(uid)

        bot.send_message(
            uid,
            "Aktif eşleşmen yok.",
            reply_markup=menu()
        )

@bot.message_handler(func=lambda m: m.text == "⏭️ Sonraki")
def next_match(message):
    end_match(message)
    find_match(message)

@bot.message_handler(content_types=[
    "text",
    "photo",
    "video",
    "voice",
    "audio",
    "document",
    "sticker",
    "animation"
])
def relay(message):
    uid = message.from_user.id

    if uid not in matches:
        return

    partner = matches[uid]

    try:
        bot.copy_message(
            partner,
            uid,
            message.message_id,
            protect_content=True
        )
    except Exception:
        bot.send_message(
            uid,
            "Mesaj gönderilemedi."
        )

print("Anonim sohbet botu çalışıyor...")
bot.infinity_polling()
