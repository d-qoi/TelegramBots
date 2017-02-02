#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import datetime
import logging

from telegram import ReplyKeyboardMarkup
from telegram.ext import ConversationHandler


class eventCreate(ChatUtilObject):

	def __init__(self, mDatabase):
		self.mDatabase = mDatabase
		self.logger = logging.getLogger(__name__)
		self.EVENTSELECT, self.EVENTTYPING, self.EVENTCREATE = range(100,103) 


	@staticmethod
	def isTimeString(input):
	    try:
	        time.strptime(input, '%H:%M')
	        return True
	    except ValueError:
	        return False


	@staticmethod
	def isDateString(toCheck):
	    try:
	        eventDate = time.strptime(toCheck, '%m/%d/%Y')
	        #print(eventDate)
	        now = datetime.datetime.now()
	        currDate = time.strptime('%d/%d/%d' %(now.month, now.day, now.year), '%m/%d/%Y')
	        #print(currDate)
	        return eventDate >= currDate
	    except ValueError:
	        #print('failure')
	        return False




	def createEventDoc(self, forChatTitle, user_data, username):
	    result = mDatabase.groups.find({"title":forChatTitle})
	    if result.count() == 1:
	        logger.info("Creating Event for %s" % forChatTitle)
	        newEvent = dict()
	        newEvent['name'] = user_data['Name']
	        newEvent['description'] = user_data['Description']
	        newEvent['time'] = user_data['Time']
	        newEvent['place'] = user_data['Place']
	        newEvent['date'] = newEvent['Date']
	        newEvent['creator'] = username
	        mDatabase.groups.update({'title':forChatTitle},{'$push':{'events':newEvent}})
	        logger.debug("Created Event: %s" % (str(newEvent)))
	        return True
	    else:
	        return False




	def eventStartEditing(self, bot, update, user_data):
	    if checkTypePrivate(update):
	        logger.info("%s (%s) is creating an event." % (update.message.from_user.username, update.message.from_user.id))

	        #reset all keys, and set them.
	        for key in ['Name','Time','Date','Description','Place','Group']:
	            user_data[key] = None

	        # Set up the keyboard
	        reply_keyboard = [['Name', 'Time', 'Date'],
	                          ['Group','Place'],
	                          ['Description']]

	        # If the user has answered all questions, add 'done', otherwise just add 'cancel'
	        if all (key in user_data for key in ['Name','Time','Date','Description','Place','Group']):
	            reply_keyboard.append(['Cancel','Done'])
	        else:
	            reply_keyboard.append(['Cancel'])

	        # Make the markup, needs to be one time because users need to reply to this thing.
	        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
	        reply_text = "Please select which you would like to edit, once you've entered something for all of these, you will be able to create the event."

	        update.message.reply_text(reply_text, reply_markup=markup)

	        #We are prompting them to select an event, need to handle that next
	        return EVENTSELECT
	    else:
	        update.message.reply_text("Please message this bot directly to create an event.")
	        return ConversationHandler.END




	def eventSelectEditing(self, bot, update, user_data):

	    user_data[user_data['editing_choice']] = update.message.text
	    reply_text = ""

	    if user_data['editing_choice'] == 'Time' and not isTimeString(update.message.text):
	        reply_text = "Your time string is not formatted correctly, please try again.\n\n"
	        user_data['Time'] = None
	    elif user_data['editing_choice'] == 'Date' and not isDateString(update.message.text):
	        reply_text = 'You Date string is not formatted correctly (m/d/20xx), please try again.\n\n'
	        user_data['Date'] = None

	    reply_keyboard = [['Name', 'Time', 'Date'],
	                          ['Group','Place'],
	                          ['Description']]

	    if all (key in user_data for key in ['Name','Time','Date','Description','Place','Group']):
	        reply_keyboard.append(['Cancel','Done'])
	    else:
	        reply_keyboard.append(['Cancel'])
	    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
	    reply_text += "Please select which you would like to edit, once you've entered something for all of these, you will be able to create the event."
	    update.message.reply_text(reply_text, reply_markup=markup)
	    return EVENTSELECT



	def eventPromptTyping(self, bot, update, user_data):
	    # Which did they choose! Store it for later use
	    userChoice = update.message.text
	    user_data['editing_choice'] = userChoice

	    # If they managed to select done
	    if userChoice == 'Done':
	        if createEventDoc(user_data['Group'], user_data, update.message.from_user.username):
	            reply_text = "Created the event!"
	            update.message.reply_text(reply_text)
	            return ConversationHandler.END

	    elif userChoice == 'Cancel':
	        reply_text = "Canceled."
	        for key in ['Name','Time','Date','Description','Place','Group','editing_choice']:
	            user_data[key] = None
	            update.message.reply_text(reply_text)
	            return ConversationHandler.END

	    elif userChoice == 'Time':
	        reply_text = "Please send me the Time of the event in HH:MM format."

	    elif userChoice == 'Date':
	        reply_text = "Please send me the Date of this event in MM/DD/YY"
	    else:
	        reply_text = "Please send me the %s of the event." % userChoice.lower()
	    update.message.reply_text(reply_text)



	def eventCancel(self, bot, update, user_data):
	    reply_text = "Canceled."
	    for key in ['Name','Time','Date','Description','Place','Group','editing_choice']:
	        user_data[key] = None
	    update.message.reply_text(reply_text)
	    return ConversationHandler.END