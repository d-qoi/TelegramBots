#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Speach to Text Bot
# Created by Alexander Hirschfeld

import argparse
import logging
import subprocess
import speech_recognition as sr
from os import getcwd
from tempfile import NamedTemporaryFile
from telegram import TelegramError
from telegram.ext import Updater, CommandHandler, Filters, MessageHandler

AUTHTOKEN = None

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

r = sr.Recognizer()

cwd = getcwd()


def start(bot, update):
    update.message.reply_text("Welcome to a Speech To Text bot! This bot will take any voice message sent to it and will try to translate it to text!")

def help(bot, update):
    update.message.reply_text("Send me a voice message, forward me a voice message, add me to groups! I will try to transcribe anything sent!")

# def inlineQuery(bot, update):
#     query = update.inline_query
#     results = list()

#     results.append(InlineQueryResultArticle(id=uuid4(), title="Test",
#         input_message_content=InputTextMessageContent("Test")))

#     logger.info(query)

def receiveMessage(bot, update):
    logger.info("Received a message")
    if update.message.voice:
        logger.debug("Is a voice message")
        voiceID = update.message.voice.file_id
        
        with NamedTemporaryFile(suffix='.ogg', dir=cwd) as inFile, NamedTemporaryFile(suffix='.wav', dir=cwd) as outFile:
            try:
                file = bot.getFile(file_id = voiceID)
                logger.debug("Got the file")
            except TelegramError:
                logger.warn("Failed to get a file.")
                raise
                        
        
            file.download(inFile.name)
            #file.download()
            logger.debug("Downloaded the file")
            print(inFile.name)
            command = ['ffmpeg','-y','-sample_fmt','s16','-i', inFile.name, outFile.name]
            subprocess.run(command, stdout=subprocess.PIPE)
            #logger.debug('oggdec output: \n %s' % p)
            
            with sr.AudioFile(outFile) as audioFile:
                audio = r.record(audioFile)
                logger.debug("Attempting to translate")
                reply_text = 'Something very bad happened.'
                try:
                    recognized = r.recognize_google(audio, show_all=True)
                    logger.debug("Translated")
                    alts = sorted(recognized['alternative'], key=lambda conf: conf['confidence'], reverse=True)
                    reply_text = "Confidence: %s\nText:\n%s"%(alts[0]['confidence'], alts[0]['transcript'])
                   
                except sr.UnknownValueError:
                    print("Google Speech Recognition could not understand audio")
                    reply_text = "Something happened."
                except sr.RequestError as e:
                    print("Could not request results from Google Speech Recognition service; {0}".format(e))
                    reply_text = "Could not access Google, try again later."
            
                update.message.reply_text(reply_text)
        
       
     

def error(bot, update, error):
    logger.warn('Update "%s" cause error "%s"' %(update, error))

def startFromCLI():
    global AUTHTOKEN
    parser = argparse.ArgumentParser()
    parser.add_argument('auth', type=str, help="The Auth Token given by Telegram's @botfather")
    parser.add_argument('-l','--llevel', default='debug', choices=['debug','info','warn','none'], help='Logging level for the logger, default = debug')
    logLevel = {'none':logging.NOTSET,'debug':logging.DEBUG,'info':logging.INFO,'warn':logging.WARNING}
    
    args = parser.parse_args()
    logger.setLevel(logLevel[args.llevel])
    
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