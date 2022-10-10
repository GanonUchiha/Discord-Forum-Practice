from typing import Union, List, Tuple, Optional
from abc import ABC, abstractmethod
from time import sleep

import discord
from discord.ext import commands
from discord import ForumTag, TextStyle, Webhook, app_commands, AppCommandType, Interaction, ButtonStyle
from discord.ext.commands import Bot
from discord.app_commands import CommandTree, ContextMenu, Command, Group, describe, Choice
from discord.channel import ForumChannel

from settings import SharedVariables

class ChannelDropdown(discord.ui.Select):

    def __init__(self, channel_list: List[ForumChannel]):
        channel_options = [discord.SelectOption(label=option.name, value=str(option.id)) for option in channel_list]
        super().__init__(options=channel_options, placeholder="Choose a channel...")
    
    async def callback(self, interaction: Interaction):
        # print(interaction.data["component_type"])
        # await interaction.response.edit_message(content="Choose a channel...")
        await interaction.response.defer()

class TagsDropdown(discord.ui.Select):

    def __init__(self, tags_list: List[ForumTag]):
        options = [discord.SelectOption(label=tag.name, value=str(tag.id)) for tag in tags_list]
        super().__init__(options=options, placeholder="Select tag(s)...", min_values=0, max_values=min(5, len(options)))
    
    async def callback(self, interaction: Interaction):
        # print(interaction.data["component_type"])
        # return await super().callback(interaction)
        await interaction.response.defer()

class SelectChannelMessage(discord.ui.View):

    def add_components(self, channel_list: List[ForumChannel]):
        self.channel_dropdown = ChannelDropdown(channel_list)
        self.add_item(self.channel_dropdown)

class SelectMessage(discord.ui.View):

    def add_components(self, dropdown: discord.ui.Select):
        self.dropdown = dropdown
        self.confirm_button = discord.ui.Button(label="Confirm")

        self.dropdown_id = self.dropdown.custom_id
        self.button_id = self.confirm_button.custom_id

        self.add_item(self.dropdown)
        self.add_item(self.confirm_button)

class ThreadContentDialogue(discord.ui.Modal):
    title_inputbox = discord.ui.TextInput(label="Title:", placeholder="Enter title", row=0)
    content_inputbox = discord.ui.TextInput(label="Content:", placeholder="Enter content", row=1, style=TextStyle.paragraph)

    def __init__(self, title: str):
        super().__init__(title=title)

    async def on_submit(self, interaction: Interaction):
        # print(interaction.user, interaction.data)
        # await interaction.response.send_message(f'Thanks for your response, {interaction.user}!', ephemeral=True)
        await interaction.response.defer()

class ForumCommands(commands.Cog):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot

    async def get_channel(self, ctx: commands.Context, channel_name: str, type: Optional[str]=None):
        '''
        Search channel by name and channel type, and returns the first match.

        ## Parameters:
        ctx: `commands.Context`
            The Context object
        channel_name: `str`
            The channel's name
        type: `Optional[str]`
            The channel type

        ## Returns
        `abc.GuildChannel`
            The first channel object that matches in both criteria
        '''
        channels = await ctx.guild.fetch_channels()
        if type != None:
            found_channel = discord.utils.get(channels, name=channel_name, type=type)
        else:
            found_channel = discord.utils.get(channels, name=channel_name)
        return found_channel

    @commands.hybrid_command(name="get-channel-info")
    @describe(channel_name="Channel Name")
    async def get_channel_info(self, ctx: commands.Context, channel_name: str):
        '''
        Find and get channel name, ID, type and NSFW by name
        '''
        print("[LOG] User {} requested the channel info of {}".format(ctx.author, channel_name))

        found_channel = await self.get_channel(ctx, channel_name)

        await ctx.send("Channel info of {}:\n\tID: {}\n\ttype: {}\n\tNSFW: {}".format(channel_name, found_channel.id, found_channel.type, found_channel.nsfw))

    @commands.hybrid_command(name="get-channel-id")
    @describe(channel_name="Channel Name")
    async def get_channel_id(self, ctx: commands.Context, channel_name: str):
        '''
        Find and get channel ID by name
        '''
        print("[LOG] User {} requested the channel ID of {}".format(ctx.author, channel_name))

        found_channel = await self.get_channel(ctx, channel_name)

        await ctx.send("Channel ID of {} is: {}".format(channel_name, found_channel.id))

    @commands.hybrid_command(name="get-available-tags")
    @describe(channel_name="Channel Name")
    async def get_available_tags(self, ctx: commands.Context, channel_name: str):
        '''
        Find and get available tags in a forum channel
        '''
        print("[LOG] User {} requested the forum tags of {}".format(ctx.author, channel_name))

        found_channel: ForumChannel = await self.get_channel(ctx, channel_name, discord.ChannelType.forum)

        def tag2str(tag: discord.ForumTag):
            emoji = tag.emoji if tag.emoji != None else ""
            return f"(ID: {tag.id}) {emoji}{tag.name}"

        if found_channel != None:
            await ctx.send("\n".join([tag2str(tag)  for tag in found_channel.available_tags]))
        else:
            await ctx.send("Channel {} is not a forum channel.")


    @app_commands.command(name="create-forum-thread-interactive", description="Create a forum post through a sequence of interactions")
    async def create_forum_thread_interactive(self, interaction: Interaction):
        '''
        Create a forum post through a sequence of interactions
        '''
        print("[LOG] User {} wants to interactively create a thread.".format(interaction.user))
        all_channels = await interaction.guild.fetch_channels()
        forum_channels = [channel for channel in all_channels if type(channel) is ForumChannel]

        # Prompt user to enter thread title and content
        modal = ThreadContentDialogue(title="Create Thread Content...")
        await interaction.response.send_modal(modal)

        # Wait until the user interacts with the modal
        res: Interaction = await self.bot.wait_for('interaction', check=lambda interact: interact.data["custom_id"] == modal.custom_id)

        selected_channel = await self.ask_select_channel(interaction, forum_channels)
        selected_tags: List[ForumTag] = await self.ask_select_tags(interaction, selected_channel)

        # Create the thread
        thread, _ = await selected_channel.create_thread(name=modal.title_inputbox.value, content=modal.content_inputbox.value, applied_tags=selected_tags)
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
    
    async def ask_select_tags(self, interaction: Interaction, selected_channel: ForumChannel):
        all_tags = selected_channel.available_tags
        
        # Prompt user to select the forum channel they want to create the thread in
        view = SelectMessage()
        select_options = TagsDropdown(all_tags)
        view.add_components(select_options)
        response1 = await interaction.followup.send(content="Select tags:", view=view, ephemeral=True, wait=True)

        # Wait until the user interacts with the dropdown box
        await self.bot.wait_for('interaction', check=lambda interact: interact.data["custom_id"] == view.button_id)
        for item in view.children:
            # print(item.custom_id, res.data["custom_id"])
            if item.custom_id == view.dropdown_id:
                select: discord.ui.Select = item
                selected_ids: List[str] = select.values
        
        # Edit out the dropdown box after user selects
        # selected_channel: ForumChannel = interaction.guild.get_channel(channel_id)
        selected_tags = [tag for tag in selected_channel.available_tags if str(tag.id) in selected_ids]
        tags_str = ", ".join([tag.name for tag in selected_tags])
        await interaction.followup.edit_message(message_id=response1.id, content="Tags: {}".format(tags_str), view=None)

        return selected_tags

    @commands.hybrid_command(name="create-forum-thread")
    @describe(channel_id="Forum ID")
    async def create_forum_thread(self, ctx: commands.Context, channel_id: str, title: str, content: str):
        '''
        Create a forum post.
        
        ## Parameters
        channel_id: str
            The channel ID
        title: str
            Title of the post
        content: str
            Content of the post
        '''
        print("[LOG] User {} wants to create a thread in {}".format(ctx.author, channel_id))

        forum_channel: ForumChannel = ctx.guild.get_channel(int(channel_id))
        thread: discord.Thread
        thread, _ = await forum_channel.create_thread(name=title, content=content)

        await ctx.send(content="Created thread at: {}".format(thread.jump_url), ephemeral=True)


async def setup(bot: commands.Bot) -> None:
  await bot.add_cog(ForumCommands(bot))