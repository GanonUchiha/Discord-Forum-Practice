
from pathlib import Path
import requests
from typing import Tuple, Union, List
from time import sleep
from bs4 import Tag, BeautifulSoup
import asyncio
from collections import defaultdict

import pandas as pd
from pandas import DataFrame

from discord.ext import commands, tasks
from discord import Guild, File, Thread
from discord.ext.commands import Context
from discord.channel import ForumChannel

from settings import BotEssentials
from bahamut import BahamutPost, get_webpage, get_posts
from mycredentials import BOT_TOKEN



class BHPage(BeautifulSoup):

    def get_title(self):
        scrolldown_header: Tag = self.find("div", attrs={"class": "c-menu__scrolldown"})
        title = scrolldown_header.find("h1", attrs={"class": "title"}).text
        return title

    def get_post_list(soup: BeautifulSoup) -> List[Tag]:
        sections: List[Tag] = soup.find_all("section", attrs={"class": "c-section"})
        return [tag for tag in sections if "id" in tag.attrs and tag.attrs["id"].startswith("post")]
    
    def get_page_btn_row(self) -> Tag:
        return self.find("p", attrs={"class": "BH-pagebtnA"})
    
    def get_page_btn_list(self) -> List[Tag]:
        return self.get_page_btn_row().find_all("a")

class BHThread:

    BH_THREAD_TEMPLATE: str = "https://forum.gamer.com.tw/C.php?bsn={board}&snA={thread}&page={page}"
    channel: ForumChannel
    bsn: int
    snA: int
    last_floor: int
    title: str
    first_page: BHPage

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

    def __init__(self, channel: ForumChannel, bsn: int, snA: int, last_floor: int, gp_thresh: int, bp_thresh: int):
        self.channel = channel
        self.bsn = bsn
        self.snA = snA
        self.last_floor = last_floor
        self.title = "No Title"
        self.gp_thresh = gp_thresh
        self.bp_thresh = bp_thresh
    
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
    
    def set_title(self, title: str):
        """
        Assigns the title of the thread.

        ## Parameter(s)
        new_title: `str`
            The thread title
        """
        self.title = title
    
    def set_channel(self, channel: ForumChannel):
        """
        Assigns the channel to save the archives in.

        ## Parameter(s)
        channel: `ForumChannel`
            The designation forum channel
        """
        self.channel = channel
    
    def get_info(self) -> List[int]:
        return [self.channel.id, self.bsn, self.snA, self.last_floor]
    
    def get_page_range(self, pages_per_batch: int = 2) -> Tuple[int, int]:
        page_start = self.start_page
        page_end = min(self.num_pages + 1, page_start + pages_per_batch)
        return (page_start, page_end)

    def get_page_count(self):
        page_count = self.first_page.get_page_btn_list()[-1].text
        return int(page_count)

    async def fetch_thread_posts(self):

        # Get webpage
        response: requests.Response = get_webpage(self.page_url())
        self.first_page = BHPage(response.text, features="lxml")

        # Get thread title
        self.title = self.first_page.get_title()

        # Get total number of pages
        self.num_pages = self.get_page_count()

        # Get page range
        page_start: int
        page_end: int
        page_start, page_end = self.get_page_range()

        for page_num in range(page_start, page_end):
            page_url = self.page_url(page=page_num)

            # Fetch the posts for the page
            response: requests.Response = get_webpage(page_url)
            bh_page = BHPage(response.text, features="lxml")
            page_post_list: List[Tag] = bh_page.get_post_list()

            await self.archive_page(page_post_list, page_url)
    
    def skip_floor(self, post: BahamutPost):
        if int(post.floor) < self.start_floor:
            return True
        elif post.gp < self.gp_thresh:
            return True
        elif self.bp_thresh > 0 and post.bp >= self.bp_thresh:
            return True
        return False

    async def archive_page(self, posts_raw: List[Tag], page_url: str):

        for post_raw in posts_raw:
            post = BahamutPost(post_raw, page_url)

            if self.skip_floor(post):
                continue

            await self.archive_post(post)

            # Update last floor 
            self.last_floor = int(post.floor)
            sleep(5)

    def prepare_thread_content(self, post: BahamutPost) -> dict:
        post_content = post.content
        post_info = post.info
        full_content = post_info + post.SEPARATOR + post_content

        if len(full_content) > 2000: # Longer posts are sent as text files
            path = Path("temp/content.txt")
            with path.open("w", encoding="utf8") as fp:
                fp.write(post_content)
            content_kwargs = {
                "content": post_info,
                "file": File(path)
            }
        else:
            content_kwargs = {
                "content": full_content
            }
        
        return content_kwargs

    async def archive_post(self, post: BahamutPost):
        post.title = self.title
        post_hashtags = post.hashtags
        applied_tags = [tag for tag in self.channel.available_tags if tag.name in post_hashtags]

        thread_kwargs = {
            "name": f"{post.title} {post.floor}樓",
            "applied_tags": applied_tags[:5],
        }
        content_kwargs = self.prepare_thread_content(post)

        thread, _ = await self.channel.create_thread(
            **thread_kwargs,
            **content_kwargs
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
            config: DataFrame = pd.read_csv(fp, index_col=None, dtype=defaultdict(lambda: "Int64"))
            self.columns = config.columns
            for _, row in config.iterrows():
                channel = self.bot.get_channel(row["channel_id"])
                self.threads.append(BHThread(
                    channel,
                    row["bsn"],
                    row["snA"], 
                    row["last_floor"],
                    row["gp_thresh"],
                    row["bp_thresh"],
                ))
        
        print("[CONFIG] Config Loaded.")

    def save_config(self):
        # columns = ["channel_id", "bsn", "snA", "last_floor"]
        config = DataFrame([bh_thread.get_info() for bh_thread in self.threads], columns=self.columns)
        with self.config_file.open("w", encoding="utf8") as fp:
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
        await ctx.send("已開始獲取討論串貼文。")

    @commands.command()
    async def pause(self, ctx: Context):
        self.fetch_posts.stop()
        await ctx.send("已下令暫停獲取討論串貼文，機器人將在本輪作業結束後停止。")

    @commands.command()
    async def stop(self, ctx: Context):
        self.fetch_posts.cancel()
        await ctx.send("已強制停止。")

    @commands.command()
    async def reload(self, ctx: Context):
        self.load_config()
        await ctx.send("已重新讀取目標討論串清單")

    @commands.command(name="archive-all")
    async def archive_all(self, ctx: Context, id: int):
        threads: List[Thread] = ctx.guild.get_channel(id).threads
        for thread in threads:
            await thread.edit(archived=True)
            sleep(1)
        await ctx.send("已關閉所有DC討論串")
    
    @commands.command(name="list")
    async def thread_list(self, ctx: Context):
        thread_list: List[str] = []
        for thr in self.threads:
            if thr.channel.guild == ctx.guild:
                thread_list.append("{}: bsn={}&snA={} {}樓".format(thr.channel.name, thr.bsn, thr.snA, thr.last_floor))
        await ctx.send("\n".join(thread_list))

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