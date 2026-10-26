import math
from abc import ABC, abstractmethod

import globals
from utils import normalize_song, song_key


class Client(ABC):
    @abstractmethod
    def ping(self):
        pass

    @abstractmethod
    def random_songs(self, size):
        pass

    @abstractmethod
    def starred(self):
        pass

    @abstractmethod
    def playlists(self):
        pass

    @abstractmethod
    def create_or_update_playlist(self, name, song_ids, playlist_id=None):
        pass

    def find_playlist(self, name: str):
        playlists = self.playlists()

        for playlist in playlists:
            if playlist.get("name") == name:
                return playlist

        return None

    def build_pool(self):
        """
        Client's random-song endpoint gives us a large, varied sample of the
        library without needing to walk every album individually.

        Multiple requests are used to reduce duplication.
        """

        songs = {}

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

            for raw_song in batch:
                song = normalize_song(raw_song)
                songs[song_key(song)] = song

            print(
                f"  pool: {len(songs)} songs (request {attempts}/{max_attempts})"
            )

        return list(songs.values())
