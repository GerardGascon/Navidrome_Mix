import os
from pathlib import Path

API_VERSION = "1.16.1"
CLIENT_NAME = "WeeklyMixGenerator"
TIMEOUT = 30

PLAYLIST_SIZE = int(os.getenv("PLAYLIST_SIZE", "155"))
MAX_PER_ARTIST = int(os.getenv("MAX_PER_ARTIST", "2"))
MAX_PER_ALBUM = int(os.getenv("MAX_PER_ALBUM", "2"))

AVOID_GENERATED_DAYS = int(os.getenv("AVOID_GENERATED_DAYS", "30"))
POOL_SIZE = int(os.getenv("POOL_SIZE", "3000"))

DAILY_PLAYLIST_PREFIX = os.getenv("DAILY_PLAYLIST_PREFIX", "Daily Mix")
WEEKLY_PLAYLIST_PREFIX = os.getenv("WEEKLY_PLAYLIST_PREFIX", "Weekly Mix")
KEEP_PLAYLIST_DAYS = int(os.getenv("KEEP_PLAYLIST_DAYS", "30"))

HISTORY_FILE = Path(os.path.abspath(os.sep)) / "data" / "history.json"