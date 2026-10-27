import mimetypes
from pathlib import Path
from typing import Any

import requests

import globals
from mix_types import Song, Playlist
from .client import Client


class Navidrome(Client):
    def __init__(self, base_url: str, username: str, password: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password

        self.session = requests.Session()
        self.token = None

    def _authenticate(self):
        url = f"{self.base_url}/auth/login"

        print(self.username)
        print(self.password)

        response = self.session.post(
            url,
            json={
                "username": self.username,
                "password": self.password,
            },
            timeout=globals.TIMEOUT,
        )
        response.raise_for_status()

        data = response.json()
        self.token = data.get("token")

        if not self.token:
            raise RuntimeError(f"Navidrome authentication failed: {data}")

    def _call(self, endpoint, method="GET", **params):
        if not self.token:
            self._authenticate()

        url = f"{self.base_url}/api/{endpoint.lstrip('/')}"

        response = self.session.request(
            method=method,
            url=url,
            params=params if method == "GET" else None,
            json=params.get("json") if method != "GET" else None,
            headers={
                "x-nd-authorization": f"Bearer {self.token}",
            },
            timeout=globals.TIMEOUT,
        )
        response.raise_for_status()

        refreshed_token = response.headers.get("x-nd-authorization")

        if refreshed_token:
            scheme, _, token = refreshed_token.partition(" ")
            if scheme.lower() == "bearer" and token:
                self.token = token

        return response.json()

    @staticmethod
    def _parse_song(raw: dict) -> Song:
        return Song(
            song_id=raw.get("id", ""),
            title=raw.get("title", "Unknown Title"),
            length=raw.get("duration", 0),
            artist=raw.get("artist", "Unknown Artist"),
            # Should we use album artist instead of artist?
            # artist=raw.get("albumArtist", "Unknown Artist"),
            album=raw.get("album", "Unknown Album"),
            play_count=raw.get("playCount", 0),
        )

    def ping(self):
        response = self.session.get(f"{self.base_url}/ping")
        response.raise_for_status()

    def random_songs(self, size) -> list[Song]:
        result = self._call(
            "song/",
            _sort="random",
            _start=0,
            _end=size,
        )

        return [self._parse_song(song) for song in result]

    def starred(self) -> list[Song]:
        result = self._call(
            "song/",
            starred=True,
        )

        return [self._parse_song(song) for song in result]

    def playlists(self):
        result = self._call("playlist/")
        return result

    def create_or_update_playlist(self, name: str, cover: str | None, songs: list[Song], playlist: Playlist | None = None) -> None:
        song_ids = [song.id for song in songs]

        if playlist:
            playlist_id = playlist.id
            self._update_playlist(name, playlist, song_ids)
        else:
            playlist_id = self._create_playlist(name, song_ids)

        if cover is not None:
            cover_path = globals.DATA_PATH / cover
            self._upload_playlist_cover(playlist_id, cover_path)

    def _create_playlist(self, name: str, song_ids: list[str]) -> str:
        result = self._call(
            "playlist/",
            method="POST",
            json={"name": name},
        )

        playlist_id = result.get("id")
        if not playlist_id:
            raise RuntimeError(
                f"Playlist creation returned no ID: {result}"
            )

        if song_ids:
            self._call(
                f"playlist/{playlist_id}/tracks/",
                method="POST",
                json={"ids": song_ids},
            )
            
        return playlist_id


    def _update_playlist(self, name: str, playlist: Playlist, song_ids: list[str]) -> Any:
        self._call(
            f"playlist/{playlist.id}/",
            method="PUT",
            json={"name": name},
        )

        self._call(
            f"playlist/{playlist.id}/tracks/",
            method="POST",
            json={"ids": song_ids},
        )

    def _upload_playlist_cover(self, playlist_id: str, cover_path: str | Path) -> None:
        path = Path(cover_path)
        content_type, _ = mimetypes.guess_type(path.name)

        if not content_type or not content_type.startswith("image/"):
            raise ValueError(f"Unsupported cover image: {path}")

        url = f"{self.base_url}/api/playlist/{playlist_id}/image"

        with path.open("rb") as image:
            response = self.session.post(
                url,
                files={"image": (path.name, image, content_type)},
                headers={"x-nd-authorization": f"Bearer {self.token}"},
                timeout=globals.TIMEOUT,
            )

        response.raise_for_status()

        refreshed_token = response.headers.get("x-nd-authorization")
        if refreshed_token:
            scheme, _, token = refreshed_token.partition(" ")
            if scheme.lower() == "bearer" and token:
                self.token = token
