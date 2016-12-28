#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ModismBot
# Created by Alexander Hirschfeld

import logging
import argparse

from pymongo import MongoClient
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, RegexHandler


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Global variables
authToken = None
mongoURI = None
mClient = None
mDatabase = None

# For the state machine of creating events, because conversation handlers are state machines
EVENTSELECT, EVENTTYPING, EVENTCREATE = range(100,103) 

# Utility commands
def checkTypeGroup(update):
    return (update.message.chat.type == 'group' or update.message.chat.type == 'supergroup')

def checkTypePrivate(update):
    return update.message.chat.type == 'private'

# returns -1 if they are not found in the users collection
def getUserID(username):
    logger.debug("Finding %s's user ID" % username)
    findRes = mDatabase.users.find({'username':username})
    if findRes.count() > 0:
        return findRes.next()['_id']
    return -1

def createChatDoc(bot, update):
    logger.info("Creating Doc For :: Title: %s :: Username: %s :: ChatID: %s :: ChatType %s" % 
        (update.message.chat.title, update.message.from_user.username, update.message.chat.id, update.message.chat.type))
    # treating groups and super groups as the same entity, it makes things easier, and they basically are.
    if checkTypeGroup(update):
        findRes = mDatabase.groups.find({'_id':update.message.chat.id})
        if findRes.count() == 0:
            newGroup = dict()
            newGroup['_id'] = update.message.chat.id
            newGroup['title'] = update.message.chat.title
            newGroup['motd'] = 0
            newGroup['custom_commands'] = [['example','This is a custom message, you can set a few of these']]
            newGroup['activePolls'] = list()
            newGroup['food']
            mDatabase.groups.insert(newGroup) 
            logger.info("Group %s (%s) joined" % (update.message.chat.title, update.message.chat.id))
        elif findRes.count() > 1:
            # Find a good way to deal with this eventually
            logger.warn("There are two group entries for %s (%s). Please fix" % (update.message.chat.title, update.message.chat.id))
        else:
            logger.info("Group %s (%s) joined again." % (update.message.chat.title, update.message.chat.id))
    elif checkTypePrivate(update):
        if mDatabase.users.find({'_id':update.message.from_user.id}).count():
            update.message.reply_text("Welcome to the bot, how may I help?")


def createEventDoc(forChatId, user_data):
    logger.info("Creating Event for %s (%s)" % (update.message.chat.title, update.message.chat.id))
    if mDatabase.groups.find({'_id':update.message.chat.id}).count():
        newEvent = dict()
        newEvent['id'] = forChatId
        newEvent['Name'] = user_data['Name']
        newEvent['Description'] = user_data['Description']
        newEvent['Time'] = user_data['Time']
        newEvent['Place'] = user_data['Place']
        newEvent['Date'] = newEvent['Date']
        mDatabase.events.insert(newEvent)
        logger.debug("Created Event: %s" % (str(newEvent)))

def addUserToGroup(userID, groupID, groupTitle):
    logger.info("Adding user to ")

def start(bot, update):
    pass

def help(bot, update):
    pass

def eventStartEditing(bot, update, user_data):
    if checkTypePrivate(update):
        logger.info("%s (%s) is creating an event." % (update.message.from_user.username, update.message.from_user.id))
        for key in ['Name','Time','Date','Description','Place']:
            user_data[key] = None
        reply_keyboard = [['Name', 'Time', 'Date'],
                          ['Chat','Place'],
                          ['Description']]
        if all (key in user_data for key in ['Name','Time','Date','Description','Place','Chat']):
            reply_keyboard.append(['Cancel','Done'])
        else:
            reply_keyboard.append(['Cancel'])
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        reply_text = "Please select which you would like to edit, once you've entered something for all of these, you will be able to create the event."
        update.message.reply_text(reply_text, reply_markup=markup)
        return EVENTSELECT
    else:
        update.message.reply_text("Please message this bot directly to create an event.")
        return ConversationHandler.END


def eventSelectEditing(bot, update, user_data):
    user_data[user_data['editing_choice']] = update.message.text
    reply_keyboard = [['Name', 'Time', 'Date'],
                      ['Description','Place']]
    if all (key in user_data for key in ['Name','Time','Date','Description','Place']):
        reply_keyboard.append(['Cancel','Done'])
    else:
        reply_keyboard.append(['Cancel'])
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    reply_text = "Please select which you would like to edit, once you've entered something for all of these, you will be able to create the event."
    update.message.reply_text(reply_text, reply_markup=markup)
    return EVENTSELECT

def eventPromptTyping(bot, update, user_data):
    userChoice = update.message.text
    user_data['editing_choice'] = userChoice
    if userChoice == 'Done':


    elif userChoice == 'Cancel':

    else:
        reply_text = "Please send me the %s of the event." % userChoice.lower()
        update.message.reply_text(reply_text)

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


def callbackHandler(bot, update, chat_data, user_data):
    query = update.callback_querry
    querry_data = query.data

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
    dp.add_handler(CallbackQueryHandler(callbackHandler, pass_chat_data = True, pass_user_data = True))

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

