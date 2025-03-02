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

from new_round import new_round_conversation_handler
from review import review_conversation_handler



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

# Define a few command handlers. These usually take the two arguments update and
# context.
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}!",
        reply_markup=ForceReply(selective=True),
    )



def full_name_from_update(update) -> str:
    full_name = update.effective_user.first_name
    
    if update.effective_user.last_name:
        full_name += " " + update.effective_user.last_name

    return full_name



async def guess_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Forward the guess to the guesses channel
    await context.bot.forward_message(chat_id=GUESSES_CHANNEL_ID,
                                from_chat_id=update.message.from_user.id,
                                message_id=update.message.message_id)

    result = await db.get((where('user_id') == update.effective_user.id) & (where('type') == "guess"))
    
    if not result:
        await record_and_respond_to_guess(update)
    else:
        guess = result['guess']
        await update.message.reply_text(f"You have already made a guess today. Your guess was: {guess}")



async def record_and_respond_to_guess(update):
    guess = update.message.text.replace("/guess ", "", 1)
    full_name = full_name_from_update(update)

    # Store the guess in the db
    await db.insert({ 'type': 'guess', 
            'username': update.effective_user.username,
            'full_name': full_name,
            'user_id': update.effective_user.id, 
            'date': update.message.date.timestamp(),
            'guess': guess })

    # Let the user know their guess has been recorded
    await update.message.reply_text(f"Your guess: \"{guess}\" has been recorded. Thanks for playing!")
    # print(f"username: {update.message.from_user.username}, chat_id: {update.message.from_user.id}, date: {update.message.date.timestamp()}")
    
    
async def guesses_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    guesses = Query()
    results = await db.search(guesses.type == "guess")
    print(results)
    for document in results:
        print(document['guess'])

async def wipe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await db.truncate()
    await update.message.reply_text("The database has been wiped")


async def no_command_issued(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"To make a guess, use the /guess command e.g. \"/guess never gonna give you up by rick astley\"")


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelling")



def main() -> None:
    print("is the b bot actualy running?")
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TOKEN).build()

    # on different commands - answer in Telegram
    # application.add_handler(CommandHandler("add_to_guesses_channel", add_to_guesses_channel))
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("guess", guess_command))
    application.add_handler(CommandHandler("guesses", guesses_command))

    # TODO: REMOVE BEFORE LAUNCH THIS IS A BAD COMMAND!!!
    application.add_handler(CommandHandler("wipe", wipe_command))


    application.add_handler(new_round_conversation_handler())
    application.add_handler(review_conversation_handler())

    # on non command i.e message - echo the message on Telegram
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, no_command_issued))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()


