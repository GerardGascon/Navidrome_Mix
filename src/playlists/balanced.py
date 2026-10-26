import math
import random

from mix_types import Song
from .playlistgenerator import PlaylistGenerator


class BalancedPlaylistGenerator(PlaylistGenerator):
    def _score_song(self, song: Song) -> float:
        never_played = 1 if song.play_count == 0 else 0
        low_play_score = 1 / (1 + song.play_count)
        familiarity = math.log1p(song.play_count)

        # Random component prevents identical mixes.
        randomness = random.random() * 25

        return never_played * 80 + low_play_score * 70 + familiarity * 20 + (80 if song.is_starred else 0) + randomness
