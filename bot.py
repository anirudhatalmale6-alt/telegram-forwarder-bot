import configparser
import asyncio
import logging
import os
import json
import re
from telethon import TelegramClient
from telethon.tl.types import MessageMediaWebPage

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

SOURCE_CHANNELS_RAW = config.get("channels", "source")
TARGET_CHANNEL = config.get("channels", "target")

SOURCE_CHANNELS = []
for ch in SOURCE_CHANNELS_RAW.split(","):
    ch = ch.strip()
    try:
        SOURCE_CHANNELS.append(int(ch))
    except ValueError:
        SOURCE_CHANNELS.append(ch)

try:
    TARGET_CHANNEL = int(TARGET_CHANNEL)
except ValueError:
    pass


def load_message_map():
    if os.path.exists(MAP_PATH):
        with open(MAP_PATH, "r") as f:
            return json.load(f)
    return {}


def save_message_map(data):
    with open(MAP_PATH, "w") as f:
        json.dump(data, f)


def transform_signal(text):
    if not text:
        return text

    text_lower = text.lower()

    if text_lower.startswith("sell"):
        direction = "Sell"
    elif text_lower.startswith("buy"):
        direction = "Buy"
    else:
        result = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', text)
        result = re.sub(r'@\w+', '@JasonBlatter', result)
        result = re.sub(r'https?://\S+', '', result)
        result = re.sub(r'www\.\S+', '', result)
        result = re.sub(r't\.me/\S+', '', result)
        result = re.sub(r'\n\s*\n\s*\n', '\n\n', result).strip()
        return result

    lines = [l.strip() for l in text.strip().split("\n") if l.strip()]

    entry = "4000"
    sl = "open"
    tp1 = "open"
    tp2 = "open"
    tp3 = "open"

    entry_match = re.search(r'(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)', text)
    if entry_match:
        entry = f"{entry_match.group(1)} - {entry_match.group(2)}"

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
msg_texts = {}
source_entities = []
target_entity = None
last_seen = {}


async def forward_message(msg):
    source_key = str(msg.id)

    if msg.media and not isinstance(msg.media, MessageMediaWebPage):
        logger.info(f"Skipping message {msg.id} (has media)")
        return

    modified_text = transform_signal(msg.text or "")
    if not modified_text.strip():
        logger.info(f"Skipping message {msg.id} (empty after transformation)")
        return

    reply_to_target = None
    if msg.reply_to and msg.reply_to.reply_to_msg_id:
        reply_source_key = str(msg.reply_to.reply_to_msg_id)
        if reply_source_key in msg_map:
            reply_to_target = msg_map[reply_source_key]
            logger.info(f"Replying to target message {reply_to_target}")

    sent = await client.send_message(
        target_entity,
        modified_text,
        reply_to=reply_to_target,
        link_preview=False
    )

    msg_map[source_key] = sent.id
    msg_texts[source_key] = msg.text
    save_message_map(msg_map)
    logger.info(f"Forwarded message {msg.id} -> {sent.id}")


async def sync_edit(msg):
    source_key = str(msg.id)
    target_msg_id = msg_map[source_key]

    modified_text = transform_signal(msg.text or "")
    if not modified_text.strip():
        return

    await client.edit_message(target_entity, target_msg_id, modified_text)
    msg_texts[source_key] = msg.text
    logger.info(f"Synced edit for message {msg.id} -> {target_msg_id}")


async def poll_loop():
    while True:
        await asyncio.sleep(2)
        for entity in source_entities:
            try:
                messages = []
                async for msg in client.iter_messages(entity, limit=5):
                    messages.append(msg)

                for msg in reversed(messages):
                    source_key = str(msg.id)

                    if msg.id <= last_seen.get(entity.id, 0):
                        if source_key in msg_map and source_key in msg_texts:
                            if msg_texts[source_key] != msg.text:
                                try:
                                    await sync_edit(msg)
                                except Exception as e:
                                    logger.error(f"Error syncing edit: {e}")
                        continue

                    last_seen[entity.id] = msg.id

                    if source_key in msg_map:
                        msg_texts[source_key] = msg.text
                        continue

                    try:
                        await forward_message(msg)
                    except Exception as e:
                        logger.error(f"Error forwarding message {msg.id}: {e}")

            except Exception as e:
                logger.error(f"Error polling source {entity.id}: {e}")


async def main():
    global target_entity

    await client.start()

    target_entity = await client.get_entity(TARGET_CHANNEL)
    logger.info(f"Target: {target_entity.title} (ID: {target_entity.id})")

    for src in SOURCE_CHANNELS:
        try:
            entity = await client.get_entity(src)
            source_entities.append(entity)
            logger.info(f"Source: {entity.title} (ID: {entity.id})")
        except Exception as e:
            logger.error(f"Could not resolve source {src}: {e}")

    for entity in source_entities:
        try:
            async for msg in client.iter_messages(entity, limit=1):
                last_seen[entity.id] = msg.id
                logger.info(f"  Starting from message ID: {msg.id}")
        except Exception as e:
            logger.error(f"Error initializing source {entity.id}: {e}")

    logger.info("Bot is running (polling mode)... Press Ctrl+C to stop.")
    await poll_loop()


if __name__ == "__main__":
    client.loop.run_until_complete(main())
