
import requests
from typing import Union, List, Tuple, Optional
from abc import ABC, abstractmethod
from time import sleep
from bs4 import Tag, BeautifulSoup

import discord
from discord.ext import commands
from discord import InteractionResponded, app_commands, Interaction, Thread
from discord.ext.commands import Bot
from discord.app_commands import CommandTree, ContextMenu, Command, Group, describe, Choice
from discord.channel import ForumChannel

from settings import SharedVariables
from bahamut import BahamutPost, get_webpage, get_posts

class ChannelDropdown(discord.ui.Select):

    def __init__(self, channel_list: List[ForumChannel]):
        channel_options = [discord.SelectOption(label=option.name, value=str(option.id)) for option in channel_list]
        super().__init__(options=channel_options, placeholder="Choose a channel...")
    
    async def callback(self, interaction: Interaction):
        # print(interaction.data["component_type"])
        # await interaction.response.edit_message(content="Choose a channel...")
        await interaction.response.defer()

class SelectMessage(discord.ui.View):

    def add_components(self, dropdown: discord.ui.Select):
        self.dropdown = dropdown
        self.confirm_button = discord.ui.Button(label="Confirm")

        self.dropdown_id = self.dropdown.custom_id
        self.button_id = self.confirm_button.custom_id

        self.add_item(self.dropdown)
        self.add_item(self.confirm_button)

class BahamutAchiver(commands.Cog):
    
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot
        self.selected_channel: ForumChannel = None
    
    
    @app_commands.command(name="bh-archive", description="Archive a post at bahamut as a DC forum post")
    @app_commands.choices(archive_range=[
        Choice(name="First Post", value=1),
        Choice(name="Page", value=2),
        Choice(name="Thread", value=3),
    ])
    @app_commands.rename(archive_range="range", post_url="url")
    async def bahamut_archive(self, interaction: Interaction, archive_range: Choice[int], post_url: str):
        '''
        Archive a post at bahamut as a DC forum post
        '''
        print("[LOG] User {} wants to archive a post with range {}.".format(interaction.user, archive_range.name))
        await interaction.response.defer(ephemeral=True)
        
        # Ask user to select a channel if not selected before
        if self.selected_channel == None:
            all_channels = await interaction.guild.fetch_channels()
            forum_channels = [channel for channel in all_channels if type(channel) is ForumChannel]
            self.selected_channel = await self.ask_select_channel(interaction, forum_channels)

        response: requests.Response = get_webpage(post_url)
        soup = BeautifulSoup(response.text, features="lxml")
        is_main_page = (soup.find("p", attrs={"class": "BH-pagebtnA"}) != None)
        posts: List[Tag] = get_posts(soup)
        
        match archive_range.value:
            case 1: # First Page
                post = BahamutPost(posts[0], post_url)
                thread: Thread =await self.archive_post(post)
                
                # Send final message
                await interaction.followup.send(
                    content="Thread created at {}: {}".format(self.selected_channel.name, thread.jump_url),
                    ephemeral=False
                )
            case 2 | 3 if not is_main_page: # Main Post
                created_threads = await self.archive_page(posts, post_url)
                thread_urls = "\n".join([thr.jump_url for thr in created_threads])

                # Send final message
                await interaction.followup.send(
                    content="Thread created at {}:\n{}".format(self.selected_channel.name, thread_urls),
                    ephemeral=False
                )
            case 3: # Whole Thread
                if soup.find("p", attrs={"class": "BH-pagebtnA"}):
                    pass
                else:
                    created_threads = await self.archive_page(posts, post_url)
                    thread_urls = "\n".join([thr.jump_url for thr in created_threads])

                    # Send final message
                    await interaction.followup.send(
                        content="Thread created at {}:\n{}".format(self.selected_channel.name, thread_urls),
                        ephemeral=False
                    )
            case _:
                # Send message
                await interaction.followup.send(
                    content="Option {} not supported yet".format(archive_range.name), ephemeral=True
                )

    async def archive_page(self, posts_raw: List[Tag], page_url: str) -> List[Thread]:
        created_threads: List[Thread] = []
        thread_title = BahamutPost(posts_raw[0]).title
        for post_raw in posts_raw:
            post = BahamutPost(post_raw, page_url)
            thread: Thread = await self.archive_post(post, thread_title=thread_title)
            created_threads.append(thread)
        
        return created_threads
    
    async def archive_post(self, post: BahamutPost, thread_title: str="") -> Thread:
        if post.title == "No Title":
            post.title = thread_title
        post_content = post.export(include_header=True)
        # Create the thread
        thread, _ = await self.selected_channel.create_thread(
            name=f"{post.title} \#{post.floor}",
            content=post_content
        )
        return thread

    @app_commands.command(name="bh-set-channel", description="Set default channel to send the archive to")
    async def bh_select_channel(self, interaction: Interaction):
        all_channels = await interaction.guild.fetch_channels()
        forum_channels = [channel for channel in all_channels if type(channel) is ForumChannel]
        self.selected_channel = await self.ask_select_channel(interaction, forum_channels)
        await interaction.followup.send(
            content="Forum channel set to: {}".format(self.selected_channel.name),
            ephemeral=True
        )

    async def ask_select_channel(self, interaction: Interaction, forum_channels: List[ForumChannel]) -> ForumChannel:

        # Prompt user to select the forum channel they want to create the thread in
        view = SelectMessage()
        select_options = ChannelDropdown(forum_channels)
        view.add_components(select_options)
        try:
            await interaction.response.defer(ephemeral=True, thinking=True)
        except InteractionResponded:
            pass
        response1 = await interaction.followup.send(content="Create Thread in:", view=view, ephemeral=True, wait=True)

        # Wait until the user interacts with the dropdown box
        await self.bot.wait_for(
            'interaction',
            check=lambda interact: "custom_id" in interact.data and interact.data["custom_id"] == view.button_id
        )
        for item in view.children:
            # print(item.custom_id, res.data["custom_id"])
            if item.custom_id == view.dropdown_id:
                select: discord.ui.Select = item
                channel_id = int(select.values[0])
        
        # Edit out the dropdown box after user selects
        selected_channel: ForumChannel = interaction.guild.get_channel(channel_id)
        await interaction.followup.edit_message(message_id=response1.id, content="Channel: {}".format(selected_channel.name), view=None)

        return selected_channel


async def setup(bot: commands.Bot) -> None:
  await bot.add_cog(BahamutAchiver(bot))