
from pathlib import Path
import requests
from typing import Union, List, Tuple, Optional
from abc import ABC, abstractmethod
from time import sleep
from bs4 import Tag, BeautifulSoup
import json
import asyncio
from math import floor

import discord
from discord.ext import commands, tasks
from discord import InteractionResponded, app_commands, Interaction, Thread, Guild
from discord.ext.commands import Bot, Context
from discord.app_commands import CommandTree, ContextMenu, Command, Group, describe, Choice
from discord.channel import ForumChannel

from settings import SharedVariables, BotEssentials
from bahamut import BahamutPost, get_webpage, get_posts
from mycredentials import BOT_TOKEN

class ArchiveChannel:

    def __init__(self, channel: ForumChannel, targets: List[List[int]]):
        self.channel = channel
        self.targets = targets
    
    def export(self) -> dict:
        return {
            "channel-id": self.channel.id,
            "BH-targets": self.targets
        }

class BHThread:
    BH_THREAD_TEMPLATE = "https://forum.gamer.com.tw/C.php?bsn={board}&snA={thread}&page={page}"

    def __init__(self, bsn: int, snA: int, start_floor: int):
        self.bsn = bsn
        self.snA = snA
        self.start_floor = start_floor
        self.title = ""
    
    def page_url(self, page: int = 1):
        return self.BH_THREAD_TEMPLATE.format(
            board=self.bsn,
            thread=self.snA,
            page=page
        )
    
    def set_title(self, new_title):
        self.title = new_title
    
    @property
    def start_page(self):
        return (self.start_floor // 20) + 1

class BHVTuberGossip(commands.Cog):
    BH_THREAD_TEMPLATE = "https://forum.gamer.com.tw/C.php?bsn={board}&snA={thread}"
    
    def __init__(self, bot: commands.Bot, config_file: Union[Path, str]) -> None:
        self.bot: commands.Bot = bot
        self.selected_channel: ForumChannel = None

        self.config_file = Path(config_file)
        self.load_config()
        print("Config Loaded.")

    def load_config(self):
        with self.config_file.open(encoding="utf8") as fp:
            self.config = json.load(fp)

    def save_config(self):
        with self.config_file.open("w", encoding="utf8") as fp:
            json.dump(self.config, fp, indent=4)

    def cog_unload(self):
        self.fetch_posts.cancel()

    @tasks.loop(minutes=10)
    async def fetch_posts(self):
        for guild_config in self.config["guilds"]:
            guild: Guild = self.bot.get_guild(guild_config["guild-id"])
            guild_channels = guild_config["channels"]
            print(f"Guild {guild.name}")

            for channel_config in guild_channels:
                channel = guild.get_channel(channel_config["channel-id"])
                print(f"Channel {channel.name}")

                for target in channel_config["BH-targets"]:
                    target_thread = BHThread(target[0], target[1], target[2])
                    last_floor = await fetch_thread_posts(target_thread, channel)
                    target[2] = last_floor + 1

        self.save_config()
    
    @commands.command()
    async def start(self, ctx: Context):
        self.fetch_posts.start()
        await ctx.send("已開始爬取討論版。")

    @commands.command()
    async def stop(self, ctx: Context):
        self.fetch_posts.stop()
        await ctx.send("已下令暫停爬取討論版，機器人將在稍後自行停止。")

    @commands.command()
    async def cancel(self, ctx: Context):
        self.fetch_posts.cancel()
        await ctx.send("已強制暫停爬取討論版。")
    
async def fetch_thread_posts(target_thread: BHThread, channel: ForumChannel) -> int:

    response: requests.Response = get_webpage(target_thread.page_url())
    soup = BeautifulSoup(response.text, features="lxml")

    pages_btn_row = soup.find("p", attrs={"class": "BH-pagebtnA"})
    top_post = BahamutPost(get_posts(soup)[0])
    target_thread.set_title(top_post.title)
    num_pages = int(pages_btn_row.find_all("a")[-1].text)
    page_start = target_thread.start_page
    page_end = min(num_pages + 1, page_start + 3)

    for page in range(page_start, page_end):
        page_url = target_thread.page_url(page=page)

        # Fetch the posts for the page
        response: requests.Response = get_webpage(page_url)
        soup = BeautifulSoup(response.text, features="lxml")
        page_posts: List[Tag] = get_posts(soup)

        last_floor = await archive_page(target_thread, page_posts, page_url, channel)
        sleep(1)
    
    return last_floor

async def archive_page(target_thread: BHThread, posts_raw: List[Tag], page_url: str, channel: ForumChannel) -> int:
    last_floor = 0

    for post_raw in posts_raw:
        post = BahamutPost(post_raw, page_url)
        await archive_post(target_thread, post, channel)
        last_floor = int(post.floor)
        sleep(2)
    
    return last_floor

async def archive_post(target_thread: BHThread, post: BahamutPost, channel: ForumChannel):
    post.title = target_thread.title
    post_content = post.export(include_header=True)
    post_hashtags = post.hashtags
    applied_tags = [tag for tag in channel.available_tags if tag.name in post_hashtags]

    if len(post_content) > 2000: # Longer posts Are sent as text files
        with Path("content.txt").open("w") as fp:
            fp.write(post_content)
        with Path("content.txt") as path:
            # Create the thread
            await channel.create_thread(
                name=f"{post.title} {post.floor}樓",
                file=discord.File(path),
                applied_tags=applied_tags
            )
    else:
        # Create the thread
        await channel.create_thread(
            name=f"{post.title} {post.floor}樓",
            content=post_content,
            applied_tags=applied_tags
        )

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(BHVTuberGossip(bot, "archive_thread_config.json"))

def main():
    # Setting up the bot
    BotEssentials.setup_bot()
    BotEssentials.bot

    asyncio.run(setup(BotEssentials.bot))
    BotEssentials.bot.run(BOT_TOKEN)

if __name__ == "__main__":
    main()