import random

from .playlist import Playlist


class DiscoveryPlaylist(Playlist):
    def _score_song(self, play_count: int, is_starred: bool) -> float:
        never_played = 1 if play_count == 0 else 0
        low_play_score = 1 / (1 + play_count)

        # Random component prevents identical mixes.
        randomness = random.random() * 25

        return never_played * 100 + low_play_score * 80 + randomness
