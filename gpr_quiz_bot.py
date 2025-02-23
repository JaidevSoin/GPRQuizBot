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
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

GUESSES_CHANNEL_ID = -1002318487709

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

# Define a few command handlers. These usually take the two arguments update and
# context.
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}!",
        reply_markup=ForceReply(selective=True),
    )
    
async def guess_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Forward the guess to the guesses channel
    await context.bot.forward_message(chat_id=GUESSES_CHANNEL_ID,
                                from_chat_id=update.message.from_user.id,
                                message_id=update.message.message_id)
    
    guess = update.message.text.replace("/guess ", "", 1)

    # Let the user know their guess has been recorded
    await update.message.reply_text(f"Your guess: \"{guess}\" has been recorded :)")


def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TOKEN).build()

    # on different commands - answer in Telegram
    # application.add_handler(CommandHandler("add_to_guesses_channel", add_to_guesses_channel))
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("guess", guess_command))

    # on non command i.e message - echo the message on Telegram
    # application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()