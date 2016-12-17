#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ModismBot
# Created by Alexander Hirschfeld

import logging
import argparse

from pymongo import MongoClient
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
		level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Global variables
authToken = None
mongoURI = None
mClient = None
mDatabase = None

def start(bot, update):
	pass

def help(bot, update):
	pass

# This should only be able to happen in groups, super groups, and chanels.
# I am assuming that this bot will only be added to groups and super groups.
def chatEventStatusUpdate(bot, update)
	logger.debug("Status update for %s (%s)" % (update.message.chat.title, update.message.chat.id))
	chatID = update.message.chat.id
	chatTitle = update.message.chat.title

	logger.debug(str(update.message.new_chat_member))
	logger.debug(str(update.message.left_chat_member))
	logger.debug(str(update.message.new_chat_title))

	# if update.message.chat.type == 'group':
		
	# elif update.message.chat.type = 'supergroup':
	# 	pass
	# else:
	# 	logger.info("There was a status update in a %s, ignoring." % update.message.chat.type)

# Message of the day
def MOTD(bot, update):
	pass

def main():
	mClient = MongoClient(mongoURI)
	mDatabase = mClient[mDatabase]
	try:
		logger.info("Mongo info:\n%s" % mClient.server_info())
		mDatabase = mClient[mDatabase]

	except:
		logger.error("Mongo unreachable.")
		raise

	updater = Updater(authToken)
	dp = updater.dispatcher

	dp.add_handler(MessageHandler(Filters.status_update, chatEventStatusUpdate))

	logger.info("Setup complete, polling...")

	updater.start_polling()
	updater.idle()

def startFromCLI():
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

