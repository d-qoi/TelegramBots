#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Speach to Text Bot
# Created by Alexander Hirschfeld

import argparse
import logging
import subprocess
import base64
import requests
import wave
import json
import time
from os import getcwd
from json import load
from tempfile import NamedTemporaryFile
from telegram import TelegramError, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, Filters, MessageHandler, CallbackQueryHandler
from telegram.ext.dispatcher import run_async



AUTHTOKEN = None
LANGUAGES = None
AUTHKEY = ""

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

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
    
@run_async
def start(bot, update):
    if not checkValidCommand(update.message.text, bot.username):
        return
    update.message.reply_text("Welcome to a Speech To Text bot! This bot will take any voice message sent to it and will try to translate it to text!")

@run_async
def help(bot, update):
    if not checkValidCommand(update.message.text, bot.username):
        return
    reply_text = "Send me a voice message, forward me a voice message, add me to groups! I will try to transcribe anything sent!\n\n"
    reply_text += "/chooselang will let you choose a language and dialect.\n"
    reply_text += "/chooselang (language code) will let you set the language directly with a supported language code.\n"
    reply_text += "/help prints this."
    update.message.reply_text(reply_text)
 
@run_async   
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
                    chat_data['langlist'] = args[0]
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
        logger.info("Response code: %d\nData:\n%s"%(r.status_code, r.text))
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
        body = json.loads(r.text)
        logger.debug("%s"%r.text)
        while not 'done' in body or not body['done']:
            time.sleep(1)
            r = requests.get(URL)
            logger.debug("%s"%r.text)
            body = json.loads(r.text)
            
        logger.debug("Translated: %s"%(body['response']['results'][0]['alternatives'][0]))
        
        text += body['response']['results'][0]['alternatives'][0]['transcript']
        confidence += body['response']['results'][0]['alternatives'][0]['confidence']
        
    return text, confidence
            
    
def receiveMessage(bot, update, chat_data):
    logger.info('Message Received')
    
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
    #with mkstemp(suffix='.ogg', dir=cwd) as inFile, mkstemp(suffix='.wav', dir=cwd) as outFile:
        try:
            logger.debug("%s, %s"%(inFile.name, outFile.name))
            file.download(inFile.name)
            #time.sleep(30)
            logger.debug("File received")
            command = ['ffmpeg','-y','-i',inFile.name, outFile.name]
            logger.debug("Command: %s", command)
            subprocess.run(command)
            wavefile = wave.open(outFile, 'rb')
            frames = wavefile.getnframes()
            rate = wavefile.getframerate()
            duration = frames / float(rate)
            logger.debug("Frames: %f, rate: %d, duration: %f"%(frames, rate, duration))
            while duration > 0:
                chunks = []
                logger.debug("remaining time: %d"%duration)
                chunk = wavefile.readframes(rate*55)
                try:
                    chunks.append(getTranslations(chunk, lang, rate))
                except ConnectionError:
                    logger.debug("Connection Error.")
                    update.message.reply_text("An error occurred, please try again.")
                    return
                
                duration-=55
            
            logger.debug("Trying to download")
            text, confidence = downloadTranslation(chunks)
            logger.debug("Translated text: %s\nConfidence: %f"%(text, confidence))
            update.message.reply_text("Confidence: %f, Lang: %s\nText::\n%s"%(confidence, lang, text))
        
        except Exception as e:
            logger.debug("Other error: %s"%e)
            update.message.reply_text("An error occurred, please try again.")
     

def error(bot, update, error):
    logger.warn('Update "%s" cause error "%s"' %(update, error))

def startFromCLI():
    global AUTHTOKEN, LANGUAGES, AUTHKEY
    parser = argparse.ArgumentParser()
    parser.add_argument('auth', type=str, help="The Auth Token given by Telegram's @botfather")
    parser.add_argument('-l','--llevel', default='debug', choices=['debug','info','warn','none'], 
                        help='Logging level for the logger, default = debug')
    parser.add_argument('-lp','--langpack', default='languages.json', 
                        help='Location to the file that contains the JSON object listing languages.')
    parser.add_argument('-g','--googleKey', help="Auth Key for google account")
    logLevel = {'none':logging.NOTSET,'debug':logging.DEBUG,'info':logging.INFO,'warn':logging.WARNING}
    
    args = parser.parse_args()
    logger.setLevel(logLevel[args.llevel])
    
    with open(args.langpack, 'r') as f:
        LANGUAGES = load(f)
        logger.debug("Languages %s" % str(LANGUAGES.keys()))
    
    AUTHTOKEN = args.auth
    AUTHKEY = args.googleKey
    logger.debug(AUTHKEY)

def main():
    
    #updater = Updater(AUTHTOKEN, user_sig_handler=sigHandler)
    updater = Updater(AUTHTOKEN)
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