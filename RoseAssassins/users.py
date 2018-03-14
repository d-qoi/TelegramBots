import logging
import functools

from cust_handlers.conversationhandler import ConversationHandler
from telegram.ext import MessageHandler, CommandHandler, CallbackQueryHandler, Filters
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from gridfs import GridFS

def log(func):
    logger = logging.getLogger(func.__module__)

    @functools.wraps(func)
    def decorator(self, *args, **kwargs):
        logger.debug("Called: %s", func.__name__)
        return func(self, *args, **kwargs)
    return decorator

class Users(object):
    # States

    CREATE_BIO_RESPONSE     = 100
    CHOOSE_ACTIVE_GAME      = 101
    START_UP_NAME_RESPONSE  = 1
    START_UP_BIO_RESPONSE   = 2
    START_UP_PHOTO_RESPONSE = 3
    START_UP_GAME_CHOICE    = 4
    MAIN_MENU_RESPONSE      = 10
    EDIT_NAME_RESPONSE      = 20
    EDIT_BIO_RESPONSE       = 21
    EDIT_PHOTO_RESPONSE     = 22


    def __init__(self, dp, MDB, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.MDB = MDB
        self.grid = GridFS(MDB)
        self.back_button_handler = CallbackQueryHandler(self.return_to_main_menu, pattern="user btm")
        self.main_conversation = ConversationHandler(
            entry_points=[
                CommandHandler(['start', 'create_profile'],
                               self.initial_call,
                               filters=Filters.private),
                CommandHandler('main_menu', self.return_to_main_menu,
                               filters=Filters.private)
            ],
            states={
                self.CHOOSE_ACTIVE_GAME: [
                    CallbackQueryHandler(self.choose_active_game, pattern="user gc (-?[0-9]+)", pass_groups=True)
                ],
                self.START_UP_GAME_CHOICE: [
                    CallbackQueryHandler(self.start_up_game_choice, pattern="user gc (-?[0-9]+)", pass_groups=True)
                ],
                self.START_UP_NAME_RESPONSE: [
                    MessageHandler(Filters.text, self.startup_name_response)
                ],
                self.START_UP_BIO_RESPONSE: [
                    MessageHandler(Filters.text, self.startup_bio_response)
                ],
                self.START_UP_PHOTO_RESPONSE: [
                    MessageHandler(Filters.photo | Filters.document, self.startup_photo_response)
                ],
                self.MAIN_MENU_RESPONSE: [
                    CallbackQueryHandler(self.main_menu_response, pattern="user mm ([a-z][a-z])", pass_groups=True)
                ],
                self.EDIT_NAME_RESPONSE: [
                    MessageHandler(Filters.text, self.edit_name_response),
                    self.back_button_handler
                ],
                self.EDIT_BIO_RESPONSE: [
                    MessageHandler(Filters.text, self.edit_bio_response),
                    self.back_button_handler
                ],
                self.EDIT_PHOTO_RESPONSE: [
                    MessageHandler(Filters.photo | Filters.document, self.edit_photo_response),
                    self.back_button_handler
                ]
            },
            fallbacks=[
                CommandHandler(['start', 'create_profile'],
                               self.initial_call,
                               filters=Filters.private),
                CommandHandler('main_menu', self.return_to_main_menu,
                               filters=Filters.private)
            ],
            collection=MDB.users_conversation
        )
        dp.add_handler(self.main_conversation)

    @log
    def __create_game_list(self, id):
        games = self.MDB.users.find_one({'user_id':id}, {'games':1})
        self.logger.debug("Games for user: %s", games)
        if (not games) or ('games' not in games):
            return None
        ret = []
        for game in games['games']:
            gd = self.MDB.games.find_one({'group_id':game['id']},{'game_name':1, 'state':1})
            ret.append(
                [InlineKeyboardButton("{} ({}, profile: {})".format(gd['game_name'],
                                                                    gd['state'],
                                                                    game['state'] if 'state' in game else 'not created'),
                                      callback_data='user gc {}'.format(game['id']))])
        return ret

    @log
    def __create_main_menu(self, id):
        active_game = self.MDB.users.find_one({'user_id':id}, {'active_game':1})['active_game']
        game = self.MDB.games.find_one({'group_id':active_game}, {"state":1, "game_name":1, "admins":1, "chats":1})
        ret = [
            [InlineKeyboardButton("Edit Name", callback_data='user mm en'),
             InlineKeyboardButton("Edit Bio", callback_data='user mm eb'),
             InlineKeyboardButton("Edit Pic", callback_data='user mm ep')],
            [InlineKeyboardButton("Contact Admins", callback_data='users mm ca')]
        ]
        if game['state'] == "running":
            ret.append([
                InlineKeyboardButton("Target Assassinated!", callback_data='user mm ta')
            ])
        if 'chats' in game and len(game['chats']):
            ret.append([
                InlineKeyboardButton("Check Admin Chats", callback_data='admin mm cc')
            ])
        ret.append([InlineKeyboardButton("Change Active Game", callback_data='user mm cg')])
        ret.append([InlineKeyboardButton("Refresh Menu", callback_data='user mm rf')])
        return ret

    @log
    def __get_largest_photos(self, photosize):
        temp = photosize[0]
        for photo in photosize:
            if photo.file_size > temp.file_size:
                temp = photo
        return temp

    @log
    def return_to_main_menu(self, bot, update):
        active_game = self.MDB.users.find_one({'user_id': update.effective_user.id}, {'active_game': 1})['active_game']
        game = self.MDB.games.find_one({'group_id': active_game}, {"state": 1, "game_name": 1})
        reply_text = "Main Menu for {}".format(game['game_name'])

        reply_markup = InlineKeyboardMarkup(self.__create_main_menu(update.effective_user.id))
        update.effective_message.reply_text(reply_text, reply_markup=reply_markup)

        return self.MAIN_MENU_RESPONSE

    @log
    def main_menu_response(self, bot, update, groups):
        self.logger.debug("Groups: %s", groups[0])
        cq = update.callback_query
        if groups[0] == 'en': # edit name
            cq.edit_message_text("Please send me your new Name. (50 character limit)", reply_markup=None)
            return self.EDIT_NAME_RESPONSE
        elif groups[0] == 'eb': # edit bio
            cq.edit_message_text("Please send me your new Bio.", reply_markup=None)
            return self.EDIT_BIO_RESPONSE
        elif groups[0] == 'ep': # edit picture
            cq.edit_message_text("Please send me your new Picture.", reply_markup=None)
            return self.EDIT_PHOTO_RESPONSE
        elif groups[0] == 'ca': # contact admins
            pass
        elif groups[0] == 'ta': # target assassinated
            # This will prompt them to send a message to the target, this can be anything, the bot will just forward the message.
            pass
        elif groups[0] == 'cg': # change game
            reply_markup = InlineKeyboardMarkup(self.__create_game_list(update.effective_user.id))
            reply_text = "Please choose a game!"
            cq.edit_message_text(reply_text, reply_markup=reply_markup)
            return self.CHOOSE_ACTIVE_GAME
        elif groups[0] == 'rf':
            cq.edit_message_text("Refreshing Main Menu, Please hold.", reply_text=None)
            return self.return_to_main_menu(bot, update)
        self.logger.warning("Unknown group called")
        return self.MAIN_MENU_RESPONSE

    @log
    def edit_name_response(self, bot, update):
        text = update.effective_message.text.strip()[:51]
        
        active_game = self.MDB.users.find_one({'user_id': update.effective_user.id}, {'active_game': 1})['active_game']

        self.MDB.users.update_one({'user_id': update.effective_user.id},
                                  {'$set': {'games.$[elem].name': text}},
                                  array_filters=[{'elem.id': active_game}])
        
        return self.return_to_main_menu(bot, update)

    @log
    def edit_bio_response(self, bot, update):
        text = update.effective_message.text.strip()

        active_game = self.MDB.users.find_one({'user_id': update.effective_user.id}, {'active_game': 1})[
            'active_game']

        self.MDB.users.update_one({'user_id': update.effective_user.id},
                                  {'$set': {'games.$[elem].bio': text}},
                                  array_filters=[{'elem.id': active_game}])

        return self.return_to_main_menu(bot, update)

    @log
    def edit_photo_response(self, bot, update):
        if not update.effective_message.photo:
            update.effective_message.reply_text("Please send me the picture as a picture, not as a file.")
            return self.EDIT_PHOTO_RESPONSE
        active_game = self.MDB.users.find_one({'user_id': update.effective_user.id}, {'active_game': 1})['active_game']

        pic = self.__get_largest_photos(update.effective_message.photo)
        uid = update.effective_user.id
        with self.grid.new_file(filename="profile_%d.png"%(uid)) as gridIn:
            bot.get_file(pic.file_id).download(out=gridIn)

            self.MDB.users.update_one({'user_id': update.effective_user.id},
                                      {'$set': {'games.$[elem].photo': gridIn._id}},
                                      array_filters=[{'elem.id': active_game}])

        return self.return_to_main_menu(bot, update)

    @log
    def choose_active_game(self, bot, update, groups=None):
        new_game = self.MDB.games.find_one({'group_id':int(groups[0])}, {"game_name":1})
        if not new_game:
            self.logger.error("Game not found, something went wrong: %d", groups[0])
            reply_text = "Unfortunately the game was not found for group id: {}.\n\n".format(groups[0])
            reply_text += "Please ask about this in the game chat.\n\n"
            reply_text += "For now, choose a new game."
            reply_markup = InlineKeyboardMarkup(self.__create_game_list(update.effective_user.id))
            update.callback_query.edit_message_text(reply_text, reply_markup=reply_markup)
            return self.CHOOSE_ACTIVE_GAME

        reply_text = "Setting game to {}.".format(new_game['game_name'])
        self.MDB.users.update_one({'user_id':update.effective_user.id}, {'$set':{'active_game':int(groups[0])}})
        update.callback_query.edit_message_text(reply_text, reply_markup=None)
        return self.return_to_main_menu(bot, update)

    @log
    def initial_call(self, bot, update):
        games = list(self.MDB.games.find({"users.id":update.effective_user.id,
                                          "users.state":'new'}))
        user = self.MDB.users.find_one({'user_id': update.effective_user.id})
        if not games or not user:
            reply_text = "Please register with a game or create one before creating your profile!"
            reply_text += "\n\nOnce you have registered with a game, you can come back here and call /create_profile to create your profile for that game!"
            update.effective_message.reply_text(reply_text)
            return ConversationHandler.END

        reply_markup = self.__create_game_list(update.effective_user.id)

        reply_markup = InlineKeyboardMarkup(reply_markup)
        reply_text = "Please choose which game you want to create a profile for."
        update.message.reply_text(reply_text, reply_markup=reply_markup)
        return self.START_UP_GAME_CHOICE

    @log
    def start_up_game_choice(self, bot, update, groups=None): #receives a callback query and prompts for a name
        update.callback_query.answer(reply_markup=None)
        game_name = self.MDB.games.find_one({'group_id':int(groups[0])}, {'game_name':1})
        if not game_name:
            reply_text = "Unfortunately the game was not found for group id: {}.\n\n"
            reply_text += "Please ask about this in the game chat.\n\n".format(groups[0])
            reply_text += "For now, choose a new game."
            reply_markup = InlineKeyboardMarkup(self.__create_game_list(update.effective_user.id))
            update.callback_query.edit_message_text(reply_text, reply_markup=reply_markup)
            return self.START_UP_GAME_CHOICE
        self.MDB.users.update_one({'user_id':update.effective_user.id}, {'$set':{'active_game':int(groups[0])}})

        reply_text = "You are now creating a profile for {}! This can be edited later.\n\n".format(game_name['game_name'])
        reply_text += "Please send me your Name (limit of 50 characters). This should be something that the other players can identify you by outside of Telegram."
        reply_text += "\n\nPlease check the rules of your game to see if there are any requirements for your name."

        update.effective_message.reply_text(reply_text, reply_markup=None)
        return self.START_UP_NAME_RESPONSE

    @log
    def startup_name_response(self, bot, update): # receives a callback query from
        reply_text = "Now please send me your Bio. This will be given to you assassin, so make it unique!\n\n"
        reply_text += "Please check the rules of your game to see if there is anything specific that you should include."

        text = update.effective_message.text.strip()[:51]
        active_game = self.MDB.users.find_one({'user_id':update.effective_user.id}, {'active_game':1})['active_game']

        self.MDB.users.update_one({'user_id':update.effective_user.id},
                                  {'$set':{'games.$[elem].name': text}},
                                  array_filters=[{'elem.id':active_game}])

        update.effective_message.reply_text(reply_text)
        return self.START_UP_BIO_RESPONSE

    @log
    def startup_bio_response(self, bot, update):
        reply_text = "Now please send me a Picture of you. This should be a recent picture, preferably taken just after receiving this message.\n"
        reply_text += "This picture should be a good representation of who you are to your assassin. Take the picture as if you were receiving it as the picture for your next target.\n\n"
        reply_text += "Please check the rules of your game to see if there is anything specific that you should do for this picture."

        text = update.effective_message.text.strip()
        active_game = self.MDB.users.find_one({'user_id': update.effective_user.id}, {'active_game': 1})['active_game']

        self.MDB.users.update_one({'user_id': update.effective_user.id},
                                  {'$set': {'games.$[elem].bio': text}},
                                  array_filters=[{'elem.id': active_game}])

        update.effective_message.reply_text(reply_text)
        return self.START_UP_PHOTO_RESPONSE

    @log
    def startup_photo_response(self, bot, update):
        reply_text = "Your profile has been created! Welcome to your main menu for {}.\n\n"
        reply_text += "More options will be available once the game starts!\n\n"
        reply_text += "New users will be unable to join once the Game starts, so tell everyone who want's to play to join in now!"

        active_game = self.MDB.users.find_one({'user_id': update.effective_user.id}, {'active_game': 1})['active_game']
        if not update.effective_message.photo:
            update.effective_message.reply_text("Please send me the picture as a picture, not as a file.")
            return self.START_UP_PHOTO_RESPONSE
        pic = self.__get_largest_photos(update.effective_message.photo)
        uid = update.effective_user.id
        with self.grid.new_file(filename="profile_%d.png"%(uid)) as gridIn:
            bot.get_file(pic.file_id).download(out=gridIn)

            self.MDB.users.update_one({'user_id': update.effective_user.id},
                                      {'$set': {'games.$[elem].photo': gridIn._id,
                                                'state': 'created'}},
                                      array_filters=[{'elem.id': active_game}])

        update.effective_message.reply_text(reply_text)
        return self.return_to_main_menu(bot, update)
