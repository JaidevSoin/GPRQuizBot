from telegram import ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, ConversationHandler, filters
from datetime import datetime, date, timedelta
from data import Round, save_round

ROUND_NAME_STATE, START_DATE_STATE, DURATION_STATE, CONFIRM_CREATE_STATE = range(4)

def new_round_conversation_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("newround", newround_command)],
        states={
            ROUND_NAME_STATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_round_name)
            ],
            START_DATE_STATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_start_date)
            ],
            DURATION_STATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_duration)
            ],
            CONFIRM_CREATE_STATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_confirm_create)
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel_command)],
        allow_reentry=True
    )

async def newround_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the new round creation process."""
    # Initialize empty round
    context.user_data['new_round'] = Round(
        name="",
        start_date=datetime.now(),  # Placeholder, will be updated
        duration_days=0  # Placeholder, will be updated
    )
    await update.message.reply_text("What is the name of the new round?")
    return ROUND_NAME_STATE

async def handle_round_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the round name input."""
    input_text = update.message.text

    if not input_text or not input_text.strip():
        await update.message.reply_text("What is the name of the new round?")
        return ROUND_NAME_STATE

    round_data = context.user_data['new_round']
    round_data.name = input_text.strip()
    await update.message.reply_text("What date will this round start on? (dd/mm/yy)")
    return START_DATE_STATE

async def handle_start_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the start date input."""
    input_text = update.message.text
    
    start_date = parse_date(input_text)
    if start_date is None:
        await update.message.reply_text("An invalid date was provided. What date will this round start on? (dd/mm/yy)")
        return START_DATE_STATE

    round_data = context.user_data['new_round']
    round_data.start_date = start_date
    await update.message.reply_text("How many days will this round run for? e.g. 5")
    return DURATION_STATE

async def handle_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the duration input."""
    input_text = update.message.text
    duration = parse_positive_int(input_text)

    if duration is None:
        await update.message.reply_text("An invalid number was entered. How many days will this round run for? Please enter this as a number e.g. 5")
        return DURATION_STATE

    round_data = context.user_data['new_round']
    round_data.duration_days = duration
    
    # Get the round details for confirmation
    end_date = get_end_date(round_data.start_date, duration)
    start_date_string = format_date_with_suffix(round_data.start_date)
    end_date_string = format_date_with_suffix(end_date)
                                                
    await update.message.reply_text(
        f"So the round is named \"{round_data.name}\", "
        f"will start on {start_date_string}, and will run until {end_date_string}. "
        f"Is that right? (y/n)"
    )
    return CONFIRM_CREATE_STATE

async def handle_confirm_create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the confirmation input and create the round if confirmed."""
    input_text = update.message.text.lower()

    if input_text == "y":
        # Try to save the round
        round_data = context.user_data['new_round']
        if save_round(round_data):
            # Clean up and confirm
            context.user_data['new_round'] = None
            await update.message.reply_text("All done, the new round has been created.")
            return ConversationHandler.END
        else:
            # Save failed due to overlap
            context.user_data['new_round'] = None
            await update.message.reply_text(
                "Unable to create round: the dates overlap with an existing round. "
                "Please try again with different dates using the /newround command."
            )
            return ConversationHandler.END
    else:
        # Clean up and cancel
        context.user_data['new_round'] = None
        await update.message.reply_text("New round creation has been cancelled.")
        return ConversationHandler.END

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the new round creation process."""
    context.user_data['new_round'] = None
    await update.message.reply_text("New round creation has been cancelled.")
    return ConversationHandler.END

def parse_date(date_string: str) -> datetime | None:
    """
    Convert a string in dd/mm/yy format to a datetime object.
    Returns None if the string doesn't match the format or isn't a valid date.
    """
    try:
        return datetime.strptime(date_string, "%d/%m/%y")
    except ValueError:
        return None

def parse_positive_int(number_string: str) -> int | None:
    """
    Convert a string to a positive integer.
    
    Args:
        number_string: String representation of a number
        
    Returns:
        A positive integer if the string is a valid number > 0
        None if the string is not a valid positive integer
    """
    try:
        num = int(number_string)
        return num if num > 0 else None
    except (ValueError, TypeError):
        return None

def format_date_with_suffix(date_obj: datetime) -> str:
    """
    Format a date object to display like "4th December"
    
    Args:
        date_obj: A datetime or date object
        
    Returns:
        Formatted date string with day suffix
    """
    day = date_obj.day
    
    # Determine the appropriate suffix
    if 11 <= day <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    
    # Format the date with the suffix
    return date_obj.strftime(f"%A %-d{suffix} %B")  # %-d removes leading zeros on Linux/Mac

def get_end_date(start_date: datetime, duration_days: int) -> datetime:
    """
    Calculate the end date of an event that starts on start_date and runs for duration_days.
    
    Args:
        start_date: A date object representing the start date
        duration_days: Number of days the event runs for
        
    Returns:
        The end date (inclusive of both start and end days)
    """
    return start_date + timedelta(days=duration_days - 1)
