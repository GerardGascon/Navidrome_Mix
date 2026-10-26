import hashlib
import os

import requests

import globals
from mix_types import Song, Playlist
from .client import Client


class Navidrome(Client):
    def __init__(self, base_url, username, password):
        self.base_url = base_url
        self.username = username
        self.password = password

    def _auth(self):
        salt = os.urandom(16).hex()
        token = hashlib.md5(
            (self.password + salt).encode("utf-8")
        ).hexdigest()

        return {
            "u": self.username,
            "t": token,
            "s": salt,
            "v": globals.API_VERSION,
            "c": globals.CLIENT_NAME,
            "f": "json",
        }

    def _call(self, endpoint, **params):
        url = f"{self.base_url}/rest/{endpoint}.view"

        query = self._auth()
        query.update(params)

        response = requests.get(
            url,
            params=query,
            timeout=globals.TIMEOUT,
        )
        response.raise_for_status()

        data = response.json()

        root = data.get("subsonic-response", {})

        if root.get("status") != "ok":
            error = root.get("error", {})
            message = error.get("message", "Unknown Navidrome API error")
            code = error.get("code", "?")
            raise RuntimeError(
                f"Navidrome API error {code}: {message}"
            )

        return root

    @staticmethod
    def _parse_song(raw: dict) -> Song:
        return Song(
            song_id=raw.get("id", ""),
            title=raw.get("title", "Unknown Title"),
            artist=raw.get("artist", "Unknown Artist"),
            album=raw.get("album", "Unknown Album"),
            play_count=raw.get("playCount", 0),
        )

    def ping(self):
        self._call("ping")

    def random_songs(self, size) -> list[Song]:
        result = self._call(
            "getRandomSongs",
            size=size,
        )

        batch = result.get("randomSongs", {}).get("song", [])

        songs: list[Song] = []
        for raw_song in batch:
            songs.append(self._parse_song(raw_song))

        return songs

    def starred(self) -> list[Song]:
        result = self._call("getStarred2")

        batch = result.get("starred2", {}).get("song", [])

        songs: list[Song] = []
        for raw_song in batch:
            songs.append(self._parse_song(raw_song))

        return songs

    def _starred_ids(self) -> list[str]:
        result = self._call("getStarred2")

        batch = result.get("starred2", {}).get("song", [])

        songs: list[str] = []
        for raw_song in batch:
            songs.append(self._parse_song(raw_song).id)

        return songs

    def playlists(self):
        result = self._call("getPlaylists")

        return result.get("playlists", {}).get("playlist", [])

    def create_or_update_playlist(self, name: str, songs: list[Song], playlist: Playlist | None = None):
        params = {
            "name": name,
            "songId": [song.id for song in songs],
        }

        if playlist:
            params["playlistId"] = playlist.id

        return self._call("createPlaylist", **params)