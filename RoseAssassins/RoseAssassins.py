
import logging
import argparse

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG) # To make sure that it is just pushing modism debug into the log
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

from telegram.ext import Updater
from pymongo import MongoClient

from games import Games
from users import Users


AUTHTOKEN = None
MCLIENT = None
MDB = None
MI = None


def startFromCLI():
    global AUTHTOKEN, MCLIENT, MDB, GRID
    parser = argparse.ArgumentParser()
    parser.add_argument('auth', type=str, help="The Auth Token given by Telegram's @botfather")
    parser.add_argument('-l','--llevel', default='info', choices=['debug','info','warn','none'], help='Logging level for the logger, default = info')
    logLevel = {'none':logging.NOTSET,'debug':logging.DEBUG,'info':logging.INFO,'warn':logging.WARNING}
    parser.add_argument('-muri','--MongoURI', default='mongodb://localhost:27017', help="The MongoDB URI for connection and auth")
    parser.add_argument('-mdb','--MongoDB', default='roseassassins', help="The MongoDB Database that this will use")
    args = parser.parse_args()

    logger.setLevel(logLevel[args.llevel])
    AUTHTOKEN = args.auth
    MCLIENT = MongoClient(args.MongoURI)
    MDB = MCLIENT[args.MongoDB]

def main():
    try:
        serverInfo = MCLIENT.server_info()
        logger.info("Connected to Mongo Server: %s." % serverInfo)
    except:
        logger.error("Could not connect to the Mongo Server.")
        raise
    updater = Updater(AUTHTOKEN)
    logger.info("Passed Auth")
    dp = updater.dispatcher

    game_state = Games(dp, MDB)
    user_state = Users(dp, MDB)


    updater.start_polling()
    logger.info("Starting polling")
    updater.idle()


if __name__ == '__main__':
    startFromCLI()
    main()
