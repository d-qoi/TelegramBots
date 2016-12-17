#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ModismBot
# Created by Alexander Hirschfeld

import logging
import argparse

from pymongo import MongoClient
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Global variables
authToken = None
mongoURI = None
mClient = None
mDatabase = None

# Utility commands
def chechTypeGroup(update):
    return (update.message.chat.type == 'group' or update.message.chat.type == 'supergroup')

# returns -1 if they are not found in the users collection
def getUserID(username):
    logger.debug("Finding %s's user ID" % username)
    findRes = mDatabase.users.find({'username':username})
    if findRes.count() > 0:
        return findRes.next()['_id']
    return -1

def createChatDoc(bot, update):
    logger.debug("Creating Doc For :: Title: %s :: Username: %s :: ChatID: %s :: ChatType %s" % 
        (update.message.chat.title, update.message.from_user.username, update.message.chat.id, update.message.chat.type))
    # treating groups and super groups as the same entity, it makes things easier, and they basically are.
    if chechTypeGroup(update):
        findRes = mDatabase.groups.find({'_id':update.message.chat.id})
        if findRes.count() == 0:
            newGroup = dict()
            newGroup['_id'] = update.message.chat.id
            newGroup['title'] = update.message.chat.title
            newGroup['motd'] = "Can be changed with setMOTD"
            newGroup['custom_commands'] = [['message','This is a custom message, you can set a few of these']]
            mDatabase.groups.insert(newGroup) 
            logger.info("Group %s (%s) joined" % (update.message.chat.title, update.message.chat.id))
        elif findRes.count() > 1:
            # Find a good way to deal with this eventually
            logger.warn("There are two group entries for %s (%s). Please fix" % (update.message.chat.title, update.message.chat.id))
        else:
            logger.info("Group %s (%s) joined again." % (update.message.chat.title, update.message.chat.id))

def start(bot, update):
    pass

def help(bot, update):
    pass

# This should only be able to happen in groups, super groups, and chanels.
# I am assuming that this bot will only be added to groups and super groups.
def chatEventStatusUpdate(bot, update, chat_data):
    logger.debug("Status update for %s (%s)" % (update.message.chat.title, update.message.chat.id))
    chatID = update.message.chat.id
    chatTitle = update.message.chat.title

    # New chat member, need to store the ids or collect ids from the chat member that 
    if update.message.new_chat_member:
        # check to see if this is a new chat, or if this bot has been restarted
        if 'loaded' in chat_data and not update.message.new_chat_member.username[-3:] == 'bot':
            newUser = update.message.new_chat_member.id
            #mDatabase.groups.update_one({'_id':chatID}, {'$push':{'user_list':newUser}})
        else:
            chat_data['loaded'] = True
            createChatDoc(bot, update)
            inlineKeyboard = [[InlineKeyboardButton("Register With Bot", callback_data='register_me')]]
            reply_markup = InlineKeyboardMarkup(inlineKeyboard)
            replyText = """Thanks for adding me! This bot has some user interaction and cannot get the list of chat members in this chat without your help.
If you would like to interact with this bot, please register then send a message to this bot, to opt out at any time, just delete the chat with this bot and it will be unable to send you further messages."""
            bot.sendMessage(chat_id=chatID, text=replyText, reply_markup=reply_markup)

    # if update.message.chat.type == 'group':
        
    # elif update.message.chat.type = 'supergroup':
    #   pass
    # else:
    #   logger.info("There was a status update in a %s, ignoring." % update.message.chat.type)

# Message of the day
def MOTD(bot, update):
    logger.debug("Title: %s :: Username: %s :: ChatID: %s :: ChatType %s"% (update.message.chat.title, update.message.from_user.username, update.message.chat.id, update.message.chat.type))
    #reply_keyboard = [['test']]
    #markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False)

    #update.message.reply_text('test', reply_markup=markup)



def main():
    global mClient, mDatabase

    mClient = MongoClient(mongoURI)
    mDatabase = mClient[mDatabase]
    updater = Updater(authToken)
    dp = updater.dispatcher

    dp.add_handler(MessageHandler(Filters.status_update, chatEventStatusUpdate))
    dp.add_handler(CommandHandler('test', MOTD))

    logger.info("Setup complete, polling...")

    updater.start_polling()
    updater.idle()

def startFromCLI():
    global mDatabase, mongoURI, authToken
    # Specifying a lot of arguments, Don't want to have to deal with config files, maybe I will later for other things
    parser = argparse.ArgumentParser()
    parser.add_argument('auth', type=str, 
                        help="The Auth Token given by Telegram's @botfather")
    parser.add_argument('-mIP', '--mongoIP', default='localhost', type=str, 
                        help='The IPAddress of a MongoDB instance, default is localhost')
    parser.add_argument('-mPT', '--mongoPort', default=27017, type=int, 
                        help="The port of the MongoDB instance, default is 27017")
    parser.add_argument('-mUser', '--mongoUser', 
                        help='If there is a user/passwd for the MongoDB instance, specify the user here')
    parser.add_argument('-mPswd', '--mongoPswd', 
                        help='If there is a user/passwd for the MongoDB instance, specify the Password here')
    parser.add_argument('-mDB', '--mongoDB', default="ChatUtil",
                        help="The database for MongoDB, default is ChatUtil")
    parser.add_argument('-l','--llevel', default='debug', choices=['debug','info','warn','none'], 
                        help='Logging level for the logger, default = debug')

    # This is not somehting that needs to be added, but it is useful for some things I think.
    logLevel = {'none':logging.NOTSET,'debug':logging.DEBUG,'info':logging.INFO,'warn':logging.WARNING} 
    args = parser.parse_args()
    logger.setLevel(logLevel[args.llevel])

    if args.mongoUser and args.mongoPswd:
        mongoURI = "mongodb://%s:%s@%s:%d" % (args.mongoUser, args.mongoPswd, args.mongoIP, args.mongoPort, args.mongoAthDB)
    else:
        mongoURI = "mongodb://%s:%d" % (args.mongoIP, args.mongoPort)

    mDatabase = args.mongoDB
    logger.info("MongoDB URI: %s" % (mongoURI))
    logger.info("MongoDB DB: %s" % (mDatabase))
    authToken = args.auth
    logger.debug("TelegramAuth: %s" % (authToken))

if __name__ == '__main__':
    startFromCLI()
    main()

