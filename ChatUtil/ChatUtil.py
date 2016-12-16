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

authToken = None
mongoURI = None
mClient = None




def main():
	mClient = MongoClient(mongoURI)
	try:
		logger.info("Database info:\n%s" % mClient.server_info())
	except:
		logger.error("Database unreachable.")
		raise

	updater = Updater(authToken)
	dp = updater.dispatcher

	dp.

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
	# I don't know if this is the right use of this functionality, it is untested in this code
	parser.add_argument('-mAthDB', '--mongoAthDB', default="",
						help="The authentication database for MongoDB, default is none, only used if user and password are specified, this may be wrong")
	parser.add_argument('-l','--llevel', default='debug', choices=['debug','info','warn','none'], 
						help='Logging level for the logger, default = debug')

	# This is not somehting that needs to be added, but it is useful for some things I think.
	logLevel = {'none':logging.NOTSET,'debug':logging.DEBUG,'info':logging.INFO,'warn':logging.WARNING} 
	args = parser.parse_args()
	logger.setLevel(logLevel[args.llevel])

	if args.mongoUser and args.mongoPswd:
		mongoURI = "mongodb://%s:%s@%s:%d/%s" % (args.mongoUser, args.mongoPswd, args.mongoIP, args.mongoPort, args.mongoAthDB)
	else:
		mongoURI = "mongodb://%s:%d" % (args.mongoIP, args.mongoPort)

	logger.info("MongoDB URI: %s" % (mongoURI))

	authToken = args.auth
	logger.debug("TelegramAuth: %s" % (authToken))

if __name__ == '__main__':
	startFromCLI()
	main()

