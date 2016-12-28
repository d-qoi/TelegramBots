#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ModismBot
# Created by Alexander Hirschfeld


from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from random import choice
import logging
import argparse

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
	level=logging.INFO)
logger = logging.getLogger(__name__)


parser = argparse.ArgumentParser()
parser.add_argument('auth', type=str, help="The Auth Token given by Telegram's @botfather")
parser.add_argument('-l','--llevel', default='debug', choices=['debug','info','warn','none'], help='Logging level for the logger, default = debug')
logLevel = {'none':logging.NOTSET,'debug':logging.DEBUG,'info':logging.INFO,'warn':logging.WARNING}
parser.add_argument('-muri','--MongoURI', default='mongodb://localhost:27017', help="The MongoDB URI for connectiong and auth")
parser.add_argument('-mdb','--MongoDB', default='STT', help="The MongoDB Database that this will use")
args = parser.parse_args()


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


def addSelfToGroup(bot, update, chat_data):
	if update.message.new_chat_member.username == bot.username and (update.message.chat.type == 'group' or update.message.chat.type == 'supergroup'):
		logger.info("Bot was added to %s (%s)" % (update.message.chat.title, update.message.chat.id))
		chat_data['mod_messages'] = list()


def receiveMessage(bot, update, chat_data):
	if update.message.chat.type == 'group' or update.message.chat.type == 'supergroup' and not update.message.chat.all_members_are_admins:
		adminIDs = [chatmember.user.username for chatmember in update.message.chat.get_administrators()]
		if update.message.from_user.username in adminIDs:
			logger.debug("Admins of %s: %s" % (update.message.chat.title, str(adminIDs)))
			logger.debug("%s sent %s to %s" % (update.message.from_user.username, update.message.text, update.message.chat.title))
			if not 'mod_chat' in chat_data:
				chat_data['mod_chat'] = list()
			chat_data['mod_chat'].append(update.message.message_id)
			logger.debug("Number of messages stored: %s" % (str(len(chat_data['mod_chat']))))


def modism(bot, update, chat_data):
	if not 'mod_chat' in chat_data or len(chat_data['mod_chat']) == 0:
		chat_data['mod_chat'] = list()
		update.message.reply_text("The message list is empty, this bot was probably restarted.")
	elif update.message.chat.type == 'group' or update.message.chat.type == 'supergroup' and not update.message.chat.all_members_are_admins and chat_data['mod_chat']:
		bot.forwardMessage(chat_id = update.message.chat.id, from_chat_id = update.message.chat.id, message_id = choice(chat_data['mod_chat']))

def modismStats(bot, update, chat_data):
	if 'mod_chat' in chat_data:
		update.message.reply_text("Messages stored: %s" % str(len(chat_data['mod_chat'])))
	else:
		chat_data['mod_chat'] = list()
		update.message.reply_text("The message list is empty, this bot was probably restarted.")


def error(bot, update, error):
	logger.warn('Update "%s" cause error "%s"' %(update, error))


def main():
	updater = Updater(args.auth)
	logger.setLevel(logLevel[args.llevel])

	dp = updater.dispatcher

	dp.add_handler(CommandHandler('start', start))
	dp.add_handler(CommandHandler('help', help))
	dp.add_handler(CommandHandler('modism', modism, pass_chat_data=True))
	dp.add_handler(CommandHandler('modismstats', modismStats, pass_chat_data=True))

	dp.add_handler(MessageHandler(Filters.text, receiveMessage, pass_chat_data=True))
	dp.add_handler(MessageHandler(Filters.status_update, addSelfToGroup, pass_chat_data=True))
	dp.add_error_handler(error)

	updater.start_polling()

	updater.idle()

if __name__ == '__main__':
	main()
