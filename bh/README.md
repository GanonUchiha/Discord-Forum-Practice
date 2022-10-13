## Discord Bot for Archiving Bahamut Forum Threads

## Code
Only files under [/bh](/bh/) are relevant.

## Usage
1. Under `src` create a file `mycredentials.py`, including credentials of your Discord Bot. For example:
    ```python
    BOT_ID = "Your Bot ID"
    BOT_TOKEN = "Your Bot Token"
    ```
    For more information, please refer to the [Discord Developer Portal](https://discord.com/developers/applications).  
    Do not share your bot token to anyone.
1. Under `config` create a file `config.csv`, and create a list including these columns:
    - `channel_id`: ID of the destination forum channel
    - `bsn`: The board ID
    - `snA`: The thread ID
    - `last_floor`: The last floor you stopped archiving at
        - Fill in `0` if you want to start from the beginning
    - `gp_thresh`: The GP threshold a post has to reach in order to be archived (inclusive)
    - `bp_thresh`: The BP threshold that excludes a post if it is reached
        - Use at least `5` to activate the threshold. Any value below `5` will be ignored.

    *All values should be integers.
1. Run `python src/bhvtubergossip.py` in your command prompt, and you should see the login information showing up in the command prompt.
1. Use the command `!start` to start the process, `!pause` to gracefully stop the bot from running, and `!stop` to forcefully stop the bot.

## Environment
Please refer to [this page](/README.md#environment).