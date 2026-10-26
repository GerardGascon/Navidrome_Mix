class Song:
    def __init__(self, song_id: str, title: str, length: int, artist: str, album: str, play_count: int):
        self.id = song_id
        self.title = title
        self.length = length
        self.artist = artist
        self.album = album
        self.play_count = play_count
        self.is_starred = False


class Playlist:
    def __init__(self, playlist_id: str):
        self.id = playlist_id
