from typing import Optional, Literal
import asyncio

from discord import Object as DiscordObject, HTTPException
from discord.ext.commands import Context, Greedy, Bot
from discord.ext.commands import guild_only as commands_guild_only
from discord.ext.commands import is_owner as commands_is_owner
from discord.ext.commands import has_guild_permissions
from discord.app_commands import CommandTree

from mycredentials import BOT_ID, BOT_TOKEN
from settings import BotEssentials
import basiccommands
import forumcommands
import countercommand

# Setting up the bot
BotEssentials.setup_bot()
bot = BotEssentials.bot

@BotEssentials.bot.event
async def on_ready():
    print(f'We have logged in as {BotEssentials.bot.user}')

@BotEssentials.bot.hybrid_command(description="Ping Pong!")
async def ping(ctx: Context):
    await ctx.send('Pong!')

@BotEssentials.bot.command(description="Sync slash commands")
@commands_guild_only()
@has_guild_permissions(manage_guild=True)
async def sync(ctx: Context, guilds: Greedy[DiscordObject], spec: Optional[Literal["~", "*", "^"]] = None) -> None:
    '''
    Code Reference: https://gist.github.com/AbstractUmbra/a9c188797ae194e592efe05fa129c57f?permalink_comment_id=4121434#gistcomment-4121434

    !sync -> global sync
    !sync ~ -> sync current guild
    !sync * -> copies all global app commands to current guild and syncs
    !sync ^ -> clears all commands from the current guild target and syncs (removes guild commands)
    !sync id_1 id_2 -> syncs guilds with id 1 and 2
    '''

    tree: CommandTree = ctx.bot.tree

    if not guilds:
        # Sync current guild
        if spec == "~":
            synced = await tree.sync(guild=ctx.guild)
        
        # Copies all global app commands to current guild and syncs
        elif spec == "*": 
            tree.copy_global_to(guild=ctx.guild)
            synced = await tree.sync(guild=ctx.guild)

        # Clears all commands from the current guild target and syncs (removes guild commands)
        elif spec == "^": 
            tree.clear_commands(guild=ctx.guild)
            await tree.sync(guild=ctx.guild)
            synced = []

        # Global sync
        else: 
            synced = await tree.sync()
        await ctx.send(
            f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}"
        )
        return
    ret = 0
    for guild in guilds:
        try:
            await tree.sync(guild=guild)
        except HTTPException:
            pass
        else:
            ret += 1
    await ctx.send(f"Synced the tree to {ret}/{len(guilds)}.")

def main():
    asyncio.run(basiccommands.setup(BotEssentials.bot))
    asyncio.run(forumcommands.setup(BotEssentials.bot))
    asyncio.run(countercommand.setup(BotEssentials.bot))

    BotEssentials.bot.run(BOT_TOKEN)

if __name__ == "__main__":
    main()