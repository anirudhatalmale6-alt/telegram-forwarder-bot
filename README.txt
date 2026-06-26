TELEGRAM FORWARDING BOT
=======================

This bot automatically forwards messages from a source Telegram channel
to your target channel, replacing text as configured.

Features:
- Forwards all new messages (text, photos, videos, documents)
- Replaces "Sell Zone Now" -> "Sell XAUUSD Now"
- Replaces "Buy Zone Now" -> "Buy XAUUSD Now"
- Syncs edits from source to target automatically
- Runs 24/7 in the background


SETUP (Windows)
===============

1. Install Python 3.10+ from https://python.org
   (Check "Add Python to PATH" during install)

2. Open Command Prompt in this folder and run:
   pip install -r requirements.txt

3. Edit config.ini:
   - source = the source channel username (without @) or numeric ID
   - target = your target channel username (without @) or numeric ID
   - Add or change text replacements as needed

4. Run the bot:
   python bot.py

5. First time only: you'll be asked to enter your phone number
   and a login code from Telegram. After that, the session is saved.

6. The bot will print "Bot is running..." when ready.


CONFIGURATION
=============

Open config.ini in any text editor:

  [channels]
  source = goldscalpingchannel
  target = mychannelname

  [text_replacements]
  Sell Zone Now = Sell XAUUSD Now
  Buy Zone Now = Buy XAUUSD Now
  Some Other Text = My Replacement

You can add as many replacement rules as you want.
Just add a new line: original text = replacement text


RUNNING IN BACKGROUND (Windows)
================================

Option A - Use the included start_bot.vbs:
  Double-click start_bot.vbs to run the bot hidden in the background.

Option B - Task Scheduler:
  1. Open Task Scheduler
  2. Create Basic Task
  3. Set trigger to "When the computer starts"
  4. Action: Start a program
  5. Program: python
  6. Arguments: bot.py
  7. Start in: (this folder path)


STOPPING THE BOT
=================

If running in foreground: Press Ctrl+C
If running via VBS: Open Task Manager, find python.exe, end task


LOGS
====

Check bot.log in this folder for activity and any errors.
