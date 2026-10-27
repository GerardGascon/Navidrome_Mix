import math
from abc import ABC, abstractmethod

import globals
from mix_types import Song, Playlist


class Client(ABC):
    @abstractmethod
    def ping(self):
        pass

    @abstractmethod
    def random_songs(self, size) -> list[Song]:
        pass

    @abstractmethod
    def starred(self) -> list[Song]:
        pass

    @abstractmethod
    def playlists(self):
        pass

    @abstractmethod
    def create_or_update_playlist(self, name: str, songs: list[Song], playlist: Playlist | None = None) -> None:
        pass

    def find_playlist(self, name: str) -> Playlist | None:
        playlists = self.playlists()

        for playlist in playlists:
            if playlist.get("name") == name:
                return Playlist(playlist.get("id"))

        return None

    def build_pool(self) -> list[Song]:
        """
        Client's random-song endpoint gives us a large, varied sample of the
        library without needing to walk every album individually.

        Multiple requests are used to reduce duplication.
        """

        songs: dict[str, Song] = {}

        attempts = 0
        max_attempts = max(3, math.ceil(globals.POOL_SIZE / 500))

        print(f"Building candidate pool (~{globals.POOL_SIZE} songs)...")

        while len(songs) < globals.POOL_SIZE and attempts < max_attempts:
            attempts += 1

            batch_size = min(
                500,
                globals.POOL_SIZE - len(songs),
            )

            batch = self.random_songs(batch_size)

            for song in batch:
                if song.length >= globals.SONG_MIN_LENGTH:
                    songs[song.id] = song

            print(f"  pool: {len(songs)} songs (request {attempts}/{max_attempts})")

        starred: list[Song] = self.starred()
        for song in starred:
            if song in songs:
                songs[song.id].is_starred = True

        return list[Song](songs.values())
