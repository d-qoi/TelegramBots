#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Speach to Text Bot
# Created by Alexander Hirschfeld

import argparse
import logging
import speech_recognition as sr
from uuid import uuid4
from pymongo import MongoClient
from tempfile import TemporaryFile
from telegram import InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Updater, InlineQueryHandler, CommandHandler, Filters, MessageHandler

AUTHTOKEN = None

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

r = sr.Recognizer()


def start(bot, update):
    update.message.reply_text("Start!")

def help(bot, update):
    update.message.reply_text("Help!")

# def inlineQuery(bot, update):
#     query = update.inline_query
#     results = list()

#     results.append(InlineQueryResultArticle(id=uuid4(), title="Test",
#         input_message_content=InputTextMessageContent("Test")))

#     logger.info(query)

def receiveMessage(bot, update):
    logger.debug("Recieved a message")
    if update.message.voice:
        logger.debug("Is a voice message")
        voiceID = update.message.voice.file_id
        
        try:
            file = bot.getFile(file_id = voiceID)
            logger.debug("Got the file")
        except telegram.TelegramError:
            logger.warn("Failed to get a file.")

        with TemporaryFile() as tfile:
            file.download(out=tfile)
            logger.debug("Downloaded the file")
            with sr.AudioFile(tfile) as audioFile:
                audio = r.record(audioFile)
                logger.debug("Attempting to translate")
                try:
                    recognized = r.recognize_google(audio, show_all=True)
                    logger.debug("Translated")
                except sr.UnknownValueError:
                    print("Google Speech Recognition could not understand audio")
                except sr.RequestError as e:
                    print("Could not request results from Google Speech Recognition service; {0}".format(e))

        update.message.reply_text(recognized)
    

def error(bot, update, error):
    logger.warn('Update "%s" cause error "%s"' %(update, error))

def startFromCLI():
    global AUTHTOKEN
    parser = argparse.ArgumentParser()
    parser.add_argument('auth', type=str, help="The Auth Token given by Telegram's @botfather")
    parser.add_argument('-l','--llevel', default='debug', choices=['debug','info','warn','none'], help='Logging level for the logger, default = debug')
    logLevel = {'none':logging.NOTSET,'debug':logging.DEBUG,'info':logging.INFO,'warn':logging.WARNING}
    args = parser.parse_args()

    AUTHTOKEN = args.auth

def main():
    updater = Updater(AUTHTOKEN)

    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start',start))
    dp.add_handler(CommandHandler('help',help))
    #dp.add_handler(InlineQueryHandler(inlineQuery))
    dp.add_handler(MessageHandler(Filters.all, receiveMessage))

    dp.add_error_handler(error)

    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    startFromCLI()
    main()  