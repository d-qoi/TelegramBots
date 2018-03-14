import logging
import functools

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Filters, CommandHandler, CallbackQueryHandler, MessageHandler
from cust_handlers.conversationhandler import ConversationHandler

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

def log(func):
    logger = logging.getLogger(func.__module__)

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

    def __init__(self, dp, MDB, logger=None):
        self.MDB = MDB
        self.logger = logger or logging.getLogger(__name__)
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
                "end_date": None,
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
        name = self.MDB.games.find_one({"group_id": update.message.chat.id}, {'game_name': 1})
        reply_text = "Main Menu for {}".format(name['game_name'])
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Set Rules", callback_data="games mm sr")],
            [InlineKeyboardButton("Set Admins", callback_data="games mm sa")],
            [InlineKeyboardButton("Add Channel", callback_data="games mm ac")],
            [InlineKeyboardButton("Create Join Prompt", callback_data="games mm jp")],
            [InlineKeyboardButton("Set End Time", callback_data="games mm et")],
            [InlineKeyboardButton("Change Game Title", callback_data="games mm gt")]
        ])
        update.message.reply_text(reply_text, reply_markup=keyboard, quote=False)
        return self.MAIN_MENU_RESPONSE

    @log
    def main_menu_response(self, bot, update, groups=None):
        group_id = update.effective_chat.id
        admins = self.MDB.findOne({'group_id':group_id}, {'admins':1})
        if update.effective_user.id not in admins:
            return
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
            update.callback_query.answer(text="Not implemented yet")
            return self.MAIN_MENU_RESPONSE
            pass
        elif groups[0] == 'gt':
            reply_text = "Please send me a new title for the game (under 50 characters)"
            update.message.reply_text(reply_text, reply_markup=None, quote=False)
            return self.SET_NAME_RESPONSE
        self.logger.warning("Unknown group called for main menu: %d", groups[0])
        return self.MAIN_MENU_RESPONSE

    @log
    def set_chanel_prompt(self, bot, update):
        pass

    @log
    def set_name_response(self, bot, update):
        admins = self.MDB.findOne({'group_id': update.effective_chat.id}, {'admins': 1})
        if update.effective_user.id not in admins:
            return
        text = update.message.text[:51]
        self.MDB.games.update_one({'group_id': update.effective_chat.id},
                                   {'$set':{'game_name':text}})
        return self.main_menu_prompt(bot, update)

    @log
    def set_rules_response(self, bot, update):
        admins = self.MDB.findOne({'group_id': update.effective_chat.id}, {'admins': 1})
        if update.effective_user.id not in admins:
            return
        self.MDB.games.update_one({'group_id': update.effective_chat.id},
                                   {'$set': {'rules': update.message.text}})
        return self.main_menu_prompt(bot, update)

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

    @log
    def calendar_call_back(self, ):