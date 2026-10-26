from datetime import datetime, timezone, timedelta
import globals


def generated_recently(song_id, history):
    cutoff = datetime.now(timezone.utc) - timedelta(days=globals.AVOID_GENERATED_DAYS)

    timestamp = history.get("tracks", {}).get(song_id)

    if not timestamp:
        return False

    try:
        played = datetime.fromisoformat(timestamp)
    except ValueError:
        return False

    return played >= cutoff


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


def normalize_song(song):
    """
    Make sure fields we depend on always exist.
    """

    song = dict(song)

    song.setdefault("id", "")
    song.setdefault("title", "Unknown Title")
    song.setdefault("artist", "Unknown Artist")
    song.setdefault("album", "Unknown Album")
    song.setdefault("playCount", 0)

    return song


def song_key(song):
    return song["id"]


def artist_key(song):
    return song.get("artist", "").strip().lower()


def album_key(song):
    return (
        song.get("artist", "").strip().lower(),
        song.get("album", "").strip().lower(),
    )
