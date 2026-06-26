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

    lines = [l.strip() for l in text.strip().split("\n") if l.strip()]

    entry = "open"
    sl = "open"
    tp1 = "open"
    tp2 = "open"
    tp3 = "open"

    entry_match = re.search(r'(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)', text)
    if entry_match:
        entry = entry_match.group(1)
    else:
        single_num = None
        for line in lines:
            if line.lower().startswith(("sell", "buy")):
                continue
            nums = re.findall(r'\d+(?:\.\d+)?', line)
            if nums and not re.search(r'(target|sl)', line, re.IGNORECASE):
                single_num = nums[0]
                break
        if single_num:
            entry = single_num

    sl_match = re.search(r'SL[/\s]*(?:invalid)?\s*(\d+(?:\.\d+)?)', text, re.IGNORECASE)
    if sl_match:
        sl = sl_match.group(1)

    targets = []
    in_targets = False
    for line in lines:
        if line.lower().startswith("target"):
            in_targets = True
            nums = re.findall(r'\d+(?:\.\d+)?', line)
            targets.extend(nums)
            continue
        if in_targets:
            nums = re.findall(r'\d+(?:\.\d+)?', line)
            if nums and not re.search(r'SL', line, re.IGNORECASE):
                targets.extend(nums)
            else:
                in_targets = False

    if len(targets) >= 1:
        tp1 = targets[0]
    if len(targets) >= 2:
        tp2 = targets[1]
    if len(targets) >= 3:
        tp3 = targets[2]

    result = (
        f"{direction} XAUUSD Now\n"
        f"\n"
        f"Entry: {entry}\n"
        f"\n"
        f"TP1: {tp1}\n"
        f"TP2: {tp2}\n"
        f"TP3: {tp3}\n"
        f"\n"
        f"SL: {sl}"
    )

    result = re.sub(r'@\w+', '@JasonBlatter', result)
    return result


client = TelegramClient(
    os.path.join(SCRIPT_DIR, "session"),
    API_ID,
    API_HASH
)

msg_map = load_message_map()


@client.on(events.NewMessage(chats=SOURCE_CHANNEL))
async def forward_handler(event):
    try:
        if event.message.media:
            logger.info(f"Skipping message {event.message.id} (has media/photo)")
            return

        modified_text = transform_signal(event.message.text or "")

        sent = await client.send_message(
            TARGET_CHANNEL,
            modified_text
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
