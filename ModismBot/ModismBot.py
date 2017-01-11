#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ModismBot
# Created by Alexander Hirschfeld


from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import TelegramError
from random import choice
from pymongo import MongoClient, ReturnDocument
import logging
import argparse

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO) # To make sure that it is just pushing modism debug into the log
logger = logging.getLogger(__name__) 

# All of this should be moved, but lazy coder is lazy
parser = argparse.ArgumentParser()
parser.add_argument('auth', type=str, help="The Auth Token given by Telegram's @botfather")
parser.add_argument('-l','--llevel', default='debug', choices=['debug','info','warn','none'], help='Logging level for the logger, default = debug')
logLevel = {'none':logging.NOTSET,'debug':logging.DEBUG,'info':logging.INFO,'warn':logging.WARNING}
parser.add_argument('-muri','--MongoURI', default='mongodb://localhost:27017', help="The MongoDB URI for connectiong and auth")
parser.add_argument('-mdb','--MongoDB', default='modism', help="The MongoDB Database that this will use")
args = parser.parse_args()

# Being ULTRA lazy
mClient = MongoClient(args.MongoURI)
mDatabase = mClient[args.MongoDB]
mCollection = mDatabase.groups

# Checks to see if a command is a valid command for the bot, aka @botname exists or doesn't
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
    logger.debug('User "%s (%s)" /start' % (update.message.from_user.username, update.message.from_user.id))
    if update.message.chat.type == 'private':
        update.message.reply_text('Hi, this bot is designed for use in Group and Supergroups, please add it to any that you wish. /help for more information.')


def help(bot, update):
    logger.debug('User "%s (%s)" /help' % (update.message.from_user.username, update.message.from_user.id))
    if update.message.chat.type == 'private':
        update.message.reply_text("Hi! This is the help command, I would recommend adding me to any group or super group and waiting for admins to speak before calling /modism. \nThis bot will forward one of their previous messages in the chat back to the chat.\nTalk to @YTKileroy if you need more help.")
    else:
        update.message.reply_text("Why would you call this command, what were you expecting?")


def receiveMessage(bot, update):
    if update.message.chat.type == 'group' or update.message.chat.type == 'supergroup' and not update.message.chat.all_members_are_admins:
        admins = update.message.chat.get_administrators()
        adminUsernames = [chatmember.user.username for chatmember in admins]
        adminIDs = [chatmember.user.id for chatmember in admins]
        if update.message.from_user.id in adminIDs:
            logger.debug("Admins of %s: %s" % (update.message.chat.title, str(adminUsernames)))
            #logger.debug("All Members Are Admins: %i" % (update.message.chat.all_members_are_admins))
            logger.debug("%s in %s sent: %s" % (update.message.from_user.username, update.message.chat.title, update.message.text))
            mCollection.update({'_id':update.message.chat.id},
                                {'$inc' : {'count':1}, 
                                 '$push' : 
                                    {"messages":
                                        {"$each":[update.message.message_id],
                                        "$slice":-4000}}}, 
                                upsert=True)
            

def modism(bot, update):
    logger.debug("User %s (%s) in chat %s (%s) called modism." % (update.message.from_user.username, update.message.from_user.id, update.message.chat.title, update.message.chat.id))
    
    if not checkValidCommand(update.message.text, bot.username):
        return

    findRes = mCollection.find({'_id':update.message.chat.id})
    if findRes.count() == 0:
        update.message.reply_text("The message list is empty, this bot was probably restarted.")
    elif update.message.chat.type == 'group' or update.message.chat.type == 'supergroup' and not update.message.chat.all_members_are_admins:
        data = findRes.next()['messages']
        #mID = 
        try:
            bot.forwardMessage(chat_id = update.message.chat.id, from_chat_id = update.message.chat.id, message_id = choice(data))
        except TelegramError:
            modism(bot, update)

    else:
        update.message.reply_text("This bot doesn't work if all members are admins.")

def modismStats(bot, update):

    if not checkValidCommand(update.message.text, bot.username):
        return

    logger.debug("User %s (%s) in chat %s (%s) called modismStats." % (update.message.from_user.username, update.message.from_user.id, update.message.chat.title, update.message.chat.id))
    findRes = mCollection.find({'_id':update.message.chat.id})
    if findRes.count() > 0:
        update.message.reply_text("Messages stored: %s" % str(findRes.next()['count']))
    else:
        update.message.reply_text("The message list is empty, this bot was probably restarted.")


def error(bot, update, error):
    logger.warn('Update "%s" cause error "%s"' %(update, error))


def main():
    updater = Updater(args.auth)
    logger.setLevel(logLevel[args.llevel])

    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('help', help))
    dp.add_handler(CommandHandler('modism', modism))
    dp.add_handler(CommandHandler('modismstats', modismStats))

    dp.add_handler(MessageHandler(Filters.text, receiveMessage))
    dp.add_error_handler(error)

    updater.start_polling()

    updater.idle()

if __name__ == '__main__':
    main()
