from dataclasses import dataclass
from datetime import datetime, date, timedelta
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

async def get_guesses_for_timerange(start_timestamp: int, end_timestamp: int) -> List[Guess]:
    """Get all guesses between start_timestamp and end_timestamp (inclusive)."""
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
            artist_name_correct=False,  # Default to false, will be set during review
            song_title_correct=False,   # Default to false, will be set during review
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

async def update_guess_marking(guess_id: int, artist_correct: bool, title_correct: bool) -> None:
    """Update the marking for a specific guess."""
    # TODO: Implement this when needed
    pass 

async def get_todays_guess(guesser_id: int) -> Optional[str]:
    """
    Check if a user has already made a guess today.
    
    Args:
        guesser_id: The Telegram user ID of the guesser
        
    Returns:
        Optional[str]: The guess text if found for today, None otherwise
    """
    result = await db.get(
        (where('type') == "guess") & 
        (where('guesser_id') == guesser_id)
    )
    return result['guess_text'] if result else None

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
        'timestamp': int(datetime.now().timestamp())
    }) 