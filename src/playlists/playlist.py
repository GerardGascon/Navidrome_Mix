from abc import ABC, abstractmethod

from utils import generated_recently


class Playlist(ABC):
    @abstractmethod
    def _score_song(self, play_count: int, is_starred: bool) -> float:
        pass

    def score(self, song, starred_ids, history) -> float:
        play_count = int(song.get("playCount") or 0)
        is_starred = song["id"] in starred_ids

        score = self._score_song(play_count, is_starred)

        # Strongly discourage tracks that appeared in recent generated mixes.
        if generated_recently(song["id"], history):
            score *= 0.03

        return score