from datetime import datetime, timedelta

import globals
from mix_types import Song


def today():
    return datetime.now().astimezone().date()


def week_start():
    """
    Return the Monday of the current week.
    """
    current = today()
    return current - timedelta(days=current.weekday())


def playlist_name(mode, frequency):
    if frequency == "daily":
        prefix = globals.DAILY_PLAYLIST_PREFIX
    elif frequency == "weekly":
        prefix = globals.WEEKLY_PLAYLIST_PREFIX
    else:
        raise ValueError(f"Unknown frequency: {frequency}")

    return f"{prefix} — {mode}"


def artist_key(song: Song):
    return song.artist.strip().lower()


def album_key(song: Song):
    return (
        song.artist.strip().lower(),
        song.album.strip().lower(),
    )
