def sendMessagePOC(bot,update):
    new_message = bot.forward_message(chat_id=update.message.chat.id,
                                      from_chat_id=update.message.chat.id,
                                      message_id=update.message.message_id)
    update.message.reply_text("oldID %s, newID %s" % (update.message.message_id, new_message.message_id))

'''
This code will prove that the message that the bot.forward_message, or any of the bot.***_message commands,
or similar that return a message, will return the message that the bot sent.

This is very useful in the case where you will want to edit that message, or something.
'''


# Checks to see if a command is a valid command for the bot, aka @botname exists or doesn't
def checkValidCommand(text, username):
    text = text.split()[0]
    try:
        at = text.index('@')+1
        if text[at:] == username:
            return True
        return False
    except ValueError:
        return True
    
    if not checkValidCommand(update.message.text, bot.username):
        return
        