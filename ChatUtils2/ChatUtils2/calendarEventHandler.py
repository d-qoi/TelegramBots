'''
Created on Jan 19, 2017

@author: hirschag
'''

import datetime
import logging

from extraUtils import checkTypePrivate, isDateString, isTimeString, checkValidCommand
from telegram import ReplyKeyboardMarkup, ParseMode
from telegram.ext import ConversationHandler, CommandHandler, RegexHandler,\
    MessageHandler, Filters, Job

class calendarEventHandler(object):
    '''
    This class will handel creating and checking events that 
    will be created with the ChatUtil telegram bot.
    '''

    def __init__(self, mCollection, job_queue):
        '''
        mCollection : The mongo collection that we will be adding events too.
        '''
        
        self.mCollection = mCollection
        self.logger = logging.getLogger(__name__)
        
        self.EVENTSELECT, self.EVENTTYPING = range(100,102)
        
        self.reply_keyboard = [['Name', 'Time', 'Date'],
                              ['Group','Place','Description']]
        
        self.usedKeys = ['Name','Time','Date','Description','Place','Group']
        
        self.conversationHandler = ConversationHandler(
            entry_points=[CommandHandler('createevent', self.eventStartEditing, pass_user_data=True)],
            states = {
                self.EVENTSELECT: [RegexHandler('^(Name|Time|Date|Description|Place|Group)$',
                                                self.eventPromptTyping,
                                                pass_user_data=True),
                                   RegexHandler('^Done$',
                                                self.eventCreate,
                                                pass_user_data=True),
                                   RegexHandler('^Cancel$',
                                                self.eventCancel,
                                                pass_user_data=True)],
                self.EVENTTYPING: [MessageHandler(Filters.text,
                                                  self.eventSelectEditing,
                                                  pass_user_data=True)]},
            fallbacks = [MessageHandler(Filters.all,
                                       self.eventCancel,
                                       pass_user_data=True)],
            allow_reentry = False)
        
        purgeOld = Job(self.removeOldEvents, 60*60*24)
        job_queue.put(purgeOld, next_t=0)
         
    def createEventDoc(self, forChatTitle, user_data, username):
        self.logger.debug("Attempting to create event for %s" % forChatTitle)
        result = self.mCollection.find({"title":forChatTitle})
        self.logger.debug("Creating event, checking title %s" % result.count())
        
        if result.count() > 0:
            self.logger.info("Creating event for %s" % forChatTitle)
            newEvent = dict()
            newEvent['name'] = user_data['Name']
            newEvent['description'] = user_data['Description']
            timeDate = user_data['Time'] + ' @ ' + user_data['Date']
            timeDate = datetime.datetime.strptime(timeDate, '%I:%M %p @ %m/%d/%Y')
            newEvent['date'] = timeDate
            newEvent['place'] = user_data['Place']
            newEvent['creator'] = username
            self.mCollection.update({'title':forChatTitle},
                                         {'$push':{
                                             'events':newEvent}})
            self.logger.debug('Event Created: %s' % str(newEvent))
            return True
        else:
            return False
         
    def eventCreate(self, bot, update, user_data):
        forChatTitle = user_data['Group']
        username = update.message.from_user.username
        self.logger.debug("userData: %s" % (str(user_data)))
        if self.createEventDoc(forChatTitle, user_data, username):
            reply_text = "Created!"
        else:
            reply_text="Something went wrong, please try again in a few minutes (the group title may have changed)\n if this problem persists, talk to @YTKileroy, and tell YTK what is going on."
        update.message.reply_text(reply_text)
        return ConversationHandler.END
           
    def eventStartEditing(self, bot, update, user_data):
        if not checkValidCommand(update.message.text, bot.username):
            return ConversationHandler.END
        
        if checkTypePrivate(update):
            self.logger.info("%s (%s) is creating an event." 
                             % (update.message.from_user.username, update.message.from_user.id))
            
            # Reset everything
            for key in self.usedKeys:
                user_data[key] = None
            
            # Copy down from global
            reply_keyboard = list(self.reply_keyboard)
            
            # append on Cancel, they have only just begun, no need for done
            reply_keyboard.append(['Cancel'])
                
            markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
            reply_text = "Please select which you would like to edit, once you've entered something for all, you will be able to create the event."
            
            
            update.message.reply_text(reply_text, reply_markup = markup)
            
            return self.EVENTSELECT
        else:
            update.message.reply_text("Please message this bot directly to create an event.")
            return ConversationHandler.END
            
    def eventSelectEditing(self, bot, update, user_data):
        
        user_data[user_data['editing_choice']] = update.message.text
        
        reply_text = ""
        
        if user_data['editing_choice'] == 'Time' and not isTimeString(update.message.text):
            reply_text = "Your Time is not formatted correctly, it must be \n `HH:MM xx`\nEx: `12:30 AM`\n"
            user_data['Time'] = None
        elif user_data['editing_choice'] == 'Date' and not isDateString(update.message.text):
            reply_text = "Your Date is not formatted correctly, it must be\n`MM/DD/YYYY`\nEx: `02/25/2017`\n"
            user_data['Date'] = None
                
        
        reply_keyboard = list(self.reply_keyboard)
        
        if all (user_data[key] for key in self.usedKeys):
            reply_keyboard.append(['Cancel','Done'])
        else:
            reply_keyboard.append(['Cancel'])
        
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        reply_text += "Please select which you would like to edit, once you'be entered something for everything, you will be able  to make the event."
        
        update.message.reply_text(reply_text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)
        
        return self.EVENTSELECT          
            
    def eventPromptTyping(self, bot, update, user_data):
        '''
        This is only for the major topics, done and cancel will be handled in separate methods
        '''
        
        # Which one did they choose?
        userChoice = update.message.text
        if userChoice not in self.usedKeys:
            for key in self.usedKeys:
                if user_data[key] is None:
                    userChoice = key
                    break
        
        user_data['editing_choice'] = userChoice
        reply_text = "Now editing %s.\n" % userChoice
        
        if userChoice == 'Time':
            reply_text += "Please send me the Time of the event in `HH:MM (am|pm)` format."
        elif userChoice == 'Date':
            reply_text += "Please send me the Date of the event in `MM/DD/YYYY` format.\n It must also be after todays date."
        
        elif user_data['editing_choice'] == 'Group':
            result = self.mCollection.find({'users':update.message.from_user.id})
            if result.count() > 0:
                reply_keyboard = []
                reply_text += "Please select the group you would like to create an event for."
                for group in result:
                    reply_keyboard.append([group['title']])
                
                markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
                update.message.reply_text(reply_text, reply_markup=markup)
                return self.EVENTTYPING
            else:
                reply_text += "Please register with a group, go to any chat this bot is in and type /registerme"
                reply_keyboard.append(['Okay!'])
                
                markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
                update.message.reply_text(reply_text, reply_markup=markup)
                return ConversationHandler.END            
        else:
            reply_text += "Please send me the text you would like displayed for the %s" % userChoice
        
        update.message.reply_text(reply_text, parse_mode=ParseMode.MARKDOWN)
        return self.EVENTTYPING

    def eventCancel(self, bot, update, user_data):
        reply_text = "Canceled"
        for key in self.usedKeys:
            user_data[key] = None
        update.message.reply_text(reply_text)
        return ConversationHandler.END
            
    def getEventList(self, bot, update):
        if not checkValidCommand(update.message.text, bot.username):
            return
        days = 21
        self.logger.info("Getting events for %s" % update.message.chat.title)
        then = datetime.datetime.now() + datetime.timedelta(days=days)
        result = self.mCollection.find({'title':update.message.chat.title})
        reply_text = ""
        try:
            events = sorted(result.next()['events'], key=lambda t: t['date'])
            reply_text = "Events! Please PM @%s if you would like to create an event.\n" % bot.username
            for event in events:
                if event['date'] <= then:
                    reply_text+="""
Name: %s
Date & Time: %s
Place: %s
Discription:
%s
Creator: @%s
___\n""" % (event['name'],event['date'], event['place'], event['description'], event['creator'])
        
        except:
            reply_text = "There does not appear to be anything within the next 3 weeks. Please PM @%s if you would like to create an event." % bot.username
        
        update.message.reply_text(reply_text)
        
    def removeOldEvents(self, bot, job):
        self.logger.info("Removing old events.")
        self.logger.debug("-----------REMOVING OLD EVENTS------------")
        now = datetime.datetime.now()
        res = self.mCollection.update({},{'$pull' : {'events': {'date' : {'$lt':now}}}}, multi=True)
        self.logger.debug("Events removed: %s" % res['nModified'])
        self.logger.debug('----------Done Removing Events-------------')
        
    
    
    
    