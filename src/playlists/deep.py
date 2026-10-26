import random

from .playlistgenerator import PlaylistGenerator


class DeepPlaylistGenerator(PlaylistGenerator):
    def _score_song(self, play_count: int, is_starred: bool) -> float:
        never_played = 1 if play_count == 0 else 0
        low_play_score = 1 / (1 + play_count)

        # Random component prevents identical mixes.
        randomness = random.random() * 25

        return never_played * 180 + low_play_score * 120 + (40 if play_count <= 2 else 0) + randomness
