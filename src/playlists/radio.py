import math
import random

from .playlistgenerator import PlaylistGenerator


class RadioPlaylistGenerator(PlaylistGenerator):
    def _score_song(self, play_count: int, is_starred: bool) -> float:
        low_play_score = 1 / (1 + play_count)

        # Frequently played songs become stronger candidates for personal radio.
        familiarity = math.log1p(play_count)

        # Random component prevents identical mixes.
        randomness = random.random() * 25

        return familiarity * 35 + (150 if is_starred else 0) + low_play_score * 20 + randomness
