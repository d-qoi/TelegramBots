#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Speach to Text Bot
# Created by Alexander Hirschfeld

import argparse
import logging
from json import load
from os import getcwd
from pymongo import MongoClient
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, Filters, MessageHandler, CallbackQueryHandler
from telegram.ext.dispatcher import run_async

from requesthistory import requesthistory


AUTHTOKEN = None
LANGUAGES = None
MCLIENT = None
MDB = None

ALERT_THRESH = None

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
        chat_data['lang'] = result.get('lang', 'en-US')

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
    reply_text += "Developed and maintained by @.\n"
    reply_text += "If you wish to help support development of this bot, consider becoming a patron at: https://www.patreon.com/.\n\n"
    reply_text += "Please share this bot with everyone!\n"
    reply_text += "And if you want to know how this bot is doing, try calling /getStats"
    update.message.reply_text(reply_text)
    
@run_async
def support(bot, update, chat_data):
    TRACKING.total.post()
    logger.info("Support called")
    if 'it' in chat_data['lang']:
        reply_text = """
Ciao!

Sono triste dire che è diventato troppo costoso per continuare a ospitare @listenformebot. E 'offline per ora. Sarà indietro quando posso trovare un discorso a prezzi ragionevoli presso il servizio di testo o se posso ottenere aiuto a ospitare questo bot.

Non mi aspettavo che il bot cresca così, ma sono contento che sia diventato popolare.

Se vuoi supportarmi per mantenere vivo questo bot, pensa a parlare con @ o donando per mantenere questo bot in esecuzione attraverso il mio sito web (/supporto)

Grazie,

"""

    elif 'es' in chat_data['lang']:
        reply_text = """
¡Hola!

Estoy triste de decir que se ha vuelto demasiado caro para seguir corriendo @ listenformebot. El bot está ahora sin conexión. Volveré cuando pueda encontrar un servicio de transcripción a un precio razonable o si puedo obtener ayuda para alojar este bot.

No esperaba que el bot creciera así, pero me alegro de que fuera popular.

Si quieres apoyarme para mantener este bot vivo, piensa en hablar con @ o donar para mantener este bot ejecutándose en mi sitio web (/support)

Gracias,
"""

    elif 'ru' in chat_data['lang']:
        reply_text = """
Здравствуйте!

Мне грустно говорить, что было слишком дорого продолжать хостинг @listenformebot. Теперь бот отключен. Этот бот вернется, когда я найду услугу транскрипции по разумной цене, или я смогу получить помощь в размещении этого бота.

Я не ожидал, что бот будет расти таким образом, но я рад, что он был популярен.

Если вы хотите поддержать меня, чтобы этот бот был жив, подумайте о том, как поговорить с @ или пожертвовать этого бота на мой сайт (/support)

Спасибо,
"""
    elif 'pt' in chat_data['lang']:
            reply_text = """
Olá!

Estou triste em dizer que tornou-se muito caro para mim continuar hospedando @listenformebot sozinho. O bot está agora offline. Será novamente on-line quando eu puder encontrar um serviço de transcrição com preços razoáveis, ou se você conseguir obter ajuda para hospedar este bot.

Não esperava que ele crescesse, mas estou feliz por ter se tornado popular.

Se você gostaria de me apoiar para manter este bot online, considere falar com @, ou doar para este bot no meu site (/ support)

Obrigado,
"""

    else:
        reply_text = """
Hello!

I am sad to say that it has become too expensive for me to continue hosting @listenformebot alone. It is offline for now. It will be back when I can find a reasonably priced speech to text service, or if I can get help hosting this bot.

I was not expecting it to grow as it did, but I am glad it became popular.

If you would like to support me to keep this bot online, consider talking to @, or donating to keep this bot running through my website (/support) 

"""

    suplist = [[InlineKeyboardButton('Website', 'https://.github.io/TelegramBots/'),
               InlineKeyboardButton('Patreon', 'https://www.patreon.com/')]]
    update.message.reply_text(reply_text, reply_markup = InlineKeyboardMarkup(suplist), quote=False)
    
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
    if not querydata:
        return
    
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
                              
            
@run_async                
def receiveMessage(bot, update, chat_data):
    logger.info('Message Received')
    TRACKING.voice.post()
    if not 'lang' in chat_data:
        getChatFile(chat_data, update.message.chat.id)
        if not 'lang' in chat_data:
            update.message.reply_text("No language set through /chooselang, defaulting to en-US.", quote=False)
            chat_data['lang'] = 'en-US'
    
    update.message.reply_text("@listenformebot has been disabled. If you would like to help keep it alive, send /support.")    
    

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
    
    result = MDB.groups.find()
    languages = dict()
    for chat in result:
        if chat['lang'] in languages:
            languages[chat['lang']] += 1
        else:
            languages[chat['lang']] = 1
            
    reply_text += "%d languages served\n" % len(languages)
    langtups = [(v, k) for k,v in languages.items()]
    langtups.sort(reverse=True)
    for v, k in langtups:
        reply_text += "%s :: %s user\n"%(k, str(v))
        
    
        
    update.message.reply_text(reply_text)

def error(bot, update, error):
    logger.warn('Update "%s" cause error "%s"' %(update, error))

def startFromCLI():
    global AUTHTOKEN, LANGUAGES, MDB, MCLIENT, TRACKING, ALERT_THRESH
    parser = argparse.ArgumentParser()
    parser.add_argument('auth', type=str, help="The Auth Token given by Telegram's @botfather")
    parser.add_argument('-l','--llevel', default='debug', choices=['debug','info','warn','none'], 
                        help='Logging level for the logger, default = debug')
    parser.add_argument('-lp','--langpack', default='languages.json', 
                        help='Location to the file that contains the JSON object listing languages.')
    parser.add_argument('-muri','--MongoURI', default='mongodb://localhost:27017', help="The MongoDB URI for connection and auth")
    parser.add_argument('-mdb','--MongoDB', default='speech', help="The MongoDB Database that this will use")
    parser.add_argument('-thr', '--thresh', default=100, type=int, help='Threshold in minutes for the alert.')
    
    logLevel = {'none':logging.NOTSET,'debug':logging.DEBUG,'info':logging.INFO,'warn':logging.WARNING}
    
    args = parser.parse_args()
    logger.setLevel(logLevel[args.llevel])
    
    with open(args.langpack, 'r') as f:
        LANGUAGES = load(f)
        logger.debug("Languages %s" % str(LANGUAGES.keys()))
    
    AUTHTOKEN = args.auth
    MCLIENT = MongoClient(args.MongoURI)
    MDB = MCLIENT[args.MongoDB]
    
    TRACKING = requesthistory('total', 'voice')
    
    ALERT_THRESH = args.thresh

def main():
    
    updater = Updater(AUTHTOKEN, workers=10)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('help', help))
    dp.add_handler(CommandHandler('info', info))
    dp.add_handler(CommandHandler('support', support, pass_chat_data=True))
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
