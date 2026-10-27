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

    def _authenticate(self) -> None:
        url = f"{self.base_url}/auth/login"

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

    def _call(self, endpoint: str, method: str = "GET", **kwargs) -> Any:
        if not self.token:
            self._authenticate()

        url = f"{self.base_url}/api/{endpoint.lstrip('/')}"

        json_body = kwargs.pop("json", None)
        query_params = kwargs.pop("params", None)

        if query_params is None:
            query_params = kwargs or None
        elif kwargs:
            query_params = {**query_params, **kwargs}

        response = self.session.request(
            method=method,
            url=url,
            params=query_params,
            json=json_body,
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

        if response.status_code == 204 or not response.content:
            return None

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

    def ping(self) -> None:
        response = self.session.get(
            f"{self.base_url}/ping",
            timeout=globals.TIMEOUT,
        )
        response.raise_for_status()

    def random_songs(self, size: int) -> list[Song]:
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

    def playlists(self) -> Any:
        return self._call("playlist/")

    def create_or_update_playlist(self, name: str, cover: str | None, songs: list[Song],
                                  playlist: Playlist | None = None) -> None:
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

    def _update_playlist(self, name: str, playlist: Playlist, song_ids: list[str]) -> None:
        self._call(
            f"playlist/{playlist.id}/",
            method="PUT",
            json={"name": name},
        )

        self._clear_playlist(playlist)

        if song_ids:
            self._call(
                f"playlist/{playlist.id}/tracks/",
                method="POST",
                json={"ids": song_ids},
            )

    def _clear_playlist(self, playlist: Playlist):
        tracks_url = f"playlist/{playlist.id}/tracks/"
        batch_size = 100

        while True:
            tracks = self._call(tracks_url)

            if not tracks:
                break

            batch = tracks[:batch_size]
            track_ids = [track["id"] for track in batch]

            self._call(
                tracks_url,
                method="DELETE",
                params=[("id", track_id) for track_id in track_ids],
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
