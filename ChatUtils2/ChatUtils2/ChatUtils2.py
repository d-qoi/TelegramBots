'''
Created on Jan 19, 2017

@author: d-qoi
'''

import logging
import argparse

from calendarEventHandler import calendarEventHandler
from extraUtils import checkValidCommand, checkTypeGroup

from pymongo import MongoClient
from telegram import TelegramError, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, Job, CommandHandler, CallbackQueryHandler
from pollEventHandler import pollEventHandler

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.DEBUG)
logger = logging.getLogger(__name__)

authToken = None
mongoURI = None
mClient = None
mDatabase = None

def callbackHandler(bot, update):
    query = update.callback_query
    from_user = query.from_user
    logger.debug("Answering Callback Query for %s (%s)" % (query.message.chat.title, query.message.chat.id))
    
    if query.data == "RegisterMe":
        #userDict = createUserDict(from_user)
        userDict = from_user.id
        mDatabase.groups.update({'_id':query.message.chat.id},
                            {'$addToSet':{'users':userDict}},
                            upsert=True)

def registerMe(bot, update):
    if not checkValidCommand(update.message.text, bot.username):
        return
    
    if not checkTypeGroup(update):
        update.message.reply_text("This only works in groups the bot is in. If you would like to add the bot to a group, do so and then send /registerme")
    
    #userDict = createUserDict(update.message.from_user)
    userDict = update.message.from_user.id
    logger.debug("New User: %s" % str(userDict))
    mDatabase.groups.update({'_id':update.message.chat.id},
                            {'$addToSet':{'users':userDict},
                             '$set':{'title':update.message.chat.title}},
                            upsert=True)
    
    logger.info("Register Me called for %s (%s)" % (update.message.chat.title, update.message.chat.id))
    keyboard = [[InlineKeyboardButton("Register Me!", 
                                      callback_data="RegisterMe")]]
    markup = InlineKeyboardMarkup(keyboard)
    reply_text = "If you would like to register with this bot for this group, send /registerme, or click the button below."
    try:
        bot.sendMessage(chat_id = update.message.chat.id,
                        text = reply_text,
                        reply_markup = markup)
    except TelegramError as TE:
        logger.error("Caught this from registerMe: %s" % str(TE))
    
def MOTD(bot, update):
    if not checkValidCommand(update.message.text, bot.username):
        return
    
    if not checkTypeGroup(update):
        return
    
    logger.debug('MOTD called for %s (%s)' % (update.message.chat.title, update.message.chat.id))
    if not checkValidCommand(update.message.text, bot.username):
        return
    result = mDatabase.groups.find({'_id':update.message.chat_id})
    if not result.count():
        return
    update.message.reply_text(result.next()['motd'], quote=False)

def setMOTD(bot, update):
    if not checkValidCommand(update.message.text, bot.username):
        return
    
    if not checkTypeGroup(update):
        return
    
    logger.debug('setMOTD called for %s (%s)' % (update.message.chat.title, update.message.chat.id))
    if not checkValidCommand(update.message.text, bot.username):
        return
    newMOTD = update.message.text[update.message.text.index(' ')+1:]
    logger.debug('setMOTD to: %s' % newMOTD)
    mDatabase.groups.update(
        {'_id':update.message.chat.id},
        {'motd':newMOTD},
        upsert=True)
    
def updateChatList(bot, job):
    logger.debug("-----------------------updatedChatList--------------------")
    logger.info("Updating the chat list")
    results = mDatabase.groups.find()
    for doc in results:
        try:
            chat = bot.getChat(chat_id = doc['_id'])
            logger.info("Chat %s (%s) responded." % (chat.title, chat.id))
            mDatabase.groups.find_one_and_update({'_id':doc['_id']},
                                           { '$set' : {'title':chat.title}})
        except TelegramError:
            logger.info("Removing %s (%s) from the database, it is not responding, re-add the bot if this is incorrect." % (doc['title'],doc['_id']))
            mDatabase.groups.remove({'_id':doc['_id']})

        except:
            logger.info("Other error when checking %s (%s), check networking" % (doc['title'],doc['_id']))


def main():
    global mClient, mDatabase
    
    mClient = MongoClient(mongoURI)
    mDatabase = mClient[mDatabase]
    
    
    try:
        serverInfo = mClient.server_info()
        logger.info("Mongo Connection Achieved")
        logger.debug("Connected to Mongo Server: %s" % serverInfo)
    except:
        logger.error("Could not connect to Mongo Server at %s" % mongoURI)
        raise
    
    updater = Updater(authToken)
    dp = updater.dispatcher
    
    
    dp.add_handler(CommandHandler('motd', MOTD))
    dp.add_handler(CommandHandler('setmotd', setMOTD))
    
    dp.add_handler(CommandHandler('registerme', registerMe))
    
    calendar = calendarEventHandler(mDatabase.groups, updater.job_queue)
    dp.add_handler(CommandHandler('listevents', calendar.getEventList))
    dp.add_handler(calendar.conversationHandler)
    
    polls = pollEventHandler(mDatabase.groups, mDatabase.pollData)
    dp.add_handler(polls.pollCreateHandler)
    
    dp.add_handler(CallbackQueryHandler(callbackHandler))
    
    updateAdmins = Job(updateChatList, 60*5)
    updater.job_queue.put(updateAdmins, next_t=0)
    
    updater.start_polling()
    updater.idle()
    
    

def startFromCLI():
    global mDatabase, mongoURI, authToken
    # Specifying a lot of arguments, Don't want to have to deal with config files, maybe I will later for other things
    parser = argparse.ArgumentParser()
    parser.add_argument('auth', type=str, 
                        help="The Auth Token given by Telegram's @botfather")
    parser.add_argument('-muri','--mongoURI', default='mongodb://localhost:27017', 
                        help="The MongoDB URI for connection and auth")
    parser.add_argument('-mDB', '--mongoDB', default="ChatUtil",
                        help="The database for MongoDB, default is ChatUtil")
    parser.add_argument('-l','--llevel', default='debug', choices=['debug','info','warn','none'], 
                        help='Logging level for the logger, default = debug')

    # This is not somehting that needs to be added, but it is useful for some things I think.
    logLevel = {'none':logging.NOTSET,'debug':logging.DEBUG,'info':logging.INFO,'warn':logging.WARNING} 
    args = parser.parse_args()


    logger.setLevel(logLevel[args.llevel])

    mDatabase = args.mongoDB
    mongoURI = args.mongoURI
    logger.info("MongoDB URI: %s" % (mongoURI))
    logger.info("MongoDB DB: %s" % (mDatabase))
    authToken = args.auth
    logger.debug("TelegramAuth: %s" % (authToken))

if __name__ == '__main__':
    startFromCLI()
    main()