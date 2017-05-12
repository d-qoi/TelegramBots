#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Speach to Text Bot
# Created by Alexander Hirschfeld

import argparse
import base64
import json
import logging
import requests
import subprocess
import time
import wave
from json import load
from os import getcwd
from pymongo import MongoClient
from tempfile import NamedTemporaryFile
from telegram import TelegramError, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, Filters, MessageHandler, CallbackQueryHandler
from telegram.ext.dispatcher import run_async

from requesthistory import requesthistory


AUTHTOKEN = None
LANGUAGES = None
AUTHKEY = ""
MCLIENT = None
MDB = None

TRACKING = None

HISTORY_ALL = list()
HISTORY_VOICE = list()

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

cwd = getcwd()

def updateChatFile(chat_data, chat_id):
    result = MDB.groups.update({'_id':chat_id}, chat_data, upsert=True)
    if 'upserted' in result:
        chat_data['lang'] = 'en-US'

def getChatFile(chat_data, chat_id):
    result = MDB.groups.find_one({'_id':chat_id})
    if result:
        chat_data['lang'] = result['lang']

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
    
@run_async
def start(bot, update):
    TRACKING.total.post()
    if not checkValidCommand(update.message.text, bot.username):
        return
    update.message.reply_text("Welcome to a Speech To Text bot! This bot will take any voice message sent to it and will try to translate it to text!")

@run_async
def help(bot, update):
    TRACKING.total.post()
    logger.info("Help called")
    if not checkValidCommand(update.message.text, bot.username):
        return
    reply_text = "Send me a voice message, forward me a voice message, add me to groups! I will try to transcribe anything sent!\n\n"
    reply_text += "/chooselang will let you choose a language and dialect.\n"
    reply_text += "/chooselang (language code) will let you set the language directly with a supported language code.\n"
    reply_text += "/help prints this. and /info prints info."
    update.message.reply_text(reply_text)
 
 
@run_async
def info(bot, update):
    TRACKING.total.post()
    logger.info("info called")
    if not checkValidCommand(update.message.text, bot.username):
        return
    reply_text = "This bot uses the Google Speech API for transcription.\n\n"
    reply_text += "Developed and maintained by @ytkileroy.\n"
    reply_text += "If you wish to help support development of this bot, consider becoming a patron at: https://www.patreon.com/YTKileroy.\n\n"
    reply_text += "Please share this bot with everyone!\n"
    reply_text += "And if you want to know how this bot is doing, try calling /getStats"
    update.message.reply_text(reply_text)
    
@run_async   
def chooseLanguage(bot, update, chat_data, args):
    TRACKING.total.post()
    if not checkValidCommand(update.message.text, bot.username):
        return
    logger.info("Choose language received")
    if args:
        for key in LANGUAGES:
            for lang in LANGUAGES[key]:
                if lang[0] == args[0]:
                    reply_text = 'Set language to: %s' % args[0]
                    update.message.reply_text(reply_text)
                    chat_data['lang'] = args[0]
                    
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
    
@run_async
def callbackHandler(bot, update, chat_data):
    logger.debug("Callback handler")
    TRACKING.total.post()
    callbackquery = update.callback_query
    querydata = callbackquery.data
    if not 'lang' in  chat_data:
        getChatFile(chat_data, update.message.chat.id)
        if not 'lang' in chat_data:
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
            updateChatFile(chat_data, callbackquery.message.chat.id)
            logger.debug('finished')
            
                    
def getTranslations(chunk, lang, rate):
    baseURL = "https://speech.googleapis.com/v1beta1/speech:asyncrecognize?key={0}".format(AUTHKEY)
    body = dict()
    config = dict()
    config['encoding'] = 'LINEAR16'
    config['sampleRate'] = rate
    config['languageCode'] = lang
    config['maxAlternatives'] = 1
    body['config'] = config
    
    audio = dict()
    audio['content'] = base64.b64encode(chunk).decode('UTF-8')
    body['audio'] = audio
    
    r = requests.post(baseURL, data=json.dumps(body))
    logger.debug("Response from google received.")
    logger.debug("%s",r.text)
    
    if r.status_code != 200:
        logger.warning("Response code: %d\nData:\n%s"%(r.status_code, r.text))
        raise ConnectionError
    
    logger.debug("Valid response.")
    resp = json.loads(r.text)
    logger.debug("Name:%s"%(resp['name']))
    return resp['name']
                
def downloadTranslation(chunks):
    text = ""
    confidence = 0;
    for chunk in chunks:
        URL = 'https://speech.googleapis.com/v1beta1/operations/%s?key=%s'%(chunk, AUTHKEY)
        r = requests.get(URL)
        
        if r.status_code != 200:
            logger.warning("Response code: %d\nData:\n%s"%(r.status_code, r.text))
            raise ConnectionError
        
        body = json.loads(r.text)
        logger.debug("%s"%r.text)
        
        while not 'done' in body or not body['done']:
            time.sleep(1)
            r = requests.get(URL)
            logger.debug("%s"%r.text)
            body = json.loads(r.text)
            
        logger.debug("Translated: %s"%(body['response']['results']))
        
        alts = sorted(body['response']['results'], key=lambda resp: resp['alternatives'][0]['confidence'], reverse=True)
        
        logger.debug("Alts: %s"%alts)
        text += alts[0]['alternatives'][0]['transcript'] + ' '
        confidence += alts[0]['alternatives'][0]['confidence']
        
    return text, confidence/float(len(chunks))
            
@run_async                
def receiveMessage(bot, update, chat_data):
    logger.info('Message Received')
    TRACKING.voice.post()
    if not 'lang' in chat_data:
        getChatFile(chat_data, update.message.chat.id)
        if not 'lang' in chat_data:
            update.message.reply_text("No language set through /chooselang, defaulting to en-US.", quote=False)
            chat_data['lang'] = 'en-US'
        
    lang = chat_data['lang']
    
    try:
        file = bot.getFile(file_id = update.message.voice.file_id)
        logger.debug("Got the file")
    except TelegramError:
        logger.warn("Failed to get a file.")
        raise
    
    with NamedTemporaryFile(suffix='.ogg', dir=cwd) as inFile, NamedTemporaryFile(suffix='.wav', dir=cwd) as outFile:
        try:
            logger.debug("%s, %s"%(inFile.name, outFile.name))
            file.download(inFile.name)
            logger.debug("File received")
            
            
            command = ['ffmpeg','-y','-i',inFile.name, outFile.name]
            logger.debug("Command: %s", command)
            subprocess.run(command)
            
            wavefile = wave.open(outFile, 'rb')
            
            frames = wavefile.getnframes()
            rate = wavefile.getframerate()
            duration = frames / float(rate)
            logger.debug("Frames: %f, rate: %d, duration: %f"%(frames, rate, duration))
            
            chunks = list()
            
            while duration > 0:
                logger.debug("remaining time: %d"%duration)
                chunk = wavefile.readframes(rate*55)
                try:
                    chunks.append(getTranslations(chunk, lang, rate))
                    logger.debug("Print: %s"%chunks)
                except ConnectionError:
                    logger.debug("Connection Error.")
                    update.message.reply_text("An error occurred, please try again.")
                    return
                
                duration-=55
                
                
            logger.debug("List of chunks: %s"%chunks)
            logger.debug("Trying to download")
            text, confidence = downloadTranslation(chunks)
            logger.debug("Translated text: %s\nConfidence: %f"%(text, confidence))
            update.message.reply_text("Confidence: %f, Lang: %s\nText::\n%s"%(confidence, lang, text))
        
        except Exception as e:
            logger.debug("Other error: %s"%e)
            update.message.reply_text("An error occurred, please try again.")
     
@run_async
def countme(bot, update):
    TRACKING.total.post()

@run_async
def getMessageStats(bot, update):
    TRACKING.total.post()
    logger.info("Stats called.")
    reply_text = "Stats for @listenformebot\n"
    reply_text += "Total in last hour: %s\n"%(str(TRACKING.total.getCountHour()))
    reply_text += "Voice in last hour: %s\n"%str(TRACKING.voice.getCountHour())
    reply_text += "Total in last minute: %s\n"%str(TRACKING.total.getCountMinute())
    reply_text += "Voice in last minute: %s\n"%str(TRACKING.voice.getCountMinute())
    update.message.reply_text(reply_text)

def error(bot, update, error):
    logger.warn('Update "%s" cause error "%s"' %(update, error))

def startFromCLI():
    global AUTHTOKEN, LANGUAGES, AUTHKEY, MDB, MCLIENT, TRACKING
    parser = argparse.ArgumentParser()
    parser.add_argument('auth', type=str, help="The Auth Token given by Telegram's @botfather")
    parser.add_argument('-l','--llevel', default='debug', choices=['debug','info','warn','none'], 
                        help='Logging level for the logger, default = debug')
    parser.add_argument('-lp','--langpack', default='languages.json', 
                        help='Location to the file that contains the JSON object listing languages.')
    parser.add_argument('-g','--googleKey', help="Auth Key for google account")
    parser.add_argument('-muri','--MongoURI', default='mongodb://localhost:27017', help="The MongoDB URI for connection and auth")
    parser.add_argument('-mdb','--MongoDB', default='speech', help="The MongoDB Database that this will use")
    
    logLevel = {'none':logging.NOTSET,'debug':logging.DEBUG,'info':logging.INFO,'warn':logging.WARNING}
    
    args = parser.parse_args()
    logger.setLevel(logLevel[args.llevel])
    
    with open(args.langpack, 'r') as f:
        LANGUAGES = load(f)
        logger.debug("Languages %s" % str(LANGUAGES.keys()))
    
    AUTHTOKEN = args.auth
    AUTHKEY = args.googleKey
    logger.debug(AUTHKEY)
    MCLIENT = MongoClient(args.MongoURI)
    MDB = MCLIENT[args.MongoDB]
    
    TRACKING = requesthistory('total', 'voice')

def main():
    
    updater = Updater(AUTHTOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('help', help))
    dp.add_handler(CommandHandler('info', info))
    dp.add_handler(CommandHandler('getStats', getMessageStats))
    dp.add_handler(CommandHandler('chooselang', chooseLanguage, pass_chat_data=True, pass_args=True))

    dp.add_handler(MessageHandler(Filters.voice, receiveMessage, pass_chat_data=True))
    dp.add_handler(MessageHandler(Filters.all, countme))
    
    dp.add_handler(CallbackQueryHandler(callbackHandler, pass_chat_data=True))

    dp.add_error_handler(error)

    updater.start_polling()
    logger.debug("Setiup complete, Idling.")
    updater.idle()


if __name__ == '__main__':
    startFromCLI()
    main()  
