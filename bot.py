import os
import telebot
from telebot import types

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN bulunamadi")

bot = telebot.TeleBot(TOKEN)

users = {}
waiting = []
matches = {}
blocked = {}


def get_user(user_id):
    if user_id not in users:
        users[user_id] = {
            "confirmed": False,
            "gender": None,
            "age": None
        }

    return users[user_id]


def remove_waiting(user_id):
    while user_id in waiting:
        waiting.remove(user_id)


def menu():
    keyboard = types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    keyboard.row("Eşleş")
    keyboard.row("Eşleşmeyi Bitir")

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


def find_partner(user_id):
    for candidate in waiting:

        if candidate == user_id:
            continue

        if candidate in matches:
            continue

        if candidate in blocked.get(user_id, set()):
            continue

        if user_id in blocked.get(candidate, set()):
            continue

        return candidate

    return None


def start_matching(user_id):

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
        "Eşleşme bulundu. Anonim sohbet başlayabilir.",
        reply_markup=menu()
    )

    bot.send_message(
        partner,
        "Eşleşme bulundu. Anonim sohbet başlayabilir.",
        reply_markup=menu()
    )


def finish_match(user_id):

    partner = matches.pop(
        user_id,
        None
    )

    if partner is not None:
        matches.pop(
            partner,
            None
        )

        bot.send_message(
            partner,
            "Karşı taraf eşleşmeyi bitirdi.",
            reply_markup=menu()
        )

    remove_waiting(user_id)

    bot.send_message(
        user_id,
        "Eşleşme bitirildi.",
        reply_markup=menu()
    )


@bot.message_handler(commands=["start"])
def start(message):

    user_id = message.from_user.id

    user = get_user(user_id)

    if user["confirmed"]:

        bot.send_message(
            user_id,
            "Tekrar hoş geldin.",
            reply_markup=menu()
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

    gender = call.data.replace(
        "gender_",
        ""
    )

    get_user(user_id)["gender"] = gender

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

    age = call.data.replace(
        "age_",
        ""
    )

    get_user(user_id)["age"] = age

    bot.answer_callback_query(
        call.id,
        "Kaydedildi"
    )

    bot.send_message(
        user_id,
        "Profilin hazır.",
        reply_markup=menu()
    )


@bot.message_handler(
    func=lambda message: message.text == "Eşleş"
)
def match_button(message):

    start_matching(
        message.from_user.id
    )


@bot.message_handler(
    func=lambda message: message.text == "Eşleşmeyi Bitir"
)
def finish_button(message):

    finish_match(
        message.from_user.id
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

    partner = matches.get(user_id)

    if partner is None:
        return

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


print("Bot çalışıyor...")

bot.infinity_polling(
    skip_pending=True,
    timeout=30,
    long_polling_timeout=30
    )
