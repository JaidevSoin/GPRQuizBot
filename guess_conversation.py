from telegram import Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)
from asynctinydb import Query, where
from data import create_guess, get_todays_guess

# Channel ID for forwarding guesses
GUESSES_CHANNEL_ID = -1002318487709

def name_from_update(update: Update) -> str:
    """Extract the full name from a Telegram update."""
    name = update.effective_user.first_name
    
    if update.effective_user.last_name:
        name += " " + update.effective_user.last_name

    return name

async def guess_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /guess command."""
    # Forward the guess to the guesses channel
    await context.bot.forward_message(
        chat_id=GUESSES_CHANNEL_ID,
        from_chat_id=update.message.from_user.id,
        message_id=update.message.message_id
    )

    # Check if user has already guessed today
    existing_guess = await get_todays_guess(update.effective_user.id)
    
    if existing_guess is None:
        await record_and_respond_to_guess(update)
    else:
        await update.message.reply_text(
            f"You have already made a guess today. Your guess was: {existing_guess}"
        )

async def record_and_respond_to_guess(update: Update) -> None:
    """Record a user's guess and send confirmation."""
    guess = update.message.text.replace("/guess ", "", 1)
    name = name_from_update(update)

    # Store the guess in the db
    await create_guess(
        guesser_id=update.effective_user.id,
        guesser_name=name,
        guess_text=guess
    )

    # Let the user know their guess has been recorded
    await update.message.reply_text(
        f"Your guess: \"{guess}\" has been recorded. Thanks for playing!"
    )

def guess_conversation_handler() -> CommandHandler:
    """Create and return the guess command handler."""
    return CommandHandler("guess", guess_command) 