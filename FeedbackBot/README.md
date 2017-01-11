# FeedbackBot

## Created using the [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) and [MongoDB](https://www.mongodb.com)

## What does this bot do?

This bot will act as a middle man for a group to provide feedback for a chat(s) and let admins reply to that feedback through the bot.

## Requirements
* MongoDB version 3.4 or later
* Python 3.x
* python-telegram-bot
* pymongo

## Starting the bot

You need to call the bot and pass in the auth key you received from @botfather on telegram

## Commands
* /start or /cancel: Restarts the current instance, and returns to the initial prompt. Use when the bot is acting up.
* /info: Prints info, can be set through initial arguments
* /help: Prints basic help

## How to use this bot

This bot is intended to be used by a group or individual that is managing a few chats and channels.

You will need to host an instance of this bot through your own key on your own hardware.

Once you've created the bot, add it to the groups that you want, and then, in @botfather, stop allowing users to add it to groups.

It is recommended that you add the commands listed above to the bot through @botfather as well.

If you are going to run this bot in your chats, please add `Creator: @YTKileroy` to either the bot's discription or about.