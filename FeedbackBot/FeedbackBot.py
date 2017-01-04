#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# FeedbackBot
# Created by Alexander Hirschfeld

import argparse
import logging
from pymongo import MongoClient
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, TelegramError
from telegram.ext import Updater, CommandHandler, Filters, MessageHandler, CallbackQueryHandler, Job

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Globals
AUTHTOKEN = None
MCLIENT = None
MDB = None

# Utility functions
# Returns the list of chats that a user is admin of.
def getChatsAdmining(id, username):
    results = MDB.groups.find({'admins': {'$eq':id}})
    listOfChats = list()
    logger.debug("%s is in %i groups as admin" % (username, results.count()))
    for doc in results:
        listOfChats.append({'title':doc['title'],'id':doc['_id']})
    return listOfChats


# Return a list of chat titles
def getChatList():
    return [[doc['title'], doc['_id']] for doc in MDB.groups.find()]




# User functions
def start(bot, update, user_data):
    logger.debug("User %s (%s) called start." % (update.message.from_user.username, update.message.from_user.id))
    if update.message.chat.type == "private":
        admining = getChatsAdmining(update.message.from_user.id, update.message.from_user.username)
        #logger.debug("Admin of %s" % user_data['admin_of'])
        if admining:
            reply_text = "Hello @%s! You are an Admin of a few chats! Would you like to give feedback or reply to feedback!" % update.message.from_user.username
            mongoData = {'0':{'chosen':None},
                         '1':{'chosen':None},
                         'reason':'admin_initial'}
            keyboard = [[InlineKeyboardButton('Give Feedback', 
                                             callback_data='0')],
                         [InlineKeyboardButton('Reply to Feedback', 
                                             callback_data='1')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            MDB.callback_data.update({ '_id' : update.message.from_user.id }, mongoData, upsert=True)
            update.message.reply_text(reply_text, reply_markup=reply_markup)
            user_data['active'] = False
        else: 
            reply_text="Hello %s, anything you send to this bot will alert an admin, they should reply quickly.\n"
            reply_text=reply_text + "We would recommend starting with what you would like to provide feedback for."
            update.message.reply_text(reply_text)
            mongoData = dict()
            mongoData['username'] = update.message.from_user.username
            mongoData['name'] = update.message.from_user.first_name + " " + update.message.from_user.last_name
            mongoData['id'] = update.message.from_user.id
            mongoData['log'] = []
            MDB.active.update({'_id':update.message.chat.id},mongoData,upsert=True)
            user_data['active'] = True
        
            


def help(bot, update, user_data, chat_data):
    logger.debug("User %s (%s) called help." % (update.message.from_user.username, update.message.from_user.id))

def addGroup(bot, update, chat_data):
    logger.debug('addGroup')

def statusReceived(bot, update):
    logger.debug("Message Received")
    if update.message.new_chat_member and update.message.new_chat_member.username == bot.username:
        logger.debug("Added To Chat")
        newGroup = dict()
        chat = update.message.chat
        #newGroup['_id'] = chat.id
        newGroup['title'] = chat.title
        newGroup['admins'] = [chatmember.user.id for chatmember in chat.get_administrators()]
        logger.debug("newGroup: %s" % newGroup)

        MDB.groups.update({'_id':chat.id}, newGroup, upsert=True)
        logger.info("Added %s to the group list" % update.message.chat.title)

    elif update.message.left_chat_member and update.message.left_chat_member.username == bot.username:
        MDB.groups.remove({'_id':update.message.chat.id})
        logger.debug("Removing entry for %s" % (update.message.chat.title))

def forwardToAll(bot, list_of_chats, from_chat_id, message_id):
    for chat in list_of_chats:
        bot.forward_message(chat_id=chat,
                            from_chat_id=from_chat_id,
                            message_id=message_id)

def sendToAll(bot, message, list_of_chats, user_chat_id):
    timeout = 10 #Timeout in seconds, though this might be a good idea, don't think this bot will be hitting this any time soon
    if Filters.text(message):
        for chat in list_of_chats:
            bot.send_message(chat_id=chat,
                             text=message.text,
                             timeout=timeout)
        newMessage = bot.send_message(chat_id=user_chat_id,
                         text=message.text,
                         timeout=timeout)

    elif Filters.audio(message):
        audio = message.audio.file_id
        for chat in list_of_chats:
            bot.send_audio(chat_id=chat,
                           audio=audio,
                           timeout=timeout)
        newMessage = bot.send_audio(chat_id=user_chat_id,
                       audio=audio,
                       timeout=timeout)

    elif Filters.document(message):
        document = message.document.file_id
        for chat in list_of_chats:
            bot.send_document(chat_id=chat,
                              document=document,
                              timeout=timeout)
        newMessage = bot.send_document(chat_id=user_chat_id,
                                       document=document,
                                       timeout=timeout)

    elif Filters.photo(message):
        photo = message.photo[0].file_id
        caption = ""
        if message.caption:
            caption = message.caption
        for chat in list_of_chats:
            bot.send_photo(chat_id=chat,
                           photo=photo,
                           caption=caption,
                           timeout=timeout)
        newMessage = bot.send_photo(chat_id=user_chat_id,
                                    photo=photo,
                                    caption=caption,
                                    timeout=timeout)

    elif Filters.sticker(message):
        sticker = message.sticker.file_id
        for chat in list_of_chats:
            bot.send_sticker(chat_id=chat,
                             sticker=sticker,
                             timeout=timeout)
        newMessage = bot.send_sticker(chat_id=user_chat_id,
                                      sticker=sticker,
                                      timeout=timeout)
    elif Filters.voice(message):
        voice = message.voice.file_id
        for chat in list_of_chats:
            bot.send_voice(chat_id=chat,
                           voice=voice,
                           timeout=timeout)
        newMessage = bot.send_voice(chat_id=user_chat_id,
                                    voice=voice,
                                    timeout=timeout)

    elif Filters.video(message):
        video = message.video.file_id
        for chat in list_of_chats:
            bot.send_video(chat_id=chat,
                           video=video,
                           timeout=timeout)
        newMessage = bot.send_video(chat_id=user_chat_id,
                                    video=video,
                                    timeout=timeout)

    elif Filters.contact(message):
        phone_number = message.contact.phone_number
        first_name = message.contact.first_name
        last_name = message.contact.last_name
        for chat in list_of_chats:
            bot.send_contact(chat_id=chat,
                             phone_number=phone_number,
                             first_name=first_name,
                             last_name=last_name,
                             timeout=timeout)
        newMessage = bot.send_contact(chat_id=user_chat_id,
                                      phone_number=phone_number,
                                      first_name=first_name,
                                      last_name=last_name,
                                      timeout=timeout)

    elif Filters.location(message):
        lat = message.location.latitude
        lon = message.location.longitude
        for chat in list_of_chats:
            bot.send_location(chat_id=chat,
                             longitude=lon,
                             latitude=lat,
                             timeout=timeout)
        newMessage = bot.send_location(chat_id=user_chat_id,
                                      longitude=lon,
                                      latitude=lat,
                                      timeout=timeout)

    elif Filters.forwarded(message):
        message_id = message.message_id
        from_chat = message.forward_from_chat.id
        for chat in list_of_chats:
            bot.forward_message(chat_id=chat,
                                from_chat_id=from_chat,
                                message_id=message_id,
                                timeout=timeout)
        newMessage = bot.forward_message(chat_id=user_chat_id,
                                from_chat_id=from_chat,
                                message_id=message_id,
                                timeout=timeout)
    else:
        pass

    MDB.active.update({'_id':user_chat_id},
                      {'$push':{'log':newMessage.message_id}})

def messageReceived(bot, update, user_data):

    if update.message.chat.type == 'private':
        # In case there was a reset of this server
        if not user_data['active'] and not user_data['reply_to']:
            user_data['active']=True
            if getChatsAdmining(update.message.from_user.id, update.message.from_user.username):
                reply_text = "There was a server reset for this bot. You were previously replying to:\n"
                results = MDB.active.find({'forward_to' : {'$elemMatch':update.message.chat.id}})
                #repairing things
                if results.count() > 1:
                    MDB.active.update_many(
                        {'forward_to' : {'$elemMatch':update.message.chat.id}},
                        {'$pull':{'forward_to':update.message.chat.id}})
                    reply_text += "None\n Type /cancel to restart or if you would like to give feedback, start typing."
                elif results.count() == 0:
                    reply_text += "None\n Type /cancel to restart or if you would like to give feedback, start typing."
                elif results.count == 1:
                    results = results.next()
                    reply_to = results['_id']
                    reply_to_name = results['name']
                    reply_text += reply_to_name
                    reply_text += '\nYou should have been forwarded any messages they sent, restart with /cancel if you would like to select another user.'
                    user_data['active']=False
                    user_data['reply_to'] = reply_to
                else:
                    logger.warn("User %s (%s) managed to break the database if statement in messageReceived" % (update.message.from_user.username, update.message.from_user.id))
                update.message.reply_text(reply_text)

        if user_data['active']
            message = update.message
            user = message.from_user
            MDB.active.update(
                {'_id':message.chat.id},
                {'$set': {
                    {'username':user.username},
                    {'name':user.first_name + " " + user.last_name},
                    {'id':user.id}
                    },
                 '$push': {
                    {'log': message.message_id}
                    }               
                })
            list_of_chats = MDB.active.find('_id':)
            forwardToAll(bot, )
        elif user_data['reply_to']


def callbackResponseHandler(bot, update, user_data):
    logger.debug("callbackResponseHandler %s" % (update.callback_query))

    query = update.callback_query
    qdata = query.data
    message_id = query.message.message_id
    chat_id = query.message.chat_id
    user_id = query.from_user.id
    result = MDB.callback_data.find({'_id':user_id}).next()

    # Long list of choices for the inlinebutton responses
    if result['reason'] == 'admin_initial':
        # This means they chose to give feedback
        if qdata == '0': 
            reply_text = 'Anything you send to this bot will be considered feedback. We recommend starting with what you would like to provide feedback for.\n'
            reply_text = reply_text + "Hitting /cancel will take you back to the initial options."
            user_data['active'] = True
        # Means they chose to answer feedback
        elif qdata == '1':
            reply_text = "Which User would you like to give feedback too?"
            userlist = [[doc['name'],doc['_id']] for doc in MDB.active.find()]
            mongoData = dict()
            keyboard = list()
            for i in range(0,len(userlist)):
                keyboard.append( [InlineKeyboardButton(chats[i][0], callback_data=str(i))] )
                mongoData[str(i)] = {'chosen':userlist[i][1]}
            mongoData['reason':'setting_user']
            reply_markup = InlineKeyboardMarkup(keyboard)
            bot.editMessageText(text=reply_text,
                                chat_id=chat_id,
                                message_id=message_id,
                                reply_markup=reply_markup)
            MDB.callback_data.update({ '_id' : user_id }, mongoData)


    

# A utility function, this is what is called when the job created in main runs
def updateChatList(bot, job):
    logger.debug("-----------------------updateChatList--------------------")
    logger.info("Updating the chat list")
    results = MDB.groups.find()
    for doc in results:
        try:
            chat = bot.getChat(chat_id = doc['_id'])
            logger.info("Chat %s (%s) responded." % (chat.title, chat.id))
            admins = [chatmember.user.id for chatmember in bot.getChatAdministrators(chat_id=doc['_id'])]
            MDB.groups.find_one_and_update({'_id':doc['_id']},
                                           { '$set' : {'title':chat.title, "admins":admins}})
        except TelegramError as te:
            logger,info("Removing %s (%s) from the database, it is not responding, re-add the bot if this is incorrect." % (doc['title'],doc['_id']))
            MDB.groups.remove({'_id':doc['_id']})

        except:
            logger.info("Other error when checking %s (%s), check networking" % (doc['title'],doc['_id']))


def error(bot, update, error):
    logger.warn('Update "%s" cause error "%s"' %(update, error))


def startFromCLI():
    global AUTHTOKEN, MCLIENT, MDB
    parser = argparse.ArgumentParser()
    parser.add_argument('auth', type=str, help="The Auth Token given by Telegram's @botfather")
    parser.add_argument('-l','--llevel', default='debug', choices=['debug','info','warn','none'], help='Logging level for the logger, default = debug')
    logLevel = {'none':logging.NOTSET,'debug':logging.DEBUG,'info':logging.INFO,'warn':logging.WARNING}
    parser.add_argument('-muri','--MongoURI', default='mongodb://localhost:27017', help="The MongoDB URI for connection and auth")
    parser.add_argument('-mdb','--MongoDB', default='feedbackbot', help="The MongoDB Database that this will use")
    args = parser.parse_args()

    logger.setLevel(logLevel[args.llevel])
    AUTHTOKEN = args.auth
    MCLIENT = MongoClient(args.MongoURI)
    MDB = MCLIENT[args.MongoDB]

def main():
    updater = Updater(AUTHTOKEN)

    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start',start, pass_user_data=True))
    dp.add_handler(CommandHandler('cancel',start, pass_user_data=True))
    dp.add_handler(CommandHandler('help',help, pass_user_data=True, pass_chat_data=True))

    dp.add_handler(CallbackQueryHandler(callbackResponseHandler, pass_user_data=True))

    dp.add_handler(MessageHandler(Filters.status_update, statusReceived))
    dp.add_handler(MessageHandler(Filters.all, messageReceived, pass_user_data=True))

    dp.add_error_handler(error)

    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    startFromCLI()
    main()  