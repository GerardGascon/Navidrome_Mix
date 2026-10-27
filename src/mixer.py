#!/usr/bin/env python3
import os
import sys
from datetime import datetime, timezone

import globals
from factories import get_client, get_playlist_generator
from history import History
from mix_types import Song
from utils import today


def run(name, mode):
    print("=" * 70)
    print(f"{name} Generator")
    print(f"Mode: {mode}")
    print(f"Date: {today()}")
    print("=" * 70)

    client_type = os.getenv("CLIENT_TYPE")
    assert client_type, "CLIENT_TYPE environment variable not set"
    client = get_client(client_type)

    print("Testing client connection...")
    client.ping()
    print("Client connection OK.")

    history = History.load()

    songs: list[Song] = client.build_pool()

    if len(songs) < globals.PLAYLIST_SIZE:
        raise RuntimeError(
            f"Only found {len(songs)} candidate songs; "
            f"need at least {globals.PLAYLIST_SIZE}."
        )

    print(f"Selecting {globals.PLAYLIST_SIZE} tracks...")

    playlist_generator = get_playlist_generator(mode)
    selected: list[Song] = playlist_generator.generate(songs=songs, history=history)

    if len(selected) < globals.PLAYLIST_SIZE:
        raise RuntimeError(f"Could only select {len(selected)} songs.")

    playlist = client.find_playlist(name)

    print()

    if playlist:
        print(f"Updating existing playlist: {name}")
        print(f"Playlist ID: {playlist.id}")
    else:
        print(f"Creating playlist: {name}")

    print()

    for index, song in enumerate(selected, 1):
        print(f"{index:02d}. {song.title} - {song.artist}")

    client.create_or_update_playlist(
        name=name,
        songs=selected,
        playlist=playlist,
    )

    # Record generated tracks so future mixes can avoid them.
    timestamp = datetime.now(timezone.utc).isoformat()

    for song in selected:
        history.tracks[song.id] = timestamp

    history.save()

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

    run(frequency, requested_mode)
