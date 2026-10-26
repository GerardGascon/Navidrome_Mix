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
