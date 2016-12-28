#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ModismBot
# Created by Alexander Hirschfeld


from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from random import choice
from pymongo import MongoClient
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

def start(bot, update):
	logger.debug('User "%s (%s)" /start' % (update.message.from_user.username, update.message.from_user.id))
	if update.message.chat.type == 'private':
		update.message.reply_text('Hi, this bot is designed for use in Group and Supergroups, please add it to any that you wish.')


def help(bot, update):
	logger.debug('User "%s (%s)" /help' % (update.message.from_user.username, update.message.from_user.id))
	if update.message.chat.type == 'private':
		update.message.reply_text("Hi! This is the help command, I would recommend adding me to any group or super group and waiting for mods to speak before calling /modism")
	else:
		update.message.reply_text("Why would you call this command, what were you expecting?")


def receiveMessage(bot, update):
	if update.message.chat.type == 'group' or update.message.chat.type == 'supergroup' and not update.message.chat.all_members_are_admins:
		adminIDs = [chatmember.user.username for chatmember in update.message.chat.get_administrators()]
		if update.message.from_user.username in adminIDs:
			logger.debug("Admins of %s: %s" % (update.message.chat.title, str(adminIDs)))
			logger.debug("%s sent %s to %s" % (update.message.from_user.username, update.message.text, update.message.chat.title))
			mCollection.find_one_and_update({'_id':update.message.chat.id},{'$inc' : {'count':1}, '$push' : {"messages":update.message.message_id}}, upsert=True)



def modism(bot, update):
	findRes = mCollection.find({'_id':update.message.chat.id})
	if findRes.count() == 0:
		update.message.reply_text("The message list is empty, this bot was probably restarted.")
	elif update.message.chat.type == 'group' or update.message.chat.type == 'supergroup' and not update.message.chat.all_members_are_admins:
		data = findRes.next()['messages']
		bot.forwardMessage(chat_id = update.message.chat.id, from_chat_id = update.message.chat.id, message_id = choice(data))

def modismStats(bot, update):
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
