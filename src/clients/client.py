from abc import ABC, abstractmethod

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
