#!/usr/bin/env python
# pylint: disable=unused-argument
# This program is dedicated to the public domain under the CC0 license.

"""
Simple Bot to reply to Telegram messages.

First, a few handler functions are defined. Then, those functions are passed to
the Application and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.

Usage:
Basic Echobot example, repeats messages.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

import logging
import os

from telegram import ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, ConversationHandler, filters
from asynctinydb import TinyDB, UUID, IncreID, Document, Query, where

from new_round_conversation import new_round_conversation_handler
from review_conversation import review_conversation_handler
from guess_conversation import guess_conversation_handler

GUESSES_CHANNEL_ID = -1002318487709

db = TinyDB('db.json')

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Load the API token
with open(os.path.dirname(os.path.realpath(__file__)) + '/api_token.txt') as file:
    TOKEN = file.readline().strip()



async def wipe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await db.truncate()
    await update.message.reply_text("The database has been wiped")


async def no_command_issued(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"To make a guess, use the /guess command e.g. \"/guess never gonna give you up by rick astley\"")


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelling")



def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TOKEN).build()

    # Store db in bot_data for access in conversation handlers
    application.bot_data['db'] = db

    # Add handlers
    application.add_handler(CommandHandler("wipe", wipe_command))  # TODO: Remove before launch
    application.add_handler(new_round_conversation_handler())
    application.add_handler(review_conversation_handler())
    application.add_handler(guess_conversation_handler())

    # Handle non-command messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, no_command_issued))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()


