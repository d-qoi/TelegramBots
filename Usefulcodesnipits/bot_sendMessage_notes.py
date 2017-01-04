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
