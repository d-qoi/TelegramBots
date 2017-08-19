'''
Created on May 11, 2017

@author: hirschag
'''

import datetime

class requesthistory(object):

    def __init__(self, *tracking):
        for track in tracking:
            self.__dict__[track] = self.monitor()
#     
    class monitor(object):
        def __init__(self):
            self.history = list()
         
        def post(self):
            self.history.append(datetime.datetime.now())
             
        def getCountHour(self):
            self.prune()
            return len(self.history)
             
        def getCountMinute(self):
            self.prune()
            now = datetime.datetime.now()
            return len([i for i in self.history if abs((now - i).total_seconds()) < 60])
             
        def getCountSeconds(self):
            self.prune()
            now = datetime.datetime.now()
            return len([i for i in self.history if abs((now - i).total_seconds()) < 1])
         
        def prune(self):
            now = datetime.datetime.now()
            self.history = [i for i in self.history if abs((now - i).total_seconds()) < 3600]