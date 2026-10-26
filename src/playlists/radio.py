import math
import random

from mix_types import Song
from .playlistgenerator import PlaylistGenerator


class RadioPlaylistGenerator(PlaylistGenerator):
    def _score_song(self, song: Song) -> float:
        low_play_score = 1 / (1 + song.play_count)

        # Frequently played songs become stronger candidates for personal radio.
        familiarity = math.log1p(song.play_count)

        # Random component prevents identical mixes.
        randomness = random.random() * 25

        return familiarity * 35 + (150 if song.is_starred else 0) + low_play_score * 20 + randomness
