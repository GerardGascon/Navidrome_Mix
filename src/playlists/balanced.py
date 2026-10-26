import math
import random

from .playlistgenerator import PlaylistGenerator


class BalancedPlaylistGenerator(PlaylistGenerator):
    def _score_song(self, play_count: int, is_starred: bool) -> float:
        never_played = 1 if play_count == 0 else 0
        low_play_score = 1 / (1 + play_count)
        familiarity = math.log1p(play_count)

        # Random component prevents identical mixes.
        randomness = random.random() * 25

        return never_played * 80 + low_play_score * 70 + familiarity * 20 + (80 if is_starred else 0) + randomness
