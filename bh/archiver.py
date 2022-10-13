
from pathlib import Path
import requests
from typing import Union, List
from time import sleep
from bs4 import Tag, BeautifulSoup
import json
import asyncio
from collections import defaultdict

import pandas as pd
from pandas import DataFrame

from discord.ext import commands, tasks
from discord import Guild, File, Thread
from discord.ext.commands import Context
from discord.channel import ForumChannel

import sys
sys.path.append("../src/")

from settings import BotEssentials
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

    def __init__(self, channel: ForumChannel, bsn: int, snA: int, last_floor: int):
        self.channel = channel
        self.bsn = bsn
        self.snA = snA
        self.last_floor = last_floor
        self.title = "No Title"
    
    def page_url(self, page: int = 1):
        """
        Gets the page URL to the thread.

        ## Parameter(s)
        page: `int`
            The page number you want to jump to. Defaults to 1.

        ## Returns
        `str`
        """
        return self.BH_THREAD_TEMPLATE.format(
            board=self.bsn,
            thread=self.snA,
            page=page
        )
    
    def set_title(self, new_title: str):
        """
        Assigns the title of the thread.

        ## Parameter(s)
        new_title: `str`
            The thread title
        """
        self.title = new_title
    
    def set_channel(self, channel: ForumChannel):
        """
        Assigns the channel to save the archives in.

        ## Parameter(s)
        channel: `ForumChannel`
            The designation forum channel
        """
        self.channel = channel
    
    def get_config(self) -> List[int]:
        return [self.channel.id, self.bsn, self.snA, self.last_floor]

    @property
    def start_floor(self):
        """
        The floor number we should continue from
        """
        return self.last_floor + 1
    
    @property
    def start_page(self):
        """
        The page number we should continue from
        """
        return (self.last_floor // 20) + 1

    async def fetch_thread_posts(self):

        # Get webpage as soup
        response: requests.Response = get_webpage(self.page_url())
        soup = BeautifulSoup(response.text, features="lxml")

        # Get thread title
        pages_btn_row = soup.find("p", attrs={"class": "BH-pagebtnA"})
        top_post = BahamutPost(get_posts(soup)[0])
        self.set_title(top_post.title)

        # Get total number of pages
        num_pages = int(pages_btn_row.find_all("a")[-1].text)

        # Get page range
        pages_per_batch = 2
        page_start = self.start_page
        page_end = min(num_pages + 1, page_start + pages_per_batch)

        for page in range(page_start, page_end):
            page_url = self.page_url(page=page)

            # Fetch the posts for the page
            response: requests.Response = get_webpage(page_url)
            soup = BeautifulSoup(response.text, features="lxml")
            page_posts: List[Tag] = get_posts(soup)

            await self.archive_page(page_posts, page_url)
    
    
    async def archive_page(self, posts_raw: List[Tag], page_url: str):

        for post_raw in posts_raw:
            post = BahamutPost(post_raw, page_url)
            if int(post.floor) < self.start_floor:
                continue

            await self.archive_post(post)

            # Update last floor 
            self.last_floor = int(post.floor)
            sleep(5)

    async def archive_post(self, post: BahamutPost):
        post.title = self.title
        post_content = post.export(include_header=True)
        post_hashtags = post.hashtags
        applied_tags = [tag for tag in self.channel.available_tags if tag.name in post_hashtags]

        if len(post_content) > 2000: # Longer posts Are sent as text files
            with Path("content.txt").open("w", encoding="utf8") as fp:
                fp.write(post_content)
            with Path("content.txt", encoding="utf8") as path:
                # Create the thread
                thread, _ = await self.channel.create_thread(
                    name=f"{post.title} {post.floor}樓",
                    content=post.metadata.info,
                    file=File(path),
                    applied_tags=applied_tags[:5],
                )
                await thread.edit(archived=True)
        else:
            # Create the thread
            thread, _ = await self.channel.create_thread(
                name=f"{post.title} {post.floor}樓",
                content=post_content,
                applied_tags=applied_tags[:5],
            )
            await thread.edit(archived=True)

class BHThreadArchiver(commands.Cog):
    BH_THREAD_TEMPLATE = "https://forum.gamer.com.tw/C.php?bsn={board}&snA={thread}"
    
    def __init__(self, bot: commands.Bot, config_file: Union[Path, str]) -> None:
        self.bot: commands.Bot = bot
        self.threads: List[BHThread] = []
        self.config_file = Path(config_file)

    def load_config(self):
        # Clear previous data
        self.threads.clear()

        # Load from config file
        with self.config_file.open(encoding="utf8") as fp:
            # self.config = json.load(fp)
            config: DataFrame = pd.read_csv(fp, index_col=None, dtype=defaultdict(lambda: "Int64"))
            self.columns = config.columns
            for _, row in config.iterrows():
                channel = self.bot.get_channel(row["channel_id"])
                self.threads.append(BHThread(channel, row["bsn"], row["snA"], row["last_floor"]))
        
        print("[CONFIG] Config Loaded.")

    def save_config(self):
        # columns = ["channel_id", "bsn", "snA", "last_floor"]
        config = DataFrame([bh_thread.get_config() for bh_thread in self.threads], columns=self.columns)
        with self.config_file.open("w", encoding="utf8") as fp:
            # json.dump(self.config, fp, indent=4)
            config.to_csv(fp, index=False, lineterminator="\n")
        print("[CONFIG] Config Saved.")

    def cog_unload(self):
        self.fetch_posts.cancel()

    @tasks.loop(minutes=20)
    async def fetch_posts(self):
        print("[LOOP] Loop started")
        for bh_thread in self.threads:
            await bh_thread.fetch_thread_posts()
        print("[LOOP] Loop completed successfully")
    
    @fetch_posts.after_loop
    async def fetch_posts_stopped(self):
        self.save_config()
        print("[LOOP] The bot stopped")
    
    # Basic commands
    @commands.command()
    async def start(self, ctx: Context):
        self.load_config()
        self.fetch_posts.start()
        await ctx.send("已開始爬取討論版。")

    @commands.command()
    async def pause(self, ctx: Context):
        self.fetch_posts.stop()
        await ctx.send("已下令暫停爬取討論版，機器人將在稍後自行停止。")

    @commands.command()
    async def stop(self, ctx: Context):
        self.fetch_posts.cancel()
        await ctx.send("已強制停止爬取討論版。")

    @commands.command()
    async def reload(self, ctx: Context):
        self.load_config()
        await ctx.send("已重新讀取目標討論版清單")

    @commands.command(name="archive-all")
    async def archive_all(self, ctx: Context, id: int):
        threads: List[Thread] = ctx.guild.get_channel(id).threads
        for thread in threads:
            await thread.edit(archived=True)
            sleep(1)
        await ctx.send("已關閉所有討論串")
    
    @commands.command(name="list")
    async def thread_list(self, ctx: Context):
        thread_list: List[str] = []
        for thr in self.threads:
            if thr.channel.guild == ctx.guild:
                thread_list.append("{}: bsn={}&snA={} {}樓".format(thr.channel.name, thr.bsn, thr.snA, thr.last_floor))
        await ctx.send("\n".join(thread_list))

# async def fetch_thread_posts(target_thread: BHThread, channel: ForumChannel) -> int:

#     response: requests.Response = get_webpage(target_thread.page_url())
#     soup = BeautifulSoup(response.text, features="lxml")

#     pages_btn_row = soup.find("p", attrs={"class": "BH-pagebtnA"})
#     top_post = BahamutPost(get_posts(soup)[0])
#     target_thread.set_title(top_post.title)

#     num_pages = int(pages_btn_row.find_all("a")[-1].text)
#     pages_per_batch = 5
#     page_start = target_thread.start_page
#     page_end = min(num_pages + 1, page_start + pages_per_batch)
#     last_floor = target_thread.start_floor - 1

#     for page in range(page_start, page_end):
#         page_url = target_thread.page_url(page=page)

#         # Fetch the posts for the page
#         response: requests.Response = get_webpage(page_url)
#         soup = BeautifulSoup(response.text, features="lxml")
#         page_posts: List[Tag] = get_posts(soup)

#         await archive_page(target_thread, page_posts, page_url, channel)
    
#     return last_floor

# async def archive_page(target_thread: BHThread, posts_raw: List[Tag], page_url: str, channel: ForumChannel) -> int:
#     last_floor = 0

#     for post_raw in posts_raw:
#         post = BahamutPost(post_raw, page_url)
#         if int(post.floor) < target_thread.start_floor:
#             continue
#         await archive_post(target_thread, post, channel)
#         target_thread.last_floor = int(post.floor)
#         sleep(5)
    
#     return last_floor

# async def archive_post(target_thread: BHThread, post: BahamutPost, channel: ForumChannel):
#     post.title = target_thread.title
#     post_content = post.export(include_header=True)
#     post_hashtags = post.hashtags
#     applied_tags = [tag for tag in channel.available_tags if tag.name in post_hashtags]

#     if len(post_content) > 2000: # Longer posts Are sent as text files
#         with Path("content.txt").open("w", encoding="utf8") as fp:
#             fp.write(post_content)
#         with Path("content.txt", encoding="utf8") as path:
#             # Create the thread
#             thread, _ = await channel.create_thread(
#                 name=f"{post.title} {post.floor}樓",
#                 file=File(path),
#                 applied_tags=applied_tags[:5],
#             )
#             await thread.edit(archived=True)
#     else:
#         # Create the thread
#         thread, _ = await channel.create_thread(
#             name=f"{post.title} {post.floor}樓",
#             content=post_content,
#             applied_tags=applied_tags[:5],
#         )
#         await thread.edit(archived=True)

async def setup(bot: commands.Bot) -> None:
    # await bot.add_cog(BHThreadArchiver(bot, "config/bhvtb_config.json"))
    await bot.add_cog(BHThreadArchiver(bot, "config/config.csv"))

def main():
    # Setting up the bot
    BotEssentials.setup_bot()

    asyncio.run(setup(BotEssentials.bot))
    BotEssentials.bot.run(BOT_TOKEN)

if __name__ == "__main__":
    main()