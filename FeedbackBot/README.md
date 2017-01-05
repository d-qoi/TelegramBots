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
