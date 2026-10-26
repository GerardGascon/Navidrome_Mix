#!/usr/bin/env python3

import json
import math
import os
import random
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from clients.client import Client
from clients.navidrome import Navidrome
from playlists.balanced import BalancedPlaylist
from playlists.deep import DeepPlaylist
from playlists.discovery import DiscoveryPlaylist
from playlists.playlist import Playlist
from playlists.radio import RadioPlaylist

import globals
from utils import generated_recently

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


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def get_playlist_generator(mode: str) -> Playlist:
    match mode:
        case "discovery":
            return DiscoveryPlaylist()
        case "radio":
            return RadioPlaylist()
        case "deep":
            return DeepPlaylist()
        case "balanced":
            return BalancedPlaylist()
    raise ValueError(f"Unknown mode: {mode}")


# ---------------------------------------------------------------------------
# Select tracks while enforcing diversity
# ---------------------------------------------------------------------------

def select_tracks(songs, mode, starred_ids, history):
    # First try to select ONLY songs that have not appeared
    # in a recently generated playlist.
    fresh_songs = [
        song
        for song in songs
        if not generated_recently(song["id"], history)
    ]

    playlist_generator = get_playlist_generator(mode)

    # If we don't have enough fresh songs, fall back to the
    # complete pool so the playlist can still reach PLAYLIST_SIZE.
    if len(fresh_songs) >= globals.PLAYLIST_SIZE:
        candidates = fresh_songs
        print(
            f"Using {len(fresh_songs)} fresh songs "
            f"(excluding recently generated tracks)."
        )
    else:
        candidates = songs
        print(
            f"WARNING: Only {len(fresh_songs)} fresh songs available. "
            f"Using full candidate pool."
        )

    scored = [
        (
            playlist_generator.score(song, starred_ids, history),
            song,
        )
        for song in candidates
    ]

    scored.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    selected = []

    artists = defaultdict(int)
    albums = defaultdict(int)

    # Enforce artist and album diversity.
    for score, song in scored:
        artist = artist_key(song)
        album = album_key(song)

        if artists[artist] >= globals.MAX_PER_ARTIST:
            continue

        if albums[album] >= globals.MAX_PER_ALBUM:
            continue

        selected.append(song)

        artists[artist] += 1
        albums[album] += 1

        if len(selected) >= globals.PLAYLIST_SIZE:
            break

    # If diversity restrictions prevented us from reaching 40,
    # fill from the remaining candidates.
    if len(selected) < globals.PLAYLIST_SIZE:
        selected_ids = {song["id"] for song in selected}

        for score, song in scored:
            if song["id"] in selected_ids:
                continue

            selected.append(song)
            selected_ids.add(song["id"])

            if len(selected) >= globals.PLAYLIST_SIZE:
                break

    random.shuffle(selected)

    return selected[:globals.PLAYLIST_SIZE]

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

    selected = select_tracks(
        songs=songs,
        mode=mode,
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
        "discovery",
        "radio",
        "deep",
        "balanced",
    }

    if frequency not in frequencies:
        print(f"Unknown frequency: {frequency}")
        sys.exit(1)

    if requested_mode not in modes:
        print(f"Unknown mode: {requested_mode}")
        sys.exit(1)

    run(
        modes,
        frequency,
    )