import os
from pathlib import Path

API_VERSION = "1.16.1"
CLIENT_NAME = "WeeklyMixGenerator"
TIMEOUT = 30

PLAYLIST_SIZE = int(os.getenv("PLAYLIST_SIZE", "50"))
MAX_PER_ARTIST = int(os.getenv("MAX_PER_ARTIST", "2"))
MAX_PER_ALBUM = int(os.getenv("MAX_PER_ALBUM", "1"))

SONG_MIN_LENGTH = int(os.getenv("SONG_MIN_LENGTH", "60"))
AVOID_GENERATED_DAYS = int(os.getenv("AVOID_GENERATED_DAYS", "30"))
POOL_SIZE = int(os.getenv("POOL_SIZE", "3000"))

HISTORY_FILE = Path(os.path.abspath(os.sep)) / "data" / "history.json"
CONFIG_FILE = Path(os.path.abspath(os.sep)) / "data" / "config.yaml"
