#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Speach to Text Bot
# Created by Alexander Hirschfeld

import argparse
import logging
import subprocess
import speech_recognition as sr
from os import getcwd
from json import load
from tempfile import NamedTemporaryFile
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from telegram import TelegramError, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, Filters, MessageHandler, CallbackQueryHandler


AUTHTOKEN = None
mClient = None
mDB = None
LANGUAGES = None

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

r = sr.Recognizer()

cwd = getcwd()

def updateKeyboard(chat_data):
    keyboard = list()
    for i in range(0,len(chat_data['langlist'][:12]),2):
        if i >= (len(chat_data['langlist']) -1):
            keyboard.append([InlineKeyboardButton(chat_data['langlist'][i], callback_data=str(i))])
            chat_data[str(i)] = chat_data['langlist'][i]
        else:
            keyboard.append([InlineKeyboardButton(chat_data['langlist'][i], callback_data=str(i)),
                             InlineKeyboardButton(chat_data['langlist'][i+1], callback_data=str(i+1))])
            chat_data[str(i)] = chat_data['langlist'][i]
            chat_data[str(i+1)] = chat_data['langlist'][i+1]
    
    chat_data['working'] = chat_data['langlist'][:12]
    chat_data['langlist'] = chat_data['langlist'][12:]
    
    keyboard.append([InlineKeyboardButton('More', callback_data='more'),
                     InlineKeyboardButton('Cancel', callback_data='cancel')])
    return keyboard

def updateKeyboardDial(chat_data):
    keyboard = list()
    for i in range(0,len(chat_data['langlist']),2):
        if i >= len(chat_data['langlist'])-1:
            keyboard.append([InlineKeyboardButton(chat_data['langlist'][i][1], callback_data=str(i))])
            chat_data[str(i)] = chat_data['langlist'][i][0]
        else:
            keyboard.append([InlineKeyboardButton(chat_data['langlist'][i][1], callback_data=str(i)),
                             InlineKeyboardButton(chat_data['langlist'][i+1][1], callback_data=str(i+1))])
            chat_data[str(i)] = chat_data['langlist'][i][0]
            chat_data[str(i+1)] = chat_data['langlist'][i+1][0]
    
    chat_data['langlist'] = []
    chat_data['working'] = []

    keyboard.append([InlineKeyboardButton('Return', callback_data='more'),
                     InlineKeyboardButton('Cancel', callback_data='cancel')])
    return keyboard

def checkValidCommand(text, username):
    text = text.split()[0]
    try:
        at = text.index('@')+1
        if text[at:] == username:
            return True
        return False
    except ValueError:
        return True
    
def start(bot, update):
    if not checkValidCommand(update.message.text, bot.username):
        return
    update.message.reply_text("Welcome to a Speech To Text bot! This bot will take any voice message sent to it and will try to translate it to text!")

def help(bot, update):
    if not checkValidCommand(update.message.text, bot.username):
        return
    reply_text = "Send me a voice message, forward me a voice message, add me to groups! I will try to transcribe anything sent!\n\n"
    reply_text += "/chooselang will let you choose a language and dialect.\n"
    reply_text += "/chooselang (language code) will let you set the language directly with a supported language code.\n"
    reply_text += "/help prints this."
    update.message.reply_text(reply_text)
    


def chooseLanguage(bot, update, chat_data, args):
    if not checkValidCommand(update.message.text, bot.username):
        return
    logger.info("Choose language received")
    if args:
        for key in LANGUAGES:
            for lang in LANGUAGES[key]:
                if lang[0] == args[0]:
                    reply_text = 'Set language to: %s' % args[0]
                    update.message.reply_text(reply_text)
                    return
                
    chat_data['choosing'] = True
    logger.debug("Starting choose language inline mess")
    reply_text = "Please choose your language, or the closest.\n"
    if not 'lang' in chat_data:
        reply_text += "Current language selected: en-US"
        chat_data['lang'] = 'en-US'
    
    chat_data['langlist'] = sorted(LANGUAGES.keys())
    keyboard = InlineKeyboardMarkup(updateKeyboard(chat_data))
    update.message.reply_text(reply_text, reply_markup=keyboard, quote=False)
    
    
def callbackHandler(bot, update, chat_data):
    logger.debug("Callback handler")
    callbackquery = update.callback_query
    querydata = callbackquery.data
    if not 'lang' in  chat_data:
        chat_data['lang'] = ""
        
    if querydata == 'more':
        chat_data['choosing'] = True
        chat_data['choosingdialect'] = False
        logger.debug('more')
        if not chat_data['langlist']:
            chat_data['langlist'] = sorted(LANGUAGES.keys())
        reply_markup = InlineKeyboardMarkup(updateKeyboard(chat_data))
        callbackquery.edit_message_reply_markup(reply_markup = reply_markup)           
        return
    
    elif querydata == 'cancel':
        logger.debug('cancel')
        reply_text = "Language set to: %s" % chat_data['lang']
        callbackquery.edit_message_text(text=reply_text)
        chat_data['choosing'] = False
        chat_data['choosingdialect'] = False
    else:
        if chat_data['choosing']:
            chat_data['choosing'] = False
            chat_data['choosingdialect'] = True
            logger.debug("Chosen %s" % querydata)
            lang = chat_data[querydata]
            chat_data['langlist'] = LANGUAGES[lang]
            reply_markup = InlineKeyboardMarkup(updateKeyboardDial(chat_data))
            reply_text = "Chosen %s, choose dialect" % lang
            callbackquery.edit_message_text(text=reply_text, reply_markup=reply_markup)
            logger.debug("prompting dialect.")
        elif chat_data['choosingdialect']:
            logger.debug('Chosen Dialect: %s', querydata)
            lang = chat_data[querydata]
            chat_data['choosingdialect'] = False
            reply_text = "Language set to: %s" % lang
            chat_data['lang'] = lang
            callbackquery.edit_message_text(reply_text)
            logger.debug('finished')
            

def receiveMessage(bot, update, chat_data):
    logger.info("Received a message")
    
    if not 'lang' in chat_data:
        update.message.reply_text("No language set through /chooselang, defaulting to en-US.", quote=False)
        chat_data['lang'] = 'en-US'
        
    selectedLang = chat_data['lang']
    
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
                    recognized = r.recognize_google(audio, show_all=True, language=selectedLang)
                    logger.debug("Translated")
                    logger.debug("Full Text: %s" (str(recognized)))
                    alts = sorted(recognized['alternative'], key=lambda conf: conf['confidence'], reverse=True)
                    reply_text = "Confidence: %s, Lang: %s\nText:\n%s"%(alts[0]['confidence'],chat_data['lang'], alts[0]['transcript'])
                   
                except sr.UnknownValueError:
                    print("Google Speech Recognition could not understand audio")
                    reply_text = "Something happened."
                except sr.RequestError as e:
                    print("Could not request results from Google Speech Recognition service; {0}".format(e))
                    reply_text = "Could not access Google, try again later."
            
                update.message.reply_text(reply_text)
        
def sigHandler(signum, frame):
    logger.debug('Closing Mongo connection')
    mClient.close()
     

def error(bot, update, error):
    logger.warn('Update "%s" cause error "%s"' %(update, error))

def startFromCLI():
    global AUTHTOKEN, mClient, mDB, LANGUAGES
    parser = argparse.ArgumentParser()
    parser.add_argument('auth', type=str, help="The Auth Token given by Telegram's @botfather")
    parser.add_argument('-l','--llevel', default='debug', choices=['debug','info','warn','none'], 
                        help='Logging level for the logger, default = debug')
    parser.add_argument('-muri','--mongoURI', default='mongodb://localhost:27017', 
                        help="The MongoDB URI for connection and auth")
    parser.add_argument('-mDB', '--mongoDB', default="stt",
                        help="The database for MongoDB, default is stt")
    parser.add_argument('-lp','--langpack', default='languages.json', 
                        help='Location to the file that contains the JSON object listing languages.')
    logLevel = {'none':logging.NOTSET,'debug':logging.DEBUG,'info':logging.INFO,'warn':logging.WARNING}
    
    args = parser.parse_args()
    logger.setLevel(logLevel[args.llevel])
    
    with open(args.langpack, 'r') as f:
        LANGUAGES = load(f)
        logger.debug("Languages %s" % str(LANGUAGES.keys()))
    
    AUTHTOKEN = args.auth
    mClient = args.mongoURI
    mDB = args.mongoDB

def main():
    global mClient, mDB    
    try:
        mClient = MongoClient(mClient)
        mDB = mClient[mDB]
        mClient.admin.command('ismaster')
        logger.debug('Mongo Connected')
    except ConnectionFailure:
        logger.warn('MongoDB not connected')
        raise
    
    updater = Updater(AUTHTOKEN, user_sig_handler=sigHandler)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start',start))
    dp.add_handler(CommandHandler('help',help))
    dp.add_handler(CommandHandler('chooselang', chooseLanguage, pass_chat_data=True, pass_args=True))
    #dp.add_handler(InlineQueryHandler(inlineQuery))
    dp.add_handler(MessageHandler(Filters.voice, receiveMessage, pass_chat_data=True))
    
    dp.add_handler(CallbackQueryHandler(callbackHandler, pass_chat_data=True))

    dp.add_error_handler(error)

    updater.start_polling()
    logger.debug("Setiup complete, Idling.")
    updater.idle()


if __name__ == '__main__':
    startFromCLI()
    main()  