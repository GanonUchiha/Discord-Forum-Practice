
import requests
from typing import Union, List, Tuple, Optional
from abc import ABC, abstractmethod
from time import sleep
from bs4 import Tag, BeautifulSoup

import discord
from discord.ext import commands
from discord import ForumTag, TextStyle, Webhook, app_commands, AppCommandType, Interaction, ButtonStyle
from discord.ext.commands import Bot
from discord.app_commands import CommandTree, ContextMenu, Command, Group, describe, Choice
from discord.channel import ForumChannel

from settings import SharedVariables
from bahamut import get_webpage, get_posts, extract_post_header, extract_post_body, PostMetadata

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
    
    
    @app_commands.command(name="bahamut-archive", description="Archive a post at bahamut as a DC forum post")
    @app_commands.choices(archive_range=[
        Choice(name="Main Post", value=1),
        Choice(name="First Page", value=2),
        Choice(name="Entire Thread", value=3),
    ])
    @app_commands.rename(archive_range="range", post_url="url")
    async def create_forum_thread_interactive(self, interaction: Interaction, archive_range: Choice[int], post_url: str):
        '''
        Archive a post at bahamut as a DC forum post
        '''
        print("[LOG] User {} wants to archive a post with range {}.".format(interaction.user, archive_range))
        await interaction.response.defer(ephemeral=True, thinking=True)

        response: requests.Response = get_webpage(post_url)
        soup = BeautifulSoup(response.text, features="lxml")
        posts: List[Tag] = get_posts(soup)
        post_meta: PostMetadata = extract_post_header(posts[0], post_url)
        post_title = post_meta.title
        post_content = extract_post_body(posts[0])
        
        match archive_range:
            case 1:
                pass
            case _:
                pass
        
        all_channels = await interaction.guild.fetch_channels()
        forum_channels = [channel for channel in all_channels if type(channel) is ForumChannel]
        selected_channel = await self.ask_select_channel(interaction, forum_channels)

        # Create the thread
        thread, _ = await selected_channel.create_thread(name=post_title, content=post_content)
        await interaction.followup.send(content="Thread created at: {}".format(thread.jump_url), ephemeral=True)

    async def ask_select_channel(self, interaction: Interaction, forum_channels: List[ForumChannel]) -> ForumChannel:

        # Prompt user to select the forum channel they want to create the thread in
        view = SelectMessage()
        select_options = ChannelDropdown(forum_channels)
        view.add_components(select_options)
        response1 = await interaction.followup.send(content="Create Thread in:", view=view, ephemeral=True, wait=True)

        # Wait until the user interacts with the dropdown box
        await self.bot.wait_for('interaction', check=lambda interact: interact.data["custom_id"] == view.button_id)
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