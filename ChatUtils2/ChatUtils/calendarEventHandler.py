'''
Created on Jan 19, 2017

@author: hirschag
'''

import datetime
import calendar
import logging
import re

from .extraUtils import checkTypePrivate, isTimeString, isDateString

from telegram import ReplyKeyboardMarkup, ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler, CommandHandler, RegexHandler,\
    MessageHandler, Filters, Job, CallbackQueryHandler

class calendarEventHandler(object):
    '''
    This class will handel creating and checking events that 
    will be created with the ChatUtil telegram bot.
    '''

    def __init__(self, mCollection, job_queue, dp):
        '''
        mCollection : The mongo collection that we will be adding events too.
        '''
        
        self.mCollection = mCollection
        self.logger = logging.getLogger(__name__)

        self.EVENT_SELECT, self.EVENT_TYPING = range(100, 102)
        
        self.reply_keyboard = [['Name', 'Time', 'Date'],
                              ['Group','Place','Description']]
        
        self.usedKeys = ['Name','Time','Date','Description','Place','Group']

        self.conversationHandler = ConversationHandler(
            entry_points=[CommandHandler('create_event', self.eventStartEditing, pass_user_data=True)],
            states = {
                self.EVENT_SELECT: [RegexHandler('^(Name|Time|Date|Description|Place|Group)$',
                                                 self.eventPromptTyping,
                                                 pass_user_data=True),
                                    RegexHandler('^Done$',
                                                self.eventCreate,
                                                pass_user_data=True),
                                    RegexHandler('^Cancel$',
                                                self.eventCancel,
                                                pass_user_data=True)
                                    ],
                self.EVENT_TYPING: [MessageHandler(Filters.text,
                                                   self.eventSelectEditing,
                                                   pass_user_data=True),
                                    CallbackQueryHandler(self.dateHandler,
                                                         pass_user_data=True,
                                                         pattern='^cal-.*'),
                                    CallbackQueryHandler(self.clockHandler,
                                                         pass_user_data=True,
                                                         pattern='^clk-.*')
                                    ]},
            fallbacks = [MessageHandler(Filters.text,
                                        self.editPreviousMessage,
                                        edited_updates=True,
                                        pass_user_data=True)],
            allow_reentry = True)

        purgeOld = Job(self.removeOldEvents, 60*60*24)
        job_queue.put(purgeOld, next_t=0)

        dp.add_handler(CommandHandler('list_events', self.getEventList))
        dp.add_handler(self.conversationHandler)

    def __create_event_temp(self, user_data):
        self.logger.debug("Date and time test: %s"%str(user_data))
        return """
Current Event:
Name: %s
Date & Time: %s @ %s
Place: %s
Group: %s
Description:
%s
\n""" % (user_data['Name'][0] if user_data['Name'] else 'None',
         user_data['Date'][0] if user_data['Date'] else 'None',
         user_data['Time'][0] if user_data['Time'] else 'None',
         user_data['Place'][0] if user_data['Place'] else 'None',
         user_data['Group'][0] if user_data['Group'] else 'None',
         user_data['Description'][0] if user_data['Description'] else 'None')

    def eventStartEditing(self, bot, update, user_data):

        if checkTypePrivate(update):
            self.logger.info("%s (%s) is creating an event."
                             % (update.message.from_user.username, update.message.from_user.id))

            user_data['id'] = update.message.from_user.id

            # Reset everything
            for key in self.usedKeys:
                user_data[key] = None

            # Copy down from global
            reply_keyboard = list(self.reply_keyboard)

            # append on Cancel, they have only just begun, no need for done
            reply_keyboard.append(['Cancel'])

            markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
            reply_text = "Please select which you would like to edit, once you've entered something for all, you will be able to create the event."

            update.message.reply_text(reply_text, reply_markup=markup)

            return self.EVENT_SELECT
        else:
            update.message.reply_text("Please message this bot directly to create an event.")
            return ConversationHandler.END
         
    def createEventDoc(self, forChatTitle, user_data, username, name):
        self.logger.debug("Attempting to create event for %s" % forChatTitle)
        result = self.mCollection.find({"title":forChatTitle})
        self.logger.debug("Creating event, checking title %s" % result.count())
        
        if result.count() > 0:
            self.logger.info("Creating event for %s" % forChatTitle)
            newEvent = dict()
            newEvent['name'] = user_data['Name'][0]
            newEvent['description'] = user_data['Description'][0]
            timeDate = user_data['Time'][0] + ' @ ' + user_data['Date'][0]
            timeDate = datetime.datetime.strptime(timeDate, '%I:%M %p @ %m/%d/%Y')
            newEvent['date'] = timeDate
            newEvent['place'] = user_data['Place'][0]
            newEvent['creator'] = username if username else name
            self.mCollection.update({'title':forChatTitle},
                                         {'$push':{
                                             'events':newEvent}})
            self.logger.debug('Event Created: %s' % str(newEvent))
            return True
        else:
            return False
         
    def eventCreate(self, bot, update, user_data):
        forChatTitle = user_data['Group'][0]
        username = update.message.from_user.username
        name = update.message.from_user.first_name + " " +  update.message.from_user.last_name
        self.logger.debug("userData: %s" % (str(user_data)))
        if self.createEventDoc(forChatTitle, user_data, username, name):
            reply_text = "Created!"
        else:
            reply_text="Something went wrong, please try again in a few minutes (the group title may have changed)\n if this problem persists, talk to @YTKileroy, and tell YTK what is going on."
        update.message.reply_text(reply_text)
        return ConversationHandler.END
            
    def eventPromptTyping(self, bot, update, user_data):
        '''
        This is only for the major topics, done and cancel will be handled in separate methods
        '''
        
        # Which one did they choose?
        # select next blank if choice is not one of list

        self.logger.debug("Prompting typing")

        userChoice = update.message.text
        
        user_data['editing_choice'] = userChoice
        reply_text = "Now editing %s.\n" % userChoice
        self.logger.debug("Chosen: %s" % userChoice)
        reply_markup = None

        try:
            if userChoice == 'Time':
                reply_text += "Please select the time you would like, or send me the Time of the event in `HH:MM (am|pm)` format."
                now = datetime.datetime.now()
                hr = now.hour
                min = now.minute
                if hr > 12:
                    hr = hr-12
                    apm = False
                else:
                    apm = True
                reply_markup = self.create_clock(hr, min, apm)
                user_data['time_data'] = [hr, min, apm]
                self.logger.debug("Time markup created successfully")
            elif userChoice == 'Date':
                self.logger.debug("Creating date")
                reply_text += "Please select the date you would like, or send me a date in the MM/DD/YYYY format"
                reply_markup = self.create_calendar(datetime.date.today().year, datetime.date.today().month)
                user_data['cal_data'] = [datetime.date.today().year, datetime.date.today().month]
                self.logger.debug("Created date")

            elif user_data['editing_choice'] == 'Group':
                result = self.mCollection.find({'users':update.message.from_user.id})
                if result.count() > 0:
                    reply_keyboard = []
                    reply_text += "Please select the group you would like to create an event for."
                    for group in result:
                        reply_keyboard.append([group['title']])

                    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
                    update.message.reply_text(reply_text, reply_markup=markup)
                    return self.EVENT_TYPING
                else:
                    reply_text += "Please register with a group, go to any chat this bot is in and type /registerme"
                    reply_keyboard = [['Okay!']]

                    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
                    update.message.reply_text(reply_text, reply_markup=markup)
                    return ConversationHandler.END
            else:
                reply_text += "Please send me the text you would like displayed for the %s" % userChoice
        except Exception as e:
            self.logger.warning("exception in prompt typing: %s"%(str(e)))

        update.message.reply_text(reply_text, reply_markup=reply_markup)
        return self.EVENT_TYPING

    def eventSelectEditing(self, bot, update, user_data):
        self.logger.debug("Selecting editing from %s"%update.message.text)
        user_data[user_data['editing_choice']] = [update.message.text, update.message.message_id]

        reply_text = ""

        if user_data['editing_choice'] == 'Time' and not isTimeString(update.message.text):
            reply_text = "Your Time is not formatted correctly, it must be \n `HH:MM xx`\nEx: `12:30 AM`\n"
            user_data['Time'][0] = None
        elif user_data['editing_choice'] == 'Date' and not isDateString(update.message.text):
            reply_text = "Your Date is not formatted correctly, it must be\n`MM/DD/YYYY`\nEx: `02/25/2017`\n"
            user_data['Date'][0] = None

        reply_keyboard = list(self.reply_keyboard)

        if all(user_data[key] for key in self.usedKeys):
            reply_keyboard.append(['Cancel', 'Done'])
        else:
            reply_keyboard.append(['Cancel'])

        reply_text += self.__create_event_temp(user_data)


        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        reply_text += "Please select which you would like to edit, once you'be entered something for everything, you will be able  to make the event."

        update.message.reply_text(reply_text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)

        return self.EVENT_SELECT

    def dateHandler(self, bot, update, user_data):
        query = update.callback_query
        data = query.data
        reply_markup = None
        dt = user_data['cal_data']
        if 'p' in data[4:]:
            dt[1] -= 1
            if dt[1] is 0:
                dt[1] = 12
                dt[0] -= 1
            reply_markup = self.create_calendar(*dt)
            query.edit_message_reply_markup(reply_markup=reply_markup)
            return self.EVENT_TYPING

        if 'n' in data[4:]:
            dt[1] += 1
            if dt[1] is 13:
                dt[1] = 1
                dt[0] += 1
            reply_markup = self.create_calendar(*dt)
            query.edit_message_reply_markup(reply_markup=reply_markup)
            return self.EVENT_TYPING

        if 'd' in data[4:]:
            self.logger.debug("Data to be processed: " + data)
            day, month, year = re.search('cal-d-([0-9]+)-([0-9]+)-([0-9]+)', data).groups()
            day = int(day)
            month = int(month)
            year = int(year)
            user_data['Date'] = "%d/%d/%d"%(month, day, year)
            reply_keyboard = list(self.reply_keyboard)

            if all(user_data[key] for key in self.usedKeys):
                reply_keyboard.append(['Cancel', 'Done'])
            else:
                reply_keyboard.append(['Cancel'])

            markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
            reply_text = "Date Selected: %s\n\n"%user_data['Date']
            reply_text += self.__create_event_temp(user_data)
            reply_text += "Please select which you would like to edit, once you'be entered something for everything, you will be able  to make the event."
            query.edit_message_reply_markup(reply_markup=None) # remove date chooser
            bot.send_message(chat_id = user_data['id'],
                             text = reply_text,
                             reply_markup = markup)

            return self.EVENT_SELECT

        else:
            self.logger.error("Something went wrong here: %s"%(str(update)))
            return self.EVENT_TYPING

    def clockHandler(self, bot, update, user_data):
        self.logger.debug("In clock handler")
        query = update.callback_query
        data = query.data
        td = user_data['time_data'] # [hr, min, apm]
        reply_markup = None
        if 'done' not in data:
            self.logger.debug("Not done, updating clock")
            if 'h' in data:
                if 'u' in data:
                    td[0] += 1
                else:
                    td[0] -= 1
            elif 'm' in data:
                if 't' in data:
                    if 'u' in data:
                        td[1] += 10
                    else:
                        td[1] -= 10
                else:
                    if 'u' in data:
                        td[1] += 1
                    else:
                        td[1] -= 1
            else:
                td[2] = not td[2]
            self.logger.debug("%d %d %s"%(td[0], td[1], str(td[2])))
            if td[0] > 12:
                td[0] = 1
            elif td[0] < 1:
                td[0] = 12
            td[1] = td[1]%60
            reply_markup=self.create_clock(td[0], td[1], td[2])
            query.edit_message_reply_markup(reply_markup=reply_markup)
            return self.EVENT_TYPING
        else:
            user_data['Time'] = "%d:%02.0f %s"%(td[0], td[1], 'AM' if td[2] else 'PM')
            reply_text = "Selected time: %s\n\n"%user_data['Time']
            query.edit_message_reply_markup(reply_markup=None)

            reply_keyboard = list(self.reply_keyboard)

            if all(user_data[key] for key in self.usedKeys):
                reply_keyboard.append(['Cancel', 'Done'])
            else:
                reply_keyboard.append(['Cancel'])

            markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
            reply_text += self.__create_event_temp(user_data)
            reply_text += "Please select which you would like to edit, once you'be entered something for everything, you will be able  to make the event."
            bot.send_message(chat_id=user_data['id'],
                             text=reply_text,
                             reply_markup=markup)
            return self.EVENT_SELECT

    def eventCancel(self, bot, update, user_data):
        reply_text = "Canceled"
        for key in self.usedKeys:
            user_data[key] = None
        update.message.reply_text(reply_text)
        return ConversationHandler.END

    def editPreviousMessage(self, bot, update, user_data):
        self.logger.debug("Caught unknown message")
        reply_text = ""
        if update.edited_message:
            chat_id = update.edited_message.chat.id
            self.logger.debug("caught edit for id: %d" % update.edited_message.message_id)

            text = update.edited_message.text
            self.logger.debug("text to amend %s" % text)

            edited_key = None
            for key in self.usedKeys:
                if user_data[key] and user_data[key][1] == update.edited_message.message_id:
                    edited_key = key

            if edited_key is None:
                return

            if edited_key == 'Time' and not isTimeString(text):
                reply_text = "Your Time is not formatted correctly, it must be \n `HH:MM xx`\nEx: `12:30 AM`\n"
            elif user_data['editing_choice'] == 'Date' and not isDateString(text):
                reply_text = "Your Date is not formatted correctly, it must be\n`MM/DD/YYYY`\nEx: `02/25/2017`\n"

            user_data[edited_key][0] = text
        else:
            chat_id = update.message.chat.id

            reply_keyboard = list(self.reply_keyboard)

            if all(user_data[key] for key in self.usedKeys):
                reply_keyboard.append(['Cancel', 'Done'])
            else:
                reply_keyboard.append(['Cancel'])

            markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)

            reply_text += self.__create_event_temp(user_data)

            reply_text += "Please select which you would like to edit, once you'be entered something for everything, you will be able  to make the event."

            bot.send_message(chat_id=chat_id,
                             text=reply_text,
                             reply_markup=markup,
                             parse_mode=ParseMode.MARKDOWN)

            return self.EVENT_SELECT

    def getEventList(self, bot, update):
        days = 21
        self.logger.info("Getting events for %s" % update.message.chat.title)
        then = datetime.datetime.now() + datetime.timedelta(days=days)
        now = datetime.datetime.now() - datetime.timedelta(days=1)
        self.logger.debug("Listing events from now: %s to then: %s"%(now.strftime('%a, %b %d, %Y @ %I:%M %p'), then.strftime('%a, %b %d, %Y @ %I:%M %p')))
        result = self.mCollection.find({'title':update.message.chat.title})
        self.logger.debug("result count: %d"%result.count())
        reply_text = ""
        try:
            events = sorted(result.next()['events'], key=lambda t: t['date'])
            reply_text = "Events! Please PM @%s if you would like to create an event.\n" % bot.username
            for event in events:
                #dt = datetime.datetime.strptime(event['date'], '%Y-%m-%d %H:%M:%S')
                dt = event['date']
                if dt <= then and dt >= now:
                    reply_text+="""
Name: %s
Date & Time: %s
Place: %s
Description:
%s
Creator: @%s
\n""" % (event['name'], dt.strftime('%a, %b %d, %Y @ %I:%M %p'), event['place'], event['description'], event['creator'])
        
        except Exception as e:
            self.logger.debug("Exception: %s"%e)
            reply_text = """There does not appear to be anything within the next 3 weeks. 
Please PM @%s if you would like to create an event, or see events outside of 3 weeks.""" % bot.username
        
        update.message.reply_text(reply_text, quote=False)

    def removeOldEvents(self, bot, job):
        self.logger.info("Removing old events.")
        self.logger.debug("-----------REMOVING OLD EVENTS------------")
        now = datetime.datetime.now() - datetime.timedelta(days=1)
        res = self.mCollection.update({},{'$pull' : {'events': {'date' : {'$lt':now}}}}, multi=True)
        self.logger.debug("Events removed: %s" % res['nModified'])
        self.logger.debug('----------Done Removing Events-------------')

    def create_calendar(self, year, month):
        self.logger.debug("in create calendar")
        markup = []
        markup.append([InlineKeyboardButton(calendar.month_name[month] + ", " + str(year), callback_data=' ')])
        week_days = ["M", "T", "W", "R", "F", "S", "U"]

        temp = []
        for day in week_days:
            temp.append(InlineKeyboardButton(day, callback_data=' '))
        markup.append(temp)

        cur_cal = calendar.monthcalendar(year, month)
        for week in cur_cal:
            temp = []
            for day in week:
                if day is 0:
                    temp.append(InlineKeyboardButton(" ", callback_data=' '))
                    continue
                temp.append(InlineKeyboardButton(str(day), callback_data='cal-d-%d-%d-%d' % (day, month, year)))

            markup.append(temp)
        temp = []
        temp.append(InlineKeyboardButton('<', callback_data='cal-p'))
        temp.append(InlineKeyboardButton('>', callback_data='cal-n'))
        markup.append(temp)
        self.logger.debug("Created calendar")
        return InlineKeyboardMarkup(markup)
        #return InlineKeyboardMarkup([[InlineKeyboardButton("This is a test", callback_data=' ')]])

    def create_clock(self, hr, min, apm):
        # apm :: True for AM, False for PM
        self.logger.debug("Creating clock for %d %d %s"%(hr, min, apm))
        markup = []
        temp = []
        markup.append([
            InlineKeyboardButton('^', callback_data='clk-h-u'),
            InlineKeyboardButton(' ', callback_data=' '),
            InlineKeyboardButton('^', callback_data='clk-m-t-u'),
            InlineKeyboardButton('^', callback_data='clk-m-s-u'),
            InlineKeyboardButton('^', callback_data='clk-a-u')
        ])
        markup.append([
            InlineKeyboardButton(str(hr), callback_data=' '),
            InlineKeyboardButton(':', callback_data=' '),
            InlineKeyboardButton(str(int(min/10)), callback_data=' '),
            InlineKeyboardButton(str(int(min%10)), callback_data=' '),
            InlineKeyboardButton('AM' if apm else 'PM', callback_data=' ')
        ])
        markup.append([
            InlineKeyboardButton('V', callback_data='clk-h-d'),
            InlineKeyboardButton(' ', callback_data=' '),
            InlineKeyboardButton('V', callback_data='clk-m-t-d'),
            InlineKeyboardButton('V', callback_data='clk-m-s-d'),
            InlineKeyboardButton('V', callback_data='clk-a-d')
        ])
        markup.append([InlineKeyboardButton("Done", callback_data="clk-done")])
        self.logger.debug("Created clock")
        return InlineKeyboardMarkup(markup)
