import logging
import functools

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Filters, CommandHandler, CallbackQueryHandler, MessageHandler
from cust_handlers.conversationhandler import ConversationHandler
from date_time_helper import DateTimeHelper

"""
game_data_dict = {
    "game_name":None,
    "chanel":None,
    "group_id":None,
    "rules": None,
    "end_date": None,
    "creator_id": None,
    "creator_username": None,
    "admins":[None],
    "state":"New"
    "users":[{"id":None, "target":None, "points":None, "state":None}]
}
"""

def restrict(func):
    @functools.wraps(func)
    def decorator(self, bot, update, *args, **kwargs):
        admins = self.MDB.games.find_one({'group_id': update.effective_chat.id}, {'admins': 1})
        if update.effective_user.id not in admins['admins']:
            return
        return func(self, bot, update, *args, **kwargs)
    return decorator

def log(func, logger=None):
    logger = logger or logging.getLogger(func.__module__)

    @functools.wraps(func)
    def decorator(self, *args, **kwargs):
        logger.debug("Called: %s", func.__name__)
        return func(self, *args, **kwargs)
    return decorator

class Games(object):
    MDB = None

    MAIN_MENU_RESPONSE = 1
    SET_RULES_RESPONSE = 2
    SET_NAME_RESPONSE = 3

    SET_DATETIME = 4

    logger=None

    def __init__(self, dp, MDB, logger=None):
        self.MDB = MDB
        self.logger = logger or logging.getLogger(__name__)
        self.DTH = DateTimeHelper(logger=logger, collection=MDB.calendar_conversations)
        self.main_conversation = ConversationHandler(
            per_user=False, per_chat=True,
            entry_points=[
                CommandHandler("create_game", self.create_game, filters=Filters.group)
            ],
            states={
                self.MAIN_MENU_RESPONSE:[
                    CallbackQueryHandler(self.main_menu_response, pattern="games mm ([a-z][a-z])", pass_groups=True)
                ],
                self.SET_RULES_RESPONSE:[
                    MessageHandler(Filters.text, self.set_rules_response)
                ],
                self.SET_NAME_RESPONSE: [
                    MessageHandler(Filters.text, self.set_name_response)
                ],
                self.SET_DATETIME: [
                    CallbackQueryHandler(self.set_datetime, pattern="(cal|clk)\-.+", pass_groups=True)
                ]
            },
            fallbacks=[
                CallbackQueryHandler(self.join_game, pattern='games join (-?[0-9]+)', pass_groups=True),
                CommandHandler('main_menu', self.main_menu_prompt)
            ],
            collection=MDB.group_conversation
        )
        dp.add_handler(self.main_conversation)

    @log
    def getAdmins(self, chat):
        ids = []
        admins = chat.get_administrators()
        for admin in admins:
            if not admin.user.is_bot:
                ids.append(admin.user.id)
        return ids

    @log
    def create_game(self, bot, update): # command only
        chat_member = bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if chat_member.status not in ['administrator', 'creator']:
            return

        reply_text = "Game created for %s"%(update.message.chat.title)

        result = self.MDB.games.find_one({"group_id":update.message.chat.id})
        if result:
            reply_text = "Game was already created for this group"
        else:
            game_data_dict = {
                "game_name": update.message.chat.title,
                "chanel_id": None,
                "group_id": update.message.chat.id,
                "rules": "Tag a your target and use the menu to signal your kill!",
                "end_date": self.DTH.now(),
                "creator_id": update.message.from_user.id,
                "creator_name": update.message.from_user.username,
                "admins":[],
                "state":"new",
                "users": [{
                    "id": update.message.from_user.id,
                    "target": None,
                    "points": 0,
                    "state": "new",
                }]
            }
            self.MDB.games.insert(game_data_dict)
            ids = self.getAdmins(update.effective_chat)
            self.MDB.games.update_one({'group_id': update.effective_chat.id},
                                      {'$set': {'admins': ids}})
        update.message.reply_text(reply_text, quote=False)
        return self.main_menu_prompt(bot, update)

    @log
    def main_menu_prompt(self, bot, update):
        name = self.MDB.games.find_one({"group_id": update.effective_chat.id}, {'game_name': 1})
        reply_text = "Main Menu for {}".format(name['game_name'])
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("Create Join Prompt", callback_data="games mm jp")],
            [InlineKeyboardButton("Set Rules", callback_data="games mm sr")],
            [InlineKeyboardButton("Set Admins", callback_data="games mm sa")],
            [InlineKeyboardButton("Add Channel", callback_data="games mm ac")],
            [InlineKeyboardButton("Change Game Title", callback_data="games mm gt")],
            [InlineKeyboardButton("Set End Time", callback_data="games mm et"),
             InlineKeyboardButton("Set End Date", callback_data="games mm ed")]
        ])
        if update.callback_query:
            update.effective_message.edit_text(reply_text, reply_markup=reply_markup)
        else:
            update.effective_message.reply_text(reply_text, reply_markup=reply_markup, quote=False)
        return self.MAIN_MENU_RESPONSE

    @log
    @restrict
    def main_menu_response(self, bot, update, groups=None):
        group_id = update.effective_chat.id
        # admins = self.MDB.findOne({'group_id':group_id}, {'admins':1})
        # if update.effective_user.id not in admins:
        #     return
        self.logger.debug("groups: %s", groups[0])
        if groups[0] == 'sr':
            reply_text = "Please send me the rules for the game."
            update.callback_query.edit_message_text(reply_text, reply_markup=None, quote=False)
            update.callback_query.answer()
            return self.SET_RULES_RESPONSE

        elif groups[0] == 'sa':
            ids = self.getAdmins(update.effective_chat)
            self.MDB.games.update_one({'group_id': group_id},
                                       {'$set':{'admins': ids}})
            update.callback_query.answer(text="Updated admins to current chat admins.")
            return self.MAIN_MENU_RESPONSE

        elif groups[0] == 'ac':
            update.callback_query.answer(text="Not implemented yet")
            return self.MAIN_MENU_RESPONSE

        elif groups[0] == 'jp':
            update.callback_query.edit_message_text("Please pin this message.")
            reply_text = "If you would like to join the game, click this! Or send /create_profile to the bot!"
            reply_markup = InlineKeyboardMarkup([[
                InlineKeyboardButton('Click this to join this game!',
                                     callback_data='games join {}'.format(update.effective_chat.id))
            ]])
            update.effective_message.reply_text(reply_text, reply_markup=reply_markup, quote=False)
            return self.MAIN_MENU_RESPONSE

        elif groups[0] == 'et':
            self.DTH.create_clock_message(bot, update)
            return self.SET_DATETIME
        elif groups[0] == 'ed':
            self.DTH.create_calendar_message(bot, update)
            return self.SET_DATETIME

        elif groups[0] == 'gt':
            reply_text = "Please send me a new title for the game (under 50 characters)"
            update.effective_message.reply_text(reply_text, reply_markup=None, quote=False)
            return self.SET_NAME_RESPONSE
        self.logger.warning("Unknown group called for main menu: %d", groups[0])
        return self.MAIN_MENU_RESPONSE

    @log
    def set_chanel_prompt(self, bot, update):
        pass

    @log
    @restrict
    def set_name_response(self, bot, update):
        # admins = self.MDB.findOne({'group_id': update.effective_chat.id}, {'admins': 1})
        # if update.effective_user.id not in admins:
        #     return
        text = update.message.text[:51]
        self.MDB.games.update_one({'group_id': update.effective_chat.id},
                                   {'$set':{'game_name':text}})
        return self.main_menu_prompt(bot, update)

    @log
    @restrict
    def set_rules_response(self, bot, update):
        # admins = self.MDB.findOne({'group_id': update.effective_chat.id}, {'admins': 1})
        # if update.effective_user.id not in admins:
        #     return
        self.MDB.games.update_one({'group_id': update.effective_chat.id},
                                   {'$set': {'rules': update.message.text}})
        return self.main_menu_prompt(bot, update)

    @log
    @restrict
    def set_datetime(self, bot, update, groups=None):
        # admins = self.MDB.findOne({'group_id': update.effective_chat.id}, {'admins': 1})
        # if update.effective_user.id not in admins:
        #     return
        resp = None
        group_id = update.effective_chat.id
        end_datetime = self.MDB.games.find_one({'group_id':group_id}, {"end_date":1})['end_date']
        if 'cal' in groups[0]:
            resp = self.DTH.calendar_handler(bot, update)
            if resp:
                end_datetime = end_datetime.replace(year=resp.year, month=resp.month, day=resp.day)
        else:
            resp = self.DTH.clock_handler(bot, update)
            if resp:
                end_datetime = end_datetime.replace(hour=resp.hour, minute=resp.minute)
        if resp:
            self.MDB.games.update({'group_id':group_id}, {'$set':{"end_date":end_datetime}})
            return self.main_menu_prompt(bot, update)
        return self.SET_DATETIME

    @log
    def join_game(self, bot, update, groups=None):
        user = update.effective_user
        created = self.MDB.games.find_one({'group_id':int(groups[0]), 'users.id':update.effective_user.id},
                                          {'users.id':1})
        if created:
            bot.answerCallbackQuery(update.callback_query.id, text="You have already created a profile")
            self.MDB.users.update_one({"user_id": user.id},
                                      {'$addToSet': {
                                          'games': {'id': int(groups[0])}
                                      }}, upsert=True)
            return
        self.MDB.games.update_one({'group_id':int(groups[0])},
                                  {'$push':{
                                      "users":{
                                          "id": user.id,
                                          "target": None,
                                          "points": 0,
                                          "state": "new"
                                      }
                                   }})
        self.MDB.users.update_one({"user_id": user.id},
                                  {'$addToSet': {
                                      'games': {'id': int(groups[0]), 'state':'not created'}
                                  }}, upsert=True)
        self.logger.debug(bot.username)
        bot.answerCallbackQuery(update.callback_query.id, url="https://t.me/{}?start=True".format(bot.username))
        #update.callback_query.answer(text="test",)