import random
from abc import ABC, abstractmethod
from collections import defaultdict

from utils import generated_recently, artist_key, album_key
import globals


class PlaylistGenerator(ABC):
    @abstractmethod
    def _score_song(self, play_count: int, is_starred: bool) -> float:
        pass

    def _score(self, song, starred_ids, history) -> float:
        play_count = int(song.get("playCount") or 0)
        is_starred = song["id"] in starred_ids

        score = self._score_song(play_count, is_starred)

        # Strongly discourage tracks that appeared in recent generated mixes.
        if generated_recently(song["id"], history):
            score *= 0.03

        return score

    def generate(self, songs, starred_ids, history):
        # First try to select ONLY songs that have not appeared
        # in a recently generated playlist.
        fresh_songs = [
            song
            for song in songs
            if not generated_recently(song["id"], history)
        ]

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
                self._score(song, starred_ids, history),
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
