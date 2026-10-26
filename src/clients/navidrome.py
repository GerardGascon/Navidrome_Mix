import hashlib
import os

import requests

from .client import Client
import globals

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

    def call(self, endpoint, **params):
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

    def ping(self):
        self.call("ping")

    def random_songs(self, size):
        result = self.call(
            "getRandomSongs",
            size=size,
        )

        return result.get("randomSongs", {}).get("song", [])

    def starred(self):
        result = self.call("getStarred2")

        return result.get("starred2", {}).get("song", [])

    def playlists(self):
        result = self.call("getPlaylists")

        return result.get("playlists", {}).get("playlist", [])

    def create_or_update_playlist(self, name, song_ids, playlist_id=None):
        params = {
            "name": name,
            "songId": song_ids,
        }

        if playlist_id:
            params["playlistId"] = playlist_id

        return self.call("createPlaylist", **params)