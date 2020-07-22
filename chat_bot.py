# Setting up Chatterbot
import os
import json
import random
import dateutil.parser

from chatterbot import ChatBot
from chatterbot.trainers import ListTrainer

# Train the bot
english_bot = ChatBot("English Bot",
                      storage_adapter="chatterbot.storage.SQLStorageAdapter",
                      database_uri=os.environ.get("DATABASE_URL"))

# Setting telegram things
tg_token = os.environ.get("BOT_TOKEN")

import logging
from telegram.ext import CommandHandler, MessageHandler, Filters, Updater

updater = Updater(token=tg_token)
dispatcher = updater.dispatcher

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


def start(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Olá :)")


start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)


def reply(bot, update):
    userText = str(update.message.text)
    botName = bot.name

    is_reply_to_bot = False
    if update.message.reply_to_message is not None:
        # Train message responses
        train_data = [update.message.reply_to_message.text, update.message.text]
        list_trainer = ListTrainer(english_bot)
        list_trainer.train(train_data)

        is_reply_to_bot = update.message.reply_to_message.from_user.username == bot.username

    answer = str(english_bot.get_response(userText))

    # TODO: Move answer probability to a config file
    if random.random() <= 0.15 or botName in userText or is_reply_to_bot:
        bot.send_message(chat_id=update.message.chat_id, text=answer)


reply_handler = MessageHandler(Filters.text, reply)
dispatcher.add_handler(reply_handler)


def train(bot, update):
    file = bot.getFile(update.message.document.file_id)
    rawData = file.download_as_bytearray()
    data = rawData.decode('utf8')
    messages = json.loads(data)

    train_data = []
    list_trainer = ListTrainer(english_bot)
    last_date = None

    for message in messages["messages"]:
        if message["text"] is str:
            train_data.append(message["text"])
        date = dateutil.parser.parse(message["date"])

        if last_date is not None:
            diff = date - last_date
            if diff.seconds >= 60 * 60 * 4:
                list_trainer.train(train_data)
                train_data = []
        last_date = date


train_handler = MessageHandler(Filters.document, train)
dispatcher.add_handler(train_handler)


def setup_webhook(updater, token):
    webhook = os.environ.get('WEBHOOK')
    port = int(os.environ.get('PORT', '8443'))
    updater.start_webhook(listen="0.0.0.0",
                          port=port,
                          url_path=token)
    updater.bot.set_webhook(webhook + token)


setup_webhook(updater, tg_token)
updater.idle()
