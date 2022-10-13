
from discord import Intents
from discord.ext.commands import Bot

class BotEssentials():

    intents: Intents = None
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