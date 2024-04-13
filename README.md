# CloneChat

CloneChat is a versatile command-line tool designed to streamline the process of cloning Telegram chats. This powerful utility offers both primary and secondary functionalities, catering to a range of cloning needs. Whether you're looking to back up messages from a target channel or group into a neatly packaged `dump.db` file, or forward content directly from one Telegram chat to another, CloneChat provides a flexible and efficient solution.

## Features and Usage

### Primary Functions

**1. Dumping Chat Content:** Begin by saving the message content of your target Telegram channel or group into a dedicated folder, complete with a `dump.db` file. This initial step is crucial for preparing the chat's content for cloning.

```shell
python3 clonechat.py clone --input/-i <chat_id> --output/-o <output_folder_name>
```

**2. Using Dumped Content:** Once the content has been successfully dumped, you can then proceed to use this stored data to clone the messages into another Telegram chat. This functionality allows for the seamless transfer of chat history between different Telegram entities.

```shell
python3 clonechat.py clone --input/-i <output_folder_name> --output/-o <chat_id>
```

### Secondary Function

**1. Direct Cloning (Use with Caution):** For users seeking a more streamlined approach, CloneChat offers the capability to directly clone messages from one Telegram chat to another in a single command. This powerful feature should be used with caution, as it combines the dumping and cloning processes into one swift action.

```shell
python3 clonechat.py clone --input/-i <chat_id> --output/-o <chat_id>
```

#### Notes:

1. When you execute, stop and restart the bot, the messages that have been cloned will be skipped and the bot will resume from where it left off.
2. If you executes clonechat two times and use `--reverse` in one of them, the order messages can be break because the script save the `last_sent_message_id` and it doenst helps when switches the order.
3. **If you only executes `python3 clonechat.py` the interactive mode will be use instead of the CLI arguments.**

### Additional Options

- **Forwarding Messages:** Add the `--forward/-fwd` flag to enable message forwarding from the input chat to the output chat, assuming user permissions allow it. This option replicates the forwarding action, maintaining the original sender's information.
- **Reverse Message Order:** Utilize the `--reverse/-rev` flag to invert the order of message cloning, starting with the oldest messages first. This can be particularly useful for chronological consistency in certain cloning scenarios. (May take a while)
- **Random Sleep** Utilize the `--sleep-range/-lr` flag to define the min and max range of seconds. The script will get a (pseudo) random number from this range and sleep (wait) seconds between each send message. Usage example: `--sleep-range 10 30` (will choice radom numbers from 10 and 30 seconds). Default range is `(0, 1)`. 

### Logging

- **Log Level Adjustment:** Control the verbosity of the operation logs by specifying the `--loglevel/-ll` followed by your desired level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`). The default setting is `INFO`, providing a balanced amount of feedback during operations.

## Cleanup Command

- **Cleanup:** Execute the `cleanup` command to remove all previously stored chat data, ensuring a clean slate for future cloning activities.

```shell
python3 clonechat.py cleanup
```

CloneChat simplifies the complex process of chat cloning, offering a robust set of features for Telegram users. Whether for backup purposes or transitioning content between chats, CloneChat delivers a user-friendly and effective solution.
