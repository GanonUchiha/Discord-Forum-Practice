## Discord Bot for Archiving Bahamut Forum Threads

## Code
Only [src/bhvtubergossip.py](/src/bhvtubergossip.py), [src/bahamut.py](/src/bahamut.py) and `src/mycredentials.py` are relevant to this section.

## Usage
1. Under `src` create a file `mycredentials.py`, including credentials of your Discord Bot. For example:
    ```python
    BOT_ID = "Your Bot ID"
    BOT_TOKEN = "Your Bot Token"
    ```
    For more information, please refer to the [Discord Developer Portal](https://discord.com/developers/applications).  
    Do not share your bot token to anyone.
1. Under `config` create a file `bhvtb_config.json`, and create a list of forum channels you want to archive in the following format:
    ```json
    {
        "guilds": [
            {
                "guild-id": <Guild ID*>,
                "channels": [
                    {
                        "channel-id": <Forum Channel ID*>,
                        "BH-targets": [
                            [
                                <Board ID (bsn)*>,
                                <Thread ID (snA)*>,
                                <Starting Floor*>
                            ]
                        ]
                    }
                ]
            }
        ]
    }
    ```
    *All values should be integers (without `<>` or `""`)
    You can also modify [config/bhvtb_config_exmaple.json](/config/bhvtb_config_exmaple.json) and rename the file afterwards. The lists can also be extended.
1. Run `python src/bhvtubergossip.py` in your command prompt, and you should see the login information showing up in the command prompt.
1. Use the command `!start` to start the process, `!pause` to gracefully stop the bot from running, and `!stop` to forcefully stop the bot.

## Environment
Please refer to [this page](/README.md#environment).