#!/usr/bin/env python3

import json
import math
import os
import sys
from datetime import datetime, timezone

import globals
from clients.client import Client
from clients.navidrome import Navidrome
from playlists.balanced import BalancedPlaylistGenerator
from playlists.deep import DeepPlaylistGenerator
from playlists.discovery import DiscoveryPlaylistGenerator
from playlists.playlistgenerator import PlaylistGenerator
from playlists.radio import RadioPlaylistGenerator
from utils import normalize_song, song_key, today, playlist_name

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CLIENT_TYPE = os.getenv("CLIENT_TYPE", "navidrome")
NAVIDROME_URL = os.getenv("NAVIDROME_URL", "http://127.0.0.1:4533").rstrip("/")
NAVIDROME_USER = os.environ["NAVIDROME_USER"]
NAVIDROME_PASSWORD = os.environ["NAVIDROME_PASSWORD"]

def get_client() -> Client:
    match CLIENT_TYPE:
        case "navidrome":
            return Navidrome(NAVIDROME_URL, NAVIDROME_USER, NAVIDROME_PASSWORD)
    raise ValueError(f"Unknown client type: {CLIENT_TYPE}")


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------

def load_history():
    if not globals.HISTORY_FILE.exists():
        return {
            "tracks": {},
            "playlists": {},
        }

    try:
        with globals.HISTORY_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        print("WARNING: Could not read history.json; starting fresh.")
        return {
            "tracks": {},
            "playlists": {},
        }


def save_history(history):
    temporary = globals.HISTORY_FILE.with_suffix(".tmp")

    with temporary.open("w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

    temporary.replace(globals.HISTORY_FILE)

# ---------------------------------------------------------------------------
# Build a large candidate pool
# ---------------------------------------------------------------------------

def build_pool(client):
    """
    Client's random-song endpoint gives us a large, varied sample of the
    library without needing to walk every album individually.

    Multiple requests are used to reduce duplication.
    """

    songs = {}

    attempts = 0
    max_attempts = max(3, math.ceil(globals.POOL_SIZE / 500))

    print(f"Building candidate pool (~{globals.POOL_SIZE} songs)...")

    while len(songs) < globals.POOL_SIZE and attempts < max_attempts:
        attempts += 1

        batch_size = min(
            500,
            globals.POOL_SIZE - len(songs),
        )

        batch = client.random_songs(batch_size)

        for raw_song in batch:
            song = normalize_song(raw_song)
            songs[song_key(song)] = song

        print(
            f"  pool: {len(songs)} songs "
            f"(request {attempts}/{max_attempts})"
        )

    return list(songs.values())


def get_playlist_generator(mode: str) -> PlaylistGenerator:
    match mode:
        case "discovery":
            return DiscoveryPlaylistGenerator()
        case "radio":
            return RadioPlaylistGenerator()
        case "deep":
            return DeepPlaylistGenerator()
        case "balanced":
            return BalancedPlaylistGenerator()
    raise ValueError(f"Unknown mode: {mode}")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def find_playlist(client: Client, name: str):
    """
    Find an existing playlist by exact name.

    Returns the playlist object or None.
    """
    playlists = client.playlists()

    for playlist in playlists:
        if playlist.get("name") == name:
            return playlist

    return None

def run(mode, frequency):
    print("=" * 70)
    print(f"{frequency.title()} Mix Generator")
    print(f"Mode: {mode}")
    print(f"Date: {today()}")
    print("=" * 70)

    client = get_client()

    print("Testing client connection...")
    client.ping()
    print("Client connection OK.")

    history = load_history()

    # Get favorites for Personal Radio / Balanced scoring.
    print("Loading favorites...")
    starred = client.starred()

    starred_ids = {
        song["id"]
        for song in starred
        if song.get("id")
    }

    print(f"Loaded {len(starred_ids)} favorites.")

    songs = build_pool(client)

    if len(songs) < globals.PLAYLIST_SIZE:
        raise RuntimeError(
            f"Only found {len(songs)} candidate songs; "
            f"need at least {globals.PLAYLIST_SIZE}."
        )

    print(f"Selecting {globals.PLAYLIST_SIZE} tracks...")

    playlist_generator = get_playlist_generator(mode)
    selected = playlist_generator.generate(
        songs=songs,
        starred_ids=starred_ids,
        history=history,
    )

    if len(selected) < globals.PLAYLIST_SIZE:
        raise RuntimeError(
            f"Could only select {len(selected)} songs."
        )

    name = playlist_name(mode, frequency)
    playlist = find_playlist(client, name)

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
        client.create_or_update_playlist(
            name=name,
            song_ids=song_ids,
            playlist_id=playlist["id"],
        )
    else:
        client.create_or_update_playlist(
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


if __name__ == "__main__":
    if len(sys.argv) != 3:
        usage()
        sys.exit(1)

    frequency = sys.argv[1].lower()
    requested_mode = sys.argv[2].lower()

    frequencies = {
        "daily",
        "weekly",
    }

    modes = {
        "discovery",
        "radio",
        "deep",
        "balanced",
    }

    if frequency not in frequencies:
        print(f"Unknown frequency: {frequency}\n")
        usage()
        sys.exit(1)

    if requested_mode not in modes:
        print(f"Unknown mode: {requested_mode}\n")
        usage()
        sys.exit(1)

    run(
        modes,
        frequency,
    )