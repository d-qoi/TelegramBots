'''
Created on Jan 19, 2017

@author: hirschag
'''
import logging

from telegram import ReplyKeyboardMarkup
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, Filters, CallbackQueryHandler

from ChatUtils.extraUtils import checkValidCommand, checkTypePrivate, getUserName


class pollEventHandler(object):
    '''
    Handels poll creation and answering
    '''

    def __init__(self, mCollection, mPollData):
        self.mCollection = mCollection
        self.mPollData = mPollData
        
        self.logger = logging.getLogger(__name__)
        
        self.POLLQUESTION, self.POLLANSWER, self.POLLGROUP = range(100,103)
        self.POLLGETANSWERING, self.POLLCAST = range(200,202)
        
        self.pollCreateHandler = ConversationHandler(
            entry_points=[CommandHandler('createpoll',
                                         self.pollStartEditing,
                                         pass_user_data=True)],
            states = {
                self.POLLQUESTION:[MessageHandler(Filters.text,
                                                  self.pollQuestionReceived,
                                                  pass_user_data=True)],
                self.POLLANSWER: [MessageHandler(Filters.text,
                                                 self.pollAnswerReceived,
                                                 pass_user_data=True),
                                  CommandHandler('done',
                                                 self.pollAskForGroup,
                                                 pass_user_data=True)],
                self.POLLGROUP: [MessageHandler(Filters.text,
                                                self.pollCreatePoll,
                                                pass_user_data=True)]},
            fallbacks=[MessageHandler('cancel',
                                      self.pollCancel,
                                      pass_user_data=True)])
        
        self.pollAnswerHandler = ConversationHandler(
            entry_points=[CommandHandler('answerpoll',
                                         self.answerPollList,
                                         pass_user_data=True)],
            states = {
                self.POLLGETANSWERING : [CallbackQueryHandler()]}
            )
        
    def createEditingMessage(self, user_data):
        reply_text = user_data['question']
        reply_text += '\n\n'
        
        if user_data['answers']:
            for answer in range(0, len(user_data['answers'])):
                reply_text += "%d. %s \n" %(answer+1, user_data['answers'][answer])
            
            reply_text += '\n\n'
                
        return reply_text

        
    def pollStartEditing(self, bot, update, user_data):
        if not checkValidCommand(update.message.text, bot.username):
            return ConversationHandler.END
        
        if not checkTypePrivate(update):
            reply_text = "Please message this bot directly to create a poll."
            update.message.reply_text(reply_text)
            return ConversationHandler.END
            
        self.logger.info("User %s is creating a poll." % update.message.from_user.id)
        reply_text = "Please send me the question you would like to ask."
        nextMessage = update.message.reply_text(reply_text)
        user_data['message_id'] = nextMessage.message_id
        user_data['question'] = ""
        user_data['answers'] = list()
        return self.POLLQUESTION
    
    def pollQuestionReceived(self, bot, update, user_data):
        user_data['question'] = update.message.text
        
        reply_text = self.createEditingMessage(user_data)
        
        reply_text += "Now please send me the answers for the poll."
        
        bot.editMessageText(text = reply_text,
                            message_id = user_data['message_id'],
                            chat_id = update.message.chat.id)
        return self.POLLANSWER
        
    
    def pollAnswerReceived(self, bot, update, user_data):
        user_data['answers'].append(update.message.text)
        
        reply_text = self.createEditingMessage(user_data)
        
        reply_text += "Please send me the next answer for the poll. send /done when you are finished creating answers."
        
        bot.editMessageText(text = reply_text,
                            message_id = user_data['message_id'],
                            chat_id = update.message.chat.id)
        return self.POLLANSWER
    
    def pollAskForGroup(self, bot, update, user_data):
        user_id = update.message.from_user.id
        result = self.mCollection.find({'users':user_id})
        if result.count() > 0:
            reply_keyboard = []
            for doc in result:
                reply_keyboard.append([doc['title']])
            
            reply_markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
            reply_text = "Here is the poll so far:\n\n"
            reply_text += self.createEditingMessage(user_data)
            reply_text = "Which group would you like to send this poll to?"
            
            update.message.reply_text(reply_text, reply_markup=reply_markup)
            
            return self.POLLGROUP
        
        else:
            reply_text = "You are not registered with any groups, please send /registerme to any chat with this bot to use this feature. "
            reply_text += "\n Once you have done that, you will be able to send /createpoll to create a poll."
            update.message.reply_text(reply_text)
            return ConversationHandler.END
    
    def pollCreatePoll(self, bot, update, user_data):
        newPoll = dict()
        newPoll['question'] = user_data['question']
        newPoll['answers'] = user_data['answers']
        
        result = self.mCollection.find_one_and_update({'title':update.message.text},{'$push':{'polls':newPoll}})
        
        if not result:
            reply_text = "Please try again."
            update.message.reply_text(reply_text)
            return self.pollAskForGroup(bot, update, user_data)
        else:
            reply_text = "Added poll to %s, the group will be notified." % update.message.text
            update.message.reply_text(reply_text)
            chat_id = result['_id']
            reply_text = "A new poll (%s) has been created by %s.\n" % (newPoll['question'], getUserName(update.message.from_user))
            reply_text += "If you would like to respond, please send /answerpoll to @%s." % bot.username
            bot.sendMessage(text = reply_text,
                            chat_id = chat_id)
        
        return ConversationHandler.END
            
    
    def pollCancel(self, bot, update, user_data):
        update.message.reply_text('Canceling new poll.')
        return ConversationHandler.END

    def answerPollList(self, bot, update):
        pass
        
        
        
        