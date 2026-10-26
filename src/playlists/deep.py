import random

from mix_types import Song
from .playlistgenerator import PlaylistGenerator


class DeepPlaylistGenerator(PlaylistGenerator):
    def _score_song(self, song: Song) -> float:
        never_played = 1 if song.play_count == 0 else 0
        low_play_score = 1 / (1 + song.play_count)

        # Random component prevents identical mixes.
        randomness = random.random() * 25

        return never_played * 180 + low_play_score * 120 + (40 if song.play_count <= 2 else 0) + randomness
