#!/usr/bin/env python3

import hashlib
import json
import math
import os
import random
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

# THIS IS A TEST 2
# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

NAVIDROME_URL = os.getenv("NAVIDROME_URL", "http://127.0.0.1:4533").rstrip("/")
NAVIDROME_USER = os.environ["NAVIDROME_USER"]
NAVIDROME_PASSWORD = os.environ["NAVIDROME_PASSWORD"]

PLAYLIST_SIZE = int(os.getenv("PLAYLIST_SIZE", "40"))
MAX_PER_ARTIST = int(os.getenv("MAX_PER_ARTIST", "2"))
MAX_PER_ALBUM = int(os.getenv("MAX_PER_ALBUM", "2"))

AVOID_GENERATED_DAYS = int(os.getenv("AVOID_GENERATED_DAYS", "14"))
POOL_SIZE = int(os.getenv("POOL_SIZE", "3000"))

DAILY_PLAYLIST_PREFIX = os.getenv("DAILY_PLAYLIST_PREFIX", "Daily Mix")
WEEKLY_PLAYLIST_PREFIX = os.getenv("WEEKLY_PLAYLIST_PREFIX", "Weekly Mix")
KEEP_PLAYLIST_DAYS = int(os.getenv("KEEP_PLAYLIST_DAYS", "30"))
WEEKLY_PLAYLISTS = True

APP_DIR = Path(__file__).resolve().parent
HISTORY_FILE = APP_DIR / "history.json"

API_VERSION = "1.16.1"
CLIENT_NAME = "WeeklyMixGenerator"
TIMEOUT = 30


# ---------------------------------------------------------------------------
# Navidrome client
# ---------------------------------------------------------------------------

class Navidrome:
    def __init__(self):
        self.base_url = NAVIDROME_URL
        self.username = NAVIDROME_USER
        self.password = NAVIDROME_PASSWORD

    def _auth(self):
        salt = os.urandom(16).hex()
        token = hashlib.md5(
            (self.password + salt).encode("utf-8")
        ).hexdigest()

        return {
            "u": self.username,
            "t": token,
            "s": salt,
            "v": API_VERSION,
            "c": CLIENT_NAME,
            "f": "json",
        }

    def call(self, endpoint, **params):
        url = f"{self.base_url}/rest/{endpoint}.view"

        query = self._auth()
        query.update(params)

        response = requests.get(
            url,
            params=query,
            timeout=TIMEOUT,
        )
        response.raise_for_status()

        data = response.json()

        root = data.get("subsonic-response", {})

        if root.get("status") != "ok":
            error = root.get("error", {})
            message = error.get("message", "Unknown Navidrome API error")
            code = error.get("code", "?")
            raise RuntimeError(
                f"Navidrome API error {code}: {message}"
            )

        return root

    def ping(self):
        self.call("ping")

    def random_songs(self, size):
        result = self.call(
            "getRandomSongs",
            size=size,
        )

        return result.get("randomSongs", {}).get("song", [])

    def starred(self):
        result = self.call("getStarred2")

        return result.get("starred2", {}).get("song", [])

    def playlists(self):
        result = self.call("getPlaylists")

        return result.get("playlists", {}).get("playlist", [])

    def create_playlist(self, name, song_ids):
        params = {
            "name": name,
        }

        # Requests supports repeated parameters when supplied as a list.
        params["songId"] = song_ids

        return self.call("createPlaylist", **params)

    
    def update_playlist(self, playlist_id, song_ids):
        params = {
            "playlistId": playlist_id,
            "songId": song_ids,
        }

        return self.call("updatePlaylist", **params)

    
    def delete_playlist(self, playlist_id):
        self.call(
            "deletePlaylist",
            id=playlist_id,
        )


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------

def load_history():
    if not HISTORY_FILE.exists():
        return {
            "tracks": {},
            "playlists": {},
        }

    try:
        with HISTORY_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        print("WARNING: Could not read history.json; starting fresh.")
        return {
            "tracks": {},
            "playlists": {},
        }


def save_history(history):
    temporary = HISTORY_FILE.with_suffix(".tmp")

    with temporary.open("w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

    temporary.replace(HISTORY_FILE)


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

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
        prefix = DAILY_PLAYLIST_PREFIX
    elif frequency == "weekly":
        prefix = WEEKLY_PLAYLIST_PREFIX
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


# ---------------------------------------------------------------------------
# Build a large candidate pool
# ---------------------------------------------------------------------------

def build_pool(navidrome):
    """
    Navidrome's random-song endpoint gives us a large, varied sample of the
    library without needing to walk every album individually.

    Multiple requests are used to reduce duplication.
    """

    songs = {}

    attempts = 0
    max_attempts = max(3, math.ceil(POOL_SIZE / 500))

    print(f"Building candidate pool (~{POOL_SIZE} songs)...")

    while len(songs) < POOL_SIZE and attempts < max_attempts:
        attempts += 1

        batch_size = min(
            500,
            POOL_SIZE - len(songs),
        )

        batch = navidrome.random_songs(batch_size)

        for raw_song in batch:
            song = normalize_song(raw_song)
            songs[song_key(song)] = song

        print(
            f"  pool: {len(songs)} songs "
            f"(request {attempts}/{max_attempts})"
        )

    return list(songs.values())


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def generated_recently(song_id, history):
    cutoff = datetime.now(timezone.utc) - timedelta(
        days=AVOID_GENERATED_DAYS
    )

    timestamp = history.get("tracks", {}).get(song_id)

    if not timestamp:
        return False

    try:
        played = datetime.fromisoformat(timestamp)
    except ValueError:
        return False

    return played >= cutoff


def score_song(song, mode, starred_ids, history):
    """
    Higher score = more desirable.

    The exact weights intentionally differ between the four modes.
    """

    play_count = int(song.get("playCount") or 0)

    is_starred = song["id"] in starred_ids

    # Random component prevents identical mixes.
    randomness = random.random() * 25

    # Never played is highly valuable for discovery/deep-library modes.
    never_played = 1 if play_count == 0 else 0

    # Low play counts are favored by discovery/deep library.
    low_play_score = 1 / (1 + play_count)

    # Frequently played songs become stronger candidates for personal radio.
    familiarity = math.log1p(play_count)

    if mode == "Discovery":
        score = (
            never_played * 100
            + low_play_score * 80
            + randomness
        )

    elif mode == "Personal Radio":
        score = (
            familiarity * 35
            + (150 if is_starred else 0)
            + low_play_score * 20
            + randomness
        )

    elif mode == "Deep Library":
        score = (
            never_played * 180
            + low_play_score * 120
            + (40 if play_count <= 2 else 0)
            + randomness
        )

    elif mode == "Balanced":
        score = (
            never_played * 80
            + low_play_score * 70
            + familiarity * 20
            + (80 if is_starred else 0)
            + randomness
        )

    else:
        raise ValueError(f"Unknown mode: {mode}")

    # Strongly discourage tracks that appeared in recent generated mixes.
    if generated_recently(song["id"], history):
        score *= 0.03

    return score


# ---------------------------------------------------------------------------
# Select tracks while enforcing diversity
# ---------------------------------------------------------------------------

def select_tracks(
    songs,
    mode,
    starred_ids,
    history,
):
    scored = [
        (
            score_song(song, mode, starred_ids, history),
            song,
        )
        for song in songs
    ]

    scored.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    selected = []

    artists = defaultdict(int)
    albums = defaultdict(int)

    # Consider more candidates than we need so diversity restrictions don't
    # leave us short.
    for score, song in scored:
        artist = artist_key(song)
        album = album_key(song)

        if artists[artist] >= MAX_PER_ARTIST:
            continue

        if albums[album] >= MAX_PER_ALBUM:
            continue

        selected.append(song)

        artists[artist] += 1
        albums[album] += 1

        if len(selected) >= PLAYLIST_SIZE:
            break

    # If the strict constraints left us short, fill the remainder with the
    # best remaining tracks while still avoiding duplicate IDs.
    if len(selected) < PLAYLIST_SIZE:
        selected_ids = {song["id"] for song in selected}

        for score, song in scored:
            if song["id"] in selected_ids:
                continue

            selected.append(song)
            selected_ids.add(song["id"])

            if len(selected) >= PLAYLIST_SIZE:
                break

    random.shuffle(selected)

    return selected[:PLAYLIST_SIZE]


# ---------------------------------------------------------------------------
# Playlist cleanup
# ---------------------------------------------------------------------------

def cleanup_old_playlists(navidrome):
    playlists = navidrome.playlists()

    cutoff = today() - timedelta(days=KEEP_PLAYLIST_DAYS)

    prefix = f"{PLAYLIST_PREFIX} —"

    for playlist in playlists:
        name = playlist.get("name", "")

        if not name.startswith(prefix):
            continue

        parts = name.split(" — ")

        if len(parts) < 3:
            continue

        date_string = parts[-1]

        try:
            playlist_date = datetime.strptime(
                date_string,
                "%Y-%m-%d",
            ).date()
        except ValueError:
            continue

        if playlist_date < cutoff:
            playlist_id = playlist.get("id")

            if playlist_id:
                print(f"Deleting old playlist: {name}")

                try:
                    navidrome.delete_playlist(playlist_id)
                except Exception as exc:
                    print(
                        f"WARNING: Could not delete {name}: {exc}"
                    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def find_playlist(navidrome, name):
    """
    Find an existing playlist by exact name.

    Returns the playlist object or None.
    """
    playlists = navidrome.playlists()

    for playlist in playlists:
        if playlist.get("name") == name:
            return playlist

    return None

def run(mode, frequency):
    print("=" * 70)
    print(f"Navidrome {frequency.title()} Mix Generator")
    print(f"Mode: {mode}")
    print(f"Date: {today()}")
    print("=" * 70)

    navidrome = Navidrome()

    print("Testing Navidrome connection...")
    navidrome.ping()
    print("Navidrome connection OK.")

    history = load_history()

    # Get favorites for Personal Radio / Balanced scoring.
    print("Loading favorites...")
    starred = navidrome.starred()

    starred_ids = {
        song["id"]
        for song in starred
        if song.get("id")
    }

    print(f"Loaded {len(starred_ids)} favorites.")

    songs = build_pool(navidrome)

    if len(songs) < PLAYLIST_SIZE:
        raise RuntimeError(
            f"Only found {len(songs)} candidate songs; "
            f"need at least {PLAYLIST_SIZE}."
        )

    print(f"Selecting {PLAYLIST_SIZE} tracks...")

    selected = select_tracks(
        songs=songs,
        mode=mode,
        starred_ids=starred_ids,
        history=history,
    )

    if len(selected) < PLAYLIST_SIZE:
        raise RuntimeError(
            f"Could only select {len(selected)} songs."
        )

    name = playlist_name(mode, frequency)
    playlist = find_playlist(navidrome, name)

    print()

    if playlist:
        print(f"Updating existing playlist: {name}")
        print(f"Playlist ID: {playlist.get('id')}")
    else:
        print(f"Creating playlist: {name}")

    print()

    for index, song in enumerate(selected, 1):
        print(
            f"{index:02d}. "
            f"{song.get('artist', 'Unknown Artist')} - "
            f"{song.get('title', 'Unknown Title')}"
        )

    song_ids = [song["id"] for song in selected]

    if playlist:
        navidrome.update_playlist(
            playlist_id=playlist["id"],
            song_ids=song_ids,
        )
    else:
        navidrome.create_playlist(
            name=name,
            song_ids=song_ids,
        )

    # Record generated tracks so future mixes can avoid them.
    timestamp = datetime.now(timezone.utc).isoformat()

    for song in selected:
        history.setdefault("tracks", {})[
            song["id"]
        ] = timestamp

    history.setdefault("playlists", {})[name] = {
        "updated": timestamp,
        "mode": mode,
        "tracks": [song["id"] for song in selected],
    }

    save_history(history)


    print()
    print("=" * 70)
    print(f"SUCCESS: {name}")
    print(f"Tracks: {len(selected)}")
    print("=" * 70)


def usage():
    print(
        """
Usage:

  daily_mix.py discovery
  daily_mix.py radio
  daily_mix.py deep
  daily_mix.py balanced

Modes:

  discovery   A - Discovery
  radio       B - Personal Radio
  deep        C - Deep Library
  balanced    D - Balanced
"""
    )


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(
            """
Usage:

  daily_mix.py daily discovery
  daily_mix.py daily radio
  daily_mix.py daily deep
  daily_mix.py daily balanced

  daily_mix.py weekly discovery
  daily_mix.py weekly radio
  daily_mix.py weekly deep
  daily_mix.py weekly balanced

Frequencies:
  daily    Update Daily Mix playlists
  weekly   Update Weekly Mix playlists

Modes:
  discovery   A - Discovery
  radio       B - Personal Radio
  deep        C - Deep Library
  balanced    D - Balanced
"""
        )
        sys.exit(1)

    frequency = sys.argv[1].lower()
    requested_mode = sys.argv[2].lower()

    frequencies = {
        "daily",
        "weekly",
    }

    modes = {
        "discovery": "Discovery",
        "radio": "Personal Radio",
        "deep": "Deep Library",
        "balanced": "Balanced",
    }

    if frequency not in frequencies:
        print(f"Unknown frequency: {frequency}")
        sys.exit(1)

    if requested_mode not in modes:
        print(f"Unknown mode: {requested_mode}")
        sys.exit(1)

    run(
        modes[requested_mode],
        frequency,
    )