from dataclasses import dataclass
from datetime import datetime, date, timedelta, time
from typing import Optional, List
from asynctinydb import TinyDB, Query, where

# Get access to the db instance
db = TinyDB('db.json')

@dataclass
class Round:
    name: str
    start_date: date
    duration_days: int

    def end_date(self) -> date:
        """Get the end date of the round."""
        return self.start_date + timedelta(days=self.duration_days - 1)

    def overlaps_with(self, other: 'Round') -> bool:
        """Check if this round overlaps with another round."""
        return (self.start_date <= other.end_date() and 
                other.start_date <= self.end_date())

    def to_dict(self) -> dict:
        """Convert the round to a dictionary for database storage."""
        return {
            'type': 'round',
            'name': self.name,
            'start_date': self.start_date.isoformat(),
            'duration_days': self.duration_days
        }

@dataclass
class Guess:
    guesser_id: int
    guesser_name: str
    guess_text: str
    artist_name_correct: bool
    song_title_correct: bool
    timestamp: int  # seconds since epoch

# Stub data for development
_mock_rounds = [
    Round("First Round", datetime.now().date(), 5),
    Round("Second Round", datetime.now().date(), 5),
    Round("Third Round", datetime.now().date(), 5)
]

_mock_guesses = [
    Guess(1, "Alice", "never gonna give you up by rick astley", True, True, int(datetime.now().timestamp())),
    Guess(2, "Bob", "never gonna let you down by rick astley", True, False, int(datetime.now().timestamp())),
    Guess(3, "Charlie", "take on me by a-ha", False, False, int(datetime.now().timestamp()))
]

async def get_rounds() -> List[Round]:
    """Get all available rounds."""
    rounds_query = Query()
    results = await db.search(rounds_query.type == "round")
    return [
        Round(
            name=r['name'],
            start_date=date.fromisoformat(r['start_date']),
            duration_days=r['duration_days']
        ) for r in results
    ]

def get_game_day_timestamps(target_date: date, current_time: Optional[time] = None) -> tuple[int, int]:
    """
    Get the start and end timestamps for a game day.
    A game day starts and ends at first_clue_time (6 AM).
    
    Args:
        target_date: The date to get timestamps for
        current_time: Optional current time to determine if we're before/after first_clue_time
                     If not provided, assumes we want the full game day for target_date
    
    Returns:
        tuple[int, int]: (start_timestamp, end_timestamp) in seconds since epoch
    """
    if current_time and current_time < first_clue_time:
        # If it's before 6 AM, we're still in the previous game day
        start_date = target_date - timedelta(days=1)
    else:
        start_date = target_date
        
    start_timestamp = int(datetime.combine(start_date, first_clue_time).timestamp())
    end_timestamp = int(datetime.combine(start_date + timedelta(days=1), first_clue_time).timestamp())
    return start_timestamp, end_timestamp

async def marked_guesses_for_day(target_date: date, song_title: str, artist_name: str) -> List[Guess]:
    """
    Get all guesses made on a specific day and mark them against the correct song.
    A day starts at first_clue_time (6 AM) and ends at first_clue_time the next day.
    
    Args:
        target_date: The date to get guesses for
        song_title: The correct song title to check guesses against
        artist_name: The correct artist name to check guesses against
        
    Returns:
        List[Guess]: List of guesses made on that day, marked for correctness
    """
    start_timestamp, end_timestamp = get_game_day_timestamps(target_date)
    
    guesses_query = Query()
    results = await db.search(
        (guesses_query.type == "guess") & 
        (guesses_query.timestamp >= start_timestamp) & 
        (guesses_query.timestamp <= end_timestamp)
    )
    return [
        Guess(
            guesser_id=g['guesser_id'],
            guesser_name=g['guesser_name'],
            guess_text=g['guess_text'],
            artist_name_correct=artist_name.lower() in g['guess_text'].lower(),
            song_title_correct=song_title.lower() in g['guess_text'].lower(),
            timestamp=int(g['timestamp'])
        ) for g in results
    ]

async def save_round(round: Round) -> bool:
    """
    Save a new round.
    
    Args:
        round: The round to save
        
    Returns:
        bool: True if the round was saved successfully, False if there was an overlap
    """
    # Check for overlaps with existing rounds
    existing_rounds = await get_rounds()
    for existing_round in existing_rounds:
        if round.overlaps_with(existing_round):
            return False
            
    # Save the round to the database
    await db.insert(round.to_dict())
    return True

async def create_guess(guesser_id: int, guesser_name: str, guess_text: str) -> None:
    """
    Create a new guess in the database.
    
    Args:
        guesser_id: The Telegram user ID of the guesser
        guesser_name: The full name of the guesser
        guess_text: The text of their guess
    """
    await db.insert({
        'type': 'guess',
        'guesser_id': guesser_id,
        'guesser_name': guesser_name,
        'guess_text': guess_text,
        'timestamp': int(datetime.now().timestamp()),
        'artist_name_correct': None,  # Initially None until reviewed
        'song_title_correct': None    # Initially None until reviewed
    })

async def get_todays_guess(guesser_id: int) -> Optional[str]:
    """
    Check if a user has already made a guess for the current game day.
    A game day starts and ends at first_clue_time (6 AM).
    
    Args:
        guesser_id: The Telegram user ID of the guesser
        
    Returns:
        Optional[str]: The guess text if found for the current game day, None otherwise
    """
    now = datetime.now()
    start_timestamp, end_timestamp = get_game_day_timestamps(now.date(), now.time())
    
    result = await db.get(
        (where('type') == "guess") & 
        (where('guesser_id') == guesser_id) &
        (where('timestamp') >= start_timestamp) &
        (where('timestamp') <= end_timestamp)
    )
    return result['guess_text'] if result else None 

async def update_guesses_marking(guesses: List[Guess]) -> None:
    """
    Update the marking for multiple guesses at once.
    
    Args:
        guesses: List of Guess objects with updated marking information
    """
    for guess in guesses:
        guesses_query = Query()
        await db.update(
            {
                'artist_name_correct': guess.artist_name_correct,
                'song_title_correct': guess.song_title_correct
            },
            (guesses_query.type == "guess") & 
            (guesses_query.guesser_id == guess.guesser_id) &
            (guesses_query.guess_text == guess.guess_text)  # Additional check to ensure we update the correct guess
        ) 