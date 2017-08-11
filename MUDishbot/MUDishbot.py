'''
Created on Mar 13, 2017

@author: hirschag
'''
import argparse
import logging
import re

from pymongo import MongoClient

#from telegram import 
from telegram.ext import Updater, CommandHandler, ConversationHandler, Filters, MessageHandler, RegexHandler
from telegram.ext.messagehandler import MessageHandler
from gi.overrides.Gdk import name

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO)
logger = logging.getLogger(__name__)

authToken = None
mongoURI = None
mClient = None
mDatabase = None

STRUCTNAME, STRUCTDESC, STRUCTDOOR = range(100,103)

def help(bot, update):
    logger.debug("User %s called /help"%(update.message.from_user.first_name + ' ' + update.message.from_user.last_name))
    text = "All add commands take a name and a description, separated by a newline.\n"
    text += "All description are separated by periods, add as many sentences as needed.\n"
    update.message.reply_text(text)
    

def start(bot, update):
    pass

def undo(bot, update):
    pass

def redoState(bot, update, user_data):
    text = "It appears you have sent something other than text, please send the %s."%user_data['currstate'][0]
    update.message.reply_text(text)
    return user_data['currstate'][1]

def roomAddObjDisc(bot, update):
    pass

def roomRemObjDisc(bot, update):
    pass

def roomAddTempDisc(bot, update):
    pass

def roomRemTempDisc(bot, update):
    pass

def doorLock(bot, update):
    pass

def doorUnlock(bot, update):
    pass

def doorKnock(bot, update):
    pass

## Character Description
def meAbout(bot, update, user_data):
    pass

def meTextResp(bot, update, user_data):
    pass

def mePhotoResp(bot, update, user_data):
    pass

def meChoose(bot, update, user_data):
    pass

def meAboutCancel(bot, update, user_data):
    pass

## Inventory
def meInv(bot, update):
    pass

def meAddInv(bot, update):
    pass

def meRemInv(bot, update):
    pass

## action Commands

def go(bot, update):
    pass


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
    
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    
    charCreationHandler = ConversationHandler(
        entry_points=[CommandHandler('meAbout',meAbout, pass_user_data=True)],
        states={
                TEXTRESP:[MessageHandler(Filters.text, meTextResp, pass_user_data=True),
                          MessageHandler(Filters.all, redoState, pass_user_data=True)],
                PHOTORESP:[MessageHandler(Filters.photo or Filters.sticker, mePhotoResp, pass_user_data=True),
                           MessageHandler(Filters.all, redoState, pass_user_data=True)],
                CHOOSE:[RegexHandler("^(Name, Discription, Photo, Bio, Cancel)$", meChoose, pass_user_data=True)]
            },  
        fallbacks=[CommandHandler('cancel',meAboutCancel, pass_user_data=True)]                                                           
        )
    structCreationHandler = ConversationHandler(
        entry_points=[CommandHandler('newStruct', editStructStart, pass_user_data=True)],
        states={STRUCTNAME:[MessageHandler(Filters.text, editStructSetName, pass_user_data=True),
                      MessageHandler(Filters.all, redoState, pass_user_data=True)]
                STRUCTDESC:[MessageHandler(Filters.text, editStructSetDesc, pass_user_data=True),
                            MessageHandler(Filters.all, redoState, pass_user_data=True)],
                STRUCTDOOR:[MessageHandler(Filters.text, editStructSetDoor, pass_user_data=True),
                            MessageHandler(Filters.all, redoState, pass_user_data=True)]},
        fallbacks=[CommandHandler("cancel", cancel)])
    roomCreationHandler = ConversationHandler(
        entry_points=[ConversationHandler("editRoom", editRoomStart)],
        states={},
        fallbacks=[CommandHandler("cancel", cancel)])
    
    dp.add_handler(CommandHandler("roomAddObjDisc", roomAddObjDisc, allow_edited=True))
    dp.add_handler(CommandHandler("roomRemObjDisc", roomRemObjDisc))
    
    dp.add_handler(CommandHandler("roomAddTempDisc", roomAddTempDisc, allow_edited=True))
    dp.add_handler(CommandHandler("roomRemTempDisc", roomRemTempDisc))
    
    dp.add_handler(CommandHandler("doorLock",doorLock))
    dp.add_handler(CommandHandler("doorUnlock", doorUnlock))
    dp.add_handler(CommandHandler("doorKnock", doorKnock))
    
    updater.start_polling()
    updater.idle()
    
    mClient.close()
    

def startFromCLI():
    global mDatabase, mongoURI, authToken
    # Specifying a lot of arguments, Don't want to have to deal with config files, maybe I will later for other things
    parser = argparse.ArgumentParser()
    parser.add_argument('auth', type=str, 
                        help="The Auth Token given by Telegram's @botfather")
    parser.add_argument('-muri','--mongoURI', default='mongodb://localhost:27017', 
                        help="The MongoDB URI for connection and auth")
    parser.add_argument('-mDB', '--mongoDB', default="MUDish",
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