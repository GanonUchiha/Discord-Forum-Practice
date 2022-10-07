from typing import Union, List
from abc import ABC, abstractmethod

import discord
from discord.ext import commands
from discord import app_commands, AppCommandType, Interaction, ButtonStyle
from discord.ext.commands import Bot
from discord.app_commands import CommandTree, ContextMenu, Command, Group, describe

from settings import SharedVariables

class BasicCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
      self.bot: commands.Bot = bot

    @commands.hybrid_command(name="hello")
    async def ping_command(self, ctx: commands.Context) -> None:
        """
        Say Hello!

        This command is actually used as an app command AND a message command.
        This means it is invoked with `!hello` and `/hello` (once synced, of course).
        """
        print("[LOG] Pinged by {}".format(ctx.author))
        await ctx.send("World!")
        
    @app_commands.command(name="commands", description="Get the list of all commands")
    async def get_commands_list(self, interaction: Interaction):
        print("[LOG] {} requested a list of commands".format(interaction.user))

        cmd_lst: List[Union[ContextMenu, Command, Group]] = interaction.client.tree.get_commands(type=AppCommandType.chat_input)
        name_lst = [command.name for command in cmd_lst]
        msg = "List of commands:\n{}".format("\n".join(name_lst))
        await interaction.response.send_message(msg, ephemeral=True,)

    @commands.hybrid_group(name="parent", description="Parent command, does nothing atm")
    async def parent_command(self, ctx: commands.Context) -> None:
        """
        We even have the use of parents. This will work as usual for ext.commands but will be un-invokable for app commands.
        This is a discord limitation as groups are un-invokable.
        """
        pass # nothing we want to do in here, I guess!
    
    @parent_command.command(name="sub", description="Subcommand, does nothing atm")
    async def sub_command(self, ctx: commands.Context, argument: str) -> None:
        """
        This subcommand can now be invoked with `?parent sub <arg>` or `/parent sub <arg>` (once synced).
        """
        await ctx.send(f"Hello, you sent {argument}!")
    
async def setup(bot: commands.Bot) -> None:
  await bot.add_cog(BasicCommands(bot))