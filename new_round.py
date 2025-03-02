
from telegram import ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, ConversationHandler, filters
from datetime import datetime, date, timedelta

ROUND_NAME_STATE, START_DATE_STATE, DURATION_STATE, CONFIRM_CREATE_STATE = range(4)

round_name = None
round_start_date = None
round_duration = None



def new_round_conversation_handler() -> ConversationHandler:
    return ConversationHandler(
    entry_points=[CommandHandler("newround", newround_command)],
    states={
        ROUND_NAME_STATE: [
            MessageHandler(None, handle_round_name)
        ],
        START_DATE_STATE: [
            MessageHandler(None, handle_start_date)
        ],
        DURATION_STATE: [
            MessageHandler(None, handle_duration)
        ],
        CONFIRM_CREATE_STATE: [
            MessageHandler(None, handle_confirm_create)
        ]
    },
    fallbacks=[CommandHandler("cancel", cancel_command)],
    allow_reentry=True
)



async def newround_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("What is the name of the new round?")
    return ROUND_NAME_STATE



async def handle_round_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global round_name

    input = update.message.text

    if bool(input and input.strip()):
        round_name = input
        await update.message.reply_text("What date will this round start on? (dd/mm/yy)")
        return START_DATE_STATE
    else:
        await update.message.reply_text("What is the name of the new round?")
        return ROUND_NAME_STATE
        


async def handle_start_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global round_start_date

    input = update.message.text
    
    round_start_date = parse_date(input)

    if round_start_date is None:
        await update.message.reply_text("An invalid date was provided. What date will this round start on? (dd/mm/yy)")
        return START_DATE_STATE
    else:
        await update.message.reply_text("How many days will this round run for? e.g. 5")
        return DURATION_STATE
 
 

async def handle_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global round_duration

    input = update.message.text

    round_duration = parse_positive_int(input)

    if round_duration is None:
        await update.message.reply_text("An invalid number was entered. How many days will this round run for? Please enter this as a number e.g. 5")
        return DURATION_STATE
    else:
        print(round_start_date)
        end_date = get_end_date(round_start_date, round_duration)
        start_date_string = format_date_with_suffix(round_start_date)
        end_date_string = format_date_with_suffix(end_date)
                                                    
        await update.message.reply_text(f"So the round is named \"{round_name}\", will start on {start_date_string}, and will run until {end_date_string}. Is that right? (y/n)")
        return CONFIRM_CREATE_STATE



async def handle_confirm_create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    input = update.message.text

    if input == "y":
        await update.message.reply_text("All done, the new round has been created.")
    else:
        reset_variables()
        await update.message.reply_text("New round creation has been cancelled.")



async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_variables()
    await update.message.reply_text("New round creation has been cancelled.")
    return ConversationHandler.END

def reset_variables():
    global round_name, round_start_date, round_duration

    round_name = None
    round_start_date = None
    round_duration = None


def parse_date(date_string):
    """
    Convert a string in dd/mm/yy format to a datetime object.
    Returns None if the string doesn't match the format or isn't a valid date.
    """
    try:
        # Attempt to parse the string according to the format
        date_object = datetime.strptime(date_string, "%d/%m/%y")
        return date_object
    except ValueError:
        # Return None
        return None

def parse_positive_int(number_string):
    """
    Convert a string to a positive integer.
    
    Args:
        number_string (str): String representation of a number
        
    Returns:
        int: A positive integer if the string is a valid number > 0
        None: If the string is not a valid positive integer
    """
    try:
        # Attempt to convert the string to an integer
        num = int(number_string)
        
        # Check if the number is greater than zero
        if num > 0:
            return num
        else:
            return None
    except (ValueError, TypeError):
        # Return None if the conversion fails or if input is not a string
        return None



def format_date_with_suffix(date_obj):
    """
    Format a date object to display like "4th December"
    
    Args:
        date_obj: A datetime or date object
        
    Returns:
        str: Formatted date string with day suffix
    """
    # Get the day number
    day = date_obj.day
    
    # Determine the appropriate suffix
    if 11 <= day <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    
    # Format the date with the suffix
    return date_obj.strftime(f"%A %-d{suffix} %B")  # %-d removes leading zeros on Linux/Mac



def get_end_date(start_date, duration_days):
    """
    Calculate the end date of an event that starts on start_date and runs for duration_days.
    
    Args:
        start_date: A date object representing the start date
        duration_days: Number of days the event runs for
        
    Returns:
        date: The end date (inclusive of both start and end days)
    """
    # Subtract 1 from duration because the start day counts as day 1
    print(start_date)
    return start_date + timedelta(days=duration_days - 1)

# What's the first step to build the rest off?

# Allow the user to set up a round

# /newround

# What is the name of the new round?

# What date will this round start on? (dd/mm/yy):

# How many days will the new round go for?

# So the first day of the round will be Mon 1st March, and the last day will be Friday 5th March is that right? (y/n)

# The round has been created


