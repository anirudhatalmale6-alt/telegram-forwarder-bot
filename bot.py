import configparser
import asyncio
import logging
import os
import json
import re
from telethon import TelegramClient, events
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.ini")
MAP_PATH = os.path.join(SCRIPT_DIR, "message_map.json")

config = configparser.ConfigParser()
config.optionxform = str
config.read(CONFIG_PATH, encoding="utf-8")

API_ID = config.getint("telegram", "api_id")
API_HASH = config.get("telegram", "api_hash")

SOURCE_CHANNEL = config.get("channels", "source")
TARGET_CHANNEL = config.get("channels", "target")

REPLACEMENTS = {}
if config.has_section("text_replacements"):
    for key, value in config.items("text_replacements"):
        REPLACEMENTS[key] = value

try:
    SOURCE_CHANNEL = int(SOURCE_CHANNEL)
except ValueError:
    pass

try:
    TARGET_CHANNEL = int(TARGET_CHANNEL)
except ValueError:
    pass


def load_message_map():
    if os.path.exists(MAP_PATH):
        with open(MAP_PATH, "r") as f:
            return json.load(f)
    return {}


def save_message_map(msg_map):
    with open(MAP_PATH, "w") as f:
        json.dump(msg_map, f)


def transform_signal(text):
    if not text:
        return text

    text_lower = text.lower()

    if "sell zone now" in text_lower:
        direction = "Sell"
    elif "buy zone now" in text_lower:
        direction = "Buy"
    else:
        return text

    numbers = re.findall(r'\d+(?:\.\d+)?', text)
    if numbers:
        entry = " - ".join(numbers[:2]) if len(numbers) >= 2 else numbers[0]
    else:
        entry = "open"

    return (
        f"{direction} XAUUSD Now\n"
        f"\n"
        f"Entry: {entry}\n"
        f"\n"
        f"SL: open\n"
        f"\n"
        f"TP1: open\n"
        f"TP2: open\n"
        f"TP3: open"
    )


client = TelegramClient(
    os.path.join(SCRIPT_DIR, "session"),
    API_ID,
    API_HASH
)

msg_map = load_message_map()


@client.on(events.NewMessage(chats=SOURCE_CHANNEL))
async def forward_handler(event):
    try:
        modified_text = transform_signal(event.message.text or "")

        if event.message.media:
            sent = await client.send_message(
                TARGET_CHANNEL,
                modified_text,
                file=event.message.media,
                formatting_entities=event.message.entities
            )
        else:
            sent = await client.send_message(
                TARGET_CHANNEL,
                modified_text,
                formatting_entities=event.message.entities
            )

        source_key = str(event.message.id)
        msg_map[source_key] = sent.id
        save_message_map(msg_map)
        logger.info(f"Forwarded message {event.message.id} -> {sent.id}")

    except Exception as e:
        logger.error(f"Error forwarding message {event.message.id}: {e}")


@client.on(events.MessageEdited(chats=SOURCE_CHANNEL))
async def edit_handler(event):
    try:
        source_key = str(event.message.id)
        if source_key not in msg_map:
            logger.warning(f"Edit for unknown message {event.message.id}, skipping")
            return

        target_msg_id = msg_map[source_key]
        modified_text = transform_signal(event.message.text or "")

        await client.edit_message(
            TARGET_CHANNEL,
            target_msg_id,
            modified_text,
            formatting_entities=event.message.entities
        )
        logger.info(f"Synced edit for message {event.message.id} -> {target_msg_id}")

    except Exception as e:
        logger.error(f"Error syncing edit for message {event.message.id}: {e}")


async def main():
    await client.start()

    source_entity = await client.get_entity(SOURCE_CHANNEL)
    target_entity = await client.get_entity(TARGET_CHANNEL)
    logger.info(f"Source: {source_entity.title} (ID: {source_entity.id})")
    logger.info(f"Target: {target_entity.title} (ID: {target_entity.id})")
    logger.info(f"Text replacements: {REPLACEMENTS}")
    logger.info("Bot is running... Press Ctrl+C to stop.")

    await client.run_until_disconnected()


if __name__ == "__main__":
    client.loop.run_until_complete(main())
