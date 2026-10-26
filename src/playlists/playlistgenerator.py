import random
from abc import ABC, abstractmethod
from collections import defaultdict
from datetime import datetime, timezone, timedelta

import globals
from history import History
from mix_types import Song
from utils import artist_key, album_key


class ScoredSong:
    def __init__(self, song: Song, score: float):
        self.song = song
        self.score = score


class PlaylistGenerator(ABC):
    @abstractmethod
    def _score_song(self, song: Song) -> float:
        pass

    def _score(self, song: Song, history) -> float:
        play_count = song.play_count

        score = self._score_song(song)

        # Strongly discourage tracks that appeared in recent generated mixes.
        if self._generated_recently(song.id, history):
            score *= 0.03

        return score

    @staticmethod
    def _generated_recently(song_id, history: History):
        cutoff = datetime.now(timezone.utc) - timedelta(days=globals.AVOID_GENERATED_DAYS)

        timestamp = history.tracks.get(song_id)

        if not timestamp:
            return False

        try:
            played = datetime.fromisoformat(timestamp)
        except ValueError:
            return False

        return played >= cutoff

    def generate(self, songs: list[Song], history: History) -> list[Song]:
        candidates = self._get_playlist_candidates(history, songs)

        scored: list[ScoredSong] = [
            (ScoredSong(song=song, score=self._score(song, history)))
            for song in candidates
        ]

        scored.sort(
            key=lambda item: item.score,
            reverse=True,
        )

        selected: list[Song] = self._select_diverse_songs(scored)

        # If diversity restrictions prevented us from reaching 40,
        # fill from the remaining candidates.
        if len(selected) < globals.PLAYLIST_SIZE:
            selected.extend(self._get_remaining_candidates(scored, selected))

        random.shuffle(selected)

        return selected[:globals.PLAYLIST_SIZE]

    @staticmethod
    def _get_remaining_candidates(scored: list[ScoredSong], selected: list[Song]) -> list[Song]:
        candidates: list[Song] = []

        selected_ids = {song.id for song in selected}

        for scoredSong in scored:
            if scoredSong.song.id in selected_ids:
                continue

            candidates.append(scoredSong.song)
            selected_ids.add(scoredSong.song.id)

            if len(selected) >= globals.PLAYLIST_SIZE:
                break

        return candidates

    @staticmethod
    def _select_diverse_songs(scored: list[ScoredSong]) -> list[Song]:
        selected: list[Song] = []

        artists = defaultdict(int)
        albums = defaultdict(int)

        # Enforce artist and album diversity.
        for scoredSong in scored:
            artist = artist_key(scoredSong.song)
            album = album_key(scoredSong.song)

            if artists[artist] >= globals.MAX_PER_ARTIST:
                continue

            if albums[album] >= globals.MAX_PER_ALBUM:
                continue

            selected.append(scoredSong.song)

            artists[artist] += 1
            albums[album] += 1

            if len(selected) >= globals.PLAYLIST_SIZE:
                break
        return selected

    @classmethod
    def _get_playlist_candidates(cls, history: History, songs: list[Song]) -> list[Song]:
        # First try to select ONLY songs that have not appeared
        # in a recently generated playlist.
        fresh_songs = [
            song
            for song in songs
            if not cls._generated_recently(song.id, history)
        ]

        # If we don't have enough fresh songs, fall back to the
        # complete pool so the playlist can still reach PLAYLIST_SIZE.
        if len(fresh_songs) >= globals.PLAYLIST_SIZE:
            print(f"Using {len(fresh_songs)} fresh songs (excluding recently generated tracks).")
            return fresh_songs

        print(f"WARNING: Only {len(fresh_songs)} fresh songs available. Using full candidate pool.")
        return songs
