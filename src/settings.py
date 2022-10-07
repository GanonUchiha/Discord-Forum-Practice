
from discord import Intents, Client
from discord.ext.commands import Bot

class BotEssentials():

    intents: Intents = None
    client: Client = None
    bot: Bot = None

    @classmethod
    def setup_bot(self):
        '''
        Setting up a bot (interactions based on commands)
        '''
        intents = Intents.default()
        intents.message_content = True
        intents.presences = True
        intents.members = True

        bot = Bot(command_prefix='!', intents=intents)

        BotEssentials.intents = intents
        BotEssentials.bot = bot

    @classmethod
    def setup_client(self):
        '''
        Setting up a client (interaction based on messages)
        '''
        intents = Intents.default()
        intents.message_content = True
        intents.presences = True
        intents.members = True

        client = Client(intents=intents)

        BotEssentials.client = client
        BotEssentials.intents = intents

class SharedVariables():

    counter: int = 0