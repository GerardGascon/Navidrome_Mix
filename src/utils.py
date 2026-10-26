from datetime import datetime, timedelta

from mix_types import Song


def today():
    return datetime.now().astimezone().date()


def week_start():
    """
    Return the Monday of the current week.
    """
    current = today()
    return current - timedelta(days=current.weekday())


def artist_key(song: Song):
    return song.artist.strip().lower()


def album_key(song: Song):
    return (
        song.artist.strip().lower(),
        song.album.strip().lower(),
    )
