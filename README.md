# Discord Forum Practice
A project to practice manipulating Discord forum channels with a bot.

## Objective
In this project, I attempt to get familiar with the capabilities of a Discord bot, and the python API wrapper for Discord, [discord.py](https://github.com/Rapptz/discord.py). The ultimate goal is to make this repository a demonstration of bot features, as well as a collection of building blocks for my future projects.  

At first, I was curious about how a bot can be used to manipulate a forum channel, creating and managing posts to be specific. However, I have discovered other interesting features along the way, such as slash commands and interactive components, so the code became a bit messy. I would like to tidy it up, but unfortunately I would have to abandon this project for a short while. 

## Usage
1. Under `src` create a file `mycredentials.py`, including credentials of your Discord Bot. For example:
    ```python
    BOT_ID = "Your Bot ID"
    BOT_TOKEN = "Your Bot Token"
    ```
    For more information, please refer to the [Discord Developer Portal](https://discord.com/developers/applications).  
    Do not share your bot token to anyone.
1. Run `python src/bot_main.py` in your command prompt, and you should see the login information showing up in the command prompt.
1. Every time you create new slash commands or modify them, you have to use `!sync` command in Discord for the new configuations to take effect.

## Environment

This project uses the following packages:
| Package | Version |
|---|---|
| beautifulsoup4 | 4.11.1 |
| discord.py | 2.1.0a* |
| python | 3.10.4 |
| urllib3 | 1.26.12 |
| requests | 2.28.1 |

*This version of the package was the latest version at the time, and was installed from source.

Detailed packages and versions can be found in `requirements.yml`. To create an identical virtual environment in Anaconda, use the command `conda env create -f requirements.yml`.

## Discord Webhook Demo
Please refer to [this page](/docs/Webhook.md).

## Discord Bot for Archiving Bahamut Forum Threads
Please refer to [this page](/docs/BH-vtb.md).