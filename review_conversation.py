from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    ConversationHandler,
    filters,
)
from datetime import datetime, timedelta, date
from typing import Optional, List
from dataclasses import dataclass
from data import Round, Guess, get_rounds, guesses_for_day

@dataclass
class Review:
    """Represents the state of a review conversation."""
    artist_name: Optional[str]
    song_title: Optional[str]
    day_to_review: Optional[date]

# Define conversation states
ROUND_NUMBER_STATE, DAY_NUMBER_STATE, ARTIST_NAME_STATE, SONG_TITLE_STATE, FIX_MARKING_STATE, REMARK_ARTIST_NAME_STATE, REMARK_SONG_TITLE_STATE = range(7)

def get_days_for_round(round: Round) -> List[datetime]:
    """Generate list of dates for a round based on start date and duration."""
    return [round.start_date + timedelta(days=x) for x in range(round.duration_days)]

def parse_int_option(input_text: str, max_value: int) -> Optional[int]:
    """
    Parse and validate an integer option from user input.
    Returns the validated integer (1-based) or None if invalid.
    """
    try:
        num = int(input_text)
        return num if 1 <= num <= max_value else None
    except ValueError:
        return None

def review_conversation_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("review", review_command)],
        states={
            ROUND_NUMBER_STATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_round_number)
            ],
            DAY_NUMBER_STATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_day_number)
            ],
            ARTIST_NAME_STATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_artist_name)
            ],
            SONG_TITLE_STATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_song_title)
            ],
            FIX_MARKING_STATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_fix_marking),
                CommandHandler("done", done_command)
            ],
            REMARK_ARTIST_NAME_STATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_remark_artist_name)
            ],
            REMARK_SONG_TITLE_STATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_remark_song_title)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_command)],
        allow_reentry=True
    )

async def review_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Entry point for the review conversation.
    Gets available rounds from data layer and displays them to user.
    """
    rounds = get_rounds()
    
    # Initialize empty review
    context.user_data['current_review'] = Review(
        artist_name=None,
        song_title=None,
        day_to_review=None
    )
    
    # Format rounds into numbered list
    rounds_text = f"Which round would you like to review? (1-{len(rounds)})\n"
    rounds_text += "\n".join(f"{i+1}. {round.name}" for i, round in enumerate(rounds))
    
    context.user_data['rounds'] = rounds
    await update.message.reply_text(rounds_text)
    return ROUND_NUMBER_STATE

async def handle_round_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles the user's round selection.
    Validates input and shows available days for selected round.
    """
    input_text = update.message.text
    rounds = context.user_data.get('rounds', [])
    
    round_num = parse_int_option(input_text, len(rounds))
    if round_num is None:
        await update.message.reply_text(f"Please enter a valid round number (1-{len(rounds)})")
        return ROUND_NUMBER_STATE
    
    selected_round = rounds[round_num - 1]
    context.user_data['selected_round'] = selected_round
    
    # Get days for the selected round
    days = get_days_for_round(selected_round)
    context.user_data['round_days'] = days
    
    # Format days into numbered list
    days_text = f"Which day do you want to review? (1-{len(days)})\n"
    days_text += "\n".join(f"{i+1}. {day.strftime('%A')}" for i, day in enumerate(days))
    
    await update.message.reply_text(days_text)
    return DAY_NUMBER_STATE

async def handle_day_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles the user's day selection.
    Validates input and stores the selected day.
    """
    input_text = update.message.text
    days = context.user_data.get('round_days', [])
    
    day_num = parse_int_option(input_text, len(days))
    if day_num is None:
        await update.message.reply_text(f"Please enter a valid day number (1-{len(days)})")
        return DAY_NUMBER_STATE
    
    selected_day = days[day_num - 1]
    
    current_review = context.user_data['current_review']
    current_review.day_to_review = selected_day.date()
    
    await update.message.reply_text(f"What was the artist name for {selected_day.strftime('%A')}?")
    return ARTIST_NAME_STATE

async def handle_artist_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles the user's artist name input.
    Validates it's not empty and stores it.
    """
    input_text = update.message.text
    
    if not input_text or not input_text.strip():
        await update.message.reply_text("Please enter an artist name")
        return ARTIST_NAME_STATE
    
    current_review = context.user_data['current_review']
    current_review.artist_name = input_text.strip()
    day_name = current_review.day_to_review.strftime('%A')
    await update.message.reply_text(f"What was the song title for {day_name}?")
    return SONG_TITLE_STATE

async def handle_song_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles the user's song title input.
    Validates input, stores it, and displays the review results.
    """
    input_text = update.message.text
    
    if not input_text or not input_text.strip():
        await update.message.reply_text("Please enter a song title")
        return SONG_TITLE_STATE
    
    current_review = context.user_data['current_review']
    current_review.song_title = input_text.strip()
    
    # Get guesses for the day
    guesses = await guesses_for_day(current_review.day_to_review)
    
    # Store guesses for fixing marking mistakes
    context.user_data['current_guesses'] = guesses
    
    await send_review_message(update, context)
    return FIX_MARKING_STATE

async def send_review_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Helper function to format and send the review message."""
    current_review = context.user_data['current_review']
    guesses = context.user_data['current_guesses']
    
    day_name = current_review.day_to_review.strftime('%A')
    review_text = f"Review for {day_name}:\n"
    review_text += f"Correct Answer: {current_review.song_title} by {current_review.artist_name}\n\n"
    review_text += "Guesses:\n"
    
    for i, guess in enumerate(guesses, 1):
        artist_mark = "✅" if guess.artist_name_correct else "❌"
        title_mark = "✅" if guess.song_title_correct else "❌"
        review_text += f"{i}. {guess.guess_text}\n   {title_mark} Title {artist_mark} Artist ({guess.guesser_name})\n\n"
    
    review_text += f"Enter a guess number to fix any mistakes in marking (1-{len(guesses)}), or enter /done to complete"
    await update.message.reply_text(review_text)

async def handle_fix_marking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles fixing marking mistakes for a specific guess.
    """
    input_text = update.message.text
    guesses = context.user_data.get('current_guesses', [])
    guess_num = parse_int_option(input_text, len(guesses))
    
    if guess_num is None:
        await update.message.reply_text(f"Please enter a valid guess number (1-{len(guesses)}) or /done")
        return FIX_MARKING_STATE
    
    # Store the selected guess number for the remark handler
    context.user_data['selected_guess_num'] = guess_num
    guess = guesses[guess_num - 1]
    
    await update.message.reply_text(f"Did {guess.guesser_name} get the artist correct? (y/n)")
    return REMARK_ARTIST_NAME_STATE

async def handle_remark_artist_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles the user's response about whether the artist name was correct.
    Only accepts 'y' or 'n' as valid inputs.
    """
    input_text = update.message.text.lower()
    
    if input_text not in ['y', 'n']:
        await update.message.reply_text("Please enter 'y' for yes or 'n' for no")
        return REMARK_ARTIST_NAME_STATE
        
    if input_text == 'n':
        guess_num = context.user_data['selected_guess_num']
        guesses = context.user_data['current_guesses']
        guess = guesses[guess_num - 1]
        guess.artist_name_correct = False
    
    # Ask about song title next
    guess_num = context.user_data['selected_guess_num']
    guesses = context.user_data['current_guesses']
    guess = guesses[guess_num - 1]
    await update.message.reply_text(f"Did {guess.guesser_name} get the song title correct? (y/n)")
    return REMARK_SONG_TITLE_STATE

async def handle_remark_song_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles the user's response about whether the song title was correct.
    Only accepts 'y' or 'n' as valid inputs.
    """
    input_text = update.message.text.lower()
    
    if input_text not in ['y', 'n']:
        await update.message.reply_text("Please enter 'y' for yes or 'n' for no")
        return REMARK_SONG_TITLE_STATE
        
    if input_text == 'n':
        guess_num = context.user_data['selected_guess_num']
        guesses = context.user_data['current_guesses']
        guess = guesses[guess_num - 1]
        guess.song_title_correct = False
    
    current_review = context.user_data['current_review']
    day_name = current_review.day_to_review.strftime('%A')
    await update.message.reply_text(f"Here's the updated marking for {day_name}:")
    await send_review_message(update, context)
    return FIX_MARKING_STATE

async def done_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Completes the review process."""
    context.user_data['current_review'] = None
    context.user_data['current_guesses'] = None
    await update.message.reply_text("Review completed.")
    return ConversationHandler.END

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancels and ends the review conversation."""
    context.user_data['current_review'] = None
    await update.message.reply_text("Review cancelled.")
    return ConversationHandler.END 