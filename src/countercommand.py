from abc import ABC, abstractmethod

import discord
from discord.ext import commands
from discord import app_commands, Interaction, ButtonStyle

from settings import SharedVariables

class CounterButton(discord.ui.Button, ABC):

    async def callback(self, interaction: Interaction):
        self.counter()

        await interaction.response.edit_message(
            content="Let's count! {}".format(SharedVariables.counter),
            view=MyCounter()
        )
    
    @abstractmethod
    def counter(self):
        pass

class PlusOneButton(CounterButton):

    def counter(self):
        SharedVariables.counter += 1

class MinusOneButton(CounterButton):

    def counter(self):
        SharedVariables.counter -= 1

class ResetButton(CounterButton):

    def counter(self):
        SharedVariables.counter = 0

class MyCounter(discord.ui.View):

    def __init__(self):
        super().__init__()
        self.add_item(PlusOneButton( 
            style=ButtonStyle.blurple,
            custom_id="button1",
            label="+1",
            emoji="🚀",
        ))
        self.add_item(ResetButton(
            style=ButtonStyle.red,
            custom_id="button2",
            label="Reset",
            disabled=(abs(SharedVariables.counter) < 5),
            emoji="🐺",
        ))
        self.add_item(MinusOneButton(
            style=ButtonStyle.green,
            custom_id="button3",
            label="-1",
            emoji="😄",
        ))


class CounterCommand(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
      self.bot: commands.Bot = bot

    @app_commands.command(name="count", description="Count the numbers!")
    async def count(self, interaction: Interaction):
        print("[LOG] Counting with {}!".format(interaction.user))
        await interaction.response.send_message(
            content="Let's count! {}".format(SharedVariables.counter),
            view=MyCounter()
        )

async def setup(bot: commands.Bot) -> None:
  await bot.add_cog(CounterCommand(bot))