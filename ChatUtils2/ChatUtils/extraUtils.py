'''
Created on Jan 19, 2017

@author: hirschag
'''    
    
import datetime
    
    
def checkTypeGroup(update):
    return (update.message.chat.type == 'group' or update.message.chat.type == 'supergroup')


def checkTypePrivate(update):
    return update.message.chat.type == 'private'


def isTimeString(toCheck):
    try:
        datetime.datetime.strptime(toCheck, '%I:%M %p')
        return True
    except ValueError:
        return False
    

def isDateString(toCheck):
    try:
        eventDate = datetime.datetime.strptime(toCheck, '%m/%d/%Y')
        now = datetime.datetime.now()
        currDate = datetime.datetime.strptime('%d/%d/%d' %(now.month, now.day, now.year), '%m/%d/%Y')
        return eventDate >= currDate
    except ValueError:
        return False
    
    
def checkValidCommand(text, username):
    text = text.split()[0]
    try:
        at = text.index('@')+1
        if text[at:] == username:
            return True
        return False
    except ValueError:
        return True
    
    
def createUserDict(from_user):
    userDict = dict()
    userDict['username'] = from_user.username
    userDict['name'] = from_user.first_name + " " + from_user.last_name
    userDict['id'] = from_user.id
    return userDict

def getUserName(from_user):
    if from_user.username:
        return '@' + from_user.username
    return "%s %s" % (from_user.first_name, from_user.last_name)