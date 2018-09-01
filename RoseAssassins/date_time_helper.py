#TODO Timezone support

import datetime
import calendar
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from MongoDict import MongoDict

class DateTimeHelper:
    def __init__(self, logger=None, collection=None):
        self.logger = logger or logging.getLogger(__name__)
        self.data = MongoDict(collection=collection)

    def create_calendar_message(self, bot, update):
        now = datetime.datetime.now()
        self.data[update.effective_chat.id] = [now.year, now.month]
        reply_markup = self.create_calendar_markup(*self.data[update.effective_chat.id])
        if update.callback_query:
            bot.edit_message_text("Please choose the end date for your game.",
                                  reply_markup=reply_markup,
                                  chat_id = update.effective_chat.id,
                                  message_id = update.effective_message.message_id)
            return None
        update.effective_message.reply_text("Please choose the end date for your game.",
                                  reply_markup=reply_markup)
        return None
    
    def calendar_handler(self, bot, update):
        cq = update.callback_query
        data = update.callback_query.data
        id = update.effective_chat.id
        date = None
        reply_markup = None
        cq.answer()
        if 'p' in data:
            self.data[id][1] -= 1
            if self.data[id][1] is 0:
                self.data[id][1] = 12
                self.data[id][0] -= 1
            reply_markup=self.create_calendar_markup(*self.data[id])

        elif 'n' in data:
            self.data[id][1] += 1
            if self.data[id][1] is 13:
                self.data[id][1] = 1
                self.data[id][0] += 1
            reply_markup = self.create_calendar_markup(*self.data[id])

        elif 'd' in data:
            date = datetime.datetime.strptime(data, 'cal-d-%d-%m-%Y')
            bot.edit_message_text("Date Updated",
                                  chat_id=cq.message.chat_id,
                                  message_id=cq.message.message_id)

        bot.answer_callback_query(cq.id)
        if reply_markup:
            bot.edit_message_reply_markup(chat_id=cq.message.chat_id,
                                          message_id=cq.message.message_id,
                                          reply_markup=reply_markup)
        return date

    def create_clock_message(self, bot, update):
        now = datetime.datetime.now()
        self.data[update.effective_chat.id] = [now.hour, now.minute]
        reply_markup = self.create_clock_markup(*self.data[update.effective_chat.id])
        if update.callback_query:
            bot.edit_message_text("Please choose the end date for your game.",
                                  reply_markup=reply_markup,
                                  chat_id = update.effective_chat.id,
                                  message_id = update.effective_message.message_id)
            return None
        update.effective_message.reply_text("Please choose the end date for your game.",
                                  reply_markup=reply_markup)

    def clock_handler(self, bot, update):
        data = update.callback_query.data
        cq = update.callback_query
        id = update.effective_chat.id
        reply_markup=None
        time = None
        cq.answer()
        if  'h' in data:
            if 'u' in data:
                self.data[id][0] += 1
                if self.data[id][0] >= 24:
                    self.data[id][0] = 0
            else:
                self.data[id][0] -= 1
                if self.data[id][0] <= -1:
                    self.data[id][0] = 23
            reply_markup = self.create_clock_markup(*self.data[id])
        elif 'm' in data:
            if 't' in data: #tens
                if 'u' in data: #up
                    self.data[id][1] += 10
                    if self.data[id][1] >= 60:
                        self.data[id][1] -= 60
                else: #down
                    self.data[id][1] -= 10
                    if self.data[id][1] < 0:
                        self.data[id][1] += 60
            else: #digits
                if 'u' in data: #up
                    self.data[id][1] += 1
                    if self.data[id][1] >= 60:
                        self.data[id][1] -= 60
                else: #down
                    self.data[id][1] -= 1
                    if self.data[id][1] < 0:
                        self.data[id][1] += 60
            reply_markup = self.create_clock_markup(*self.data[id])
        elif 'a' in data: #am/pm
            if 'u' in data:
                self.data[id][0] += 12
                if self.data[id][0] >= 24:
                    self.data[id][0] -= 24
            else:
                self.data[id][0] -= 12
                if self.data[id][0] <= -1:
                    self.data[id][0] += 24
            reply_markup = self.create_clock_markup(*self.data[id])
        elif 'done' in data:
            bot.edit_message_text("Time updated",
                                          chat_id=cq.message.chat_id,
                                          message_id=cq.message.message_id)
            time = datetime.datetime(1, 1, 1, hour=self.data[id][0], minute=self.data[id][1])
        bot.answer_callback_query(cq.id)
        if reply_markup:
            bot.edit_message_reply_markup(chat_id=cq.message.chat_id,
                                         message_id=cq.message.message_id,
                                         reply_markup=reply_markup)
        return time

    def create_calendar_markup(self, year, month):
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
        # return InlineKeyboardMarkup([[InlineKeyboardButton("This is a test", callback_data=' ')]])

    def create_clock_markup(self, hr, min):
        # apm :: True for AM, False for PM
        self.logger.debug("Creating clock for %d %d" % (hr, min))
        apm = hr < 12
        hr = hr if hr < 13 else hr - 12
        hr = hr if hr != 0 else 12
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
            InlineKeyboardButton(str(hr if hr < 13 else hr-12), callback_data=' '),
            InlineKeyboardButton(':', callback_data=' '),
            InlineKeyboardButton(str(int(min / 10)), callback_data=' '),
            InlineKeyboardButton(str(int(min % 10)), callback_data=' '),
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

    def now(self):
        return datetime.datetime.now()