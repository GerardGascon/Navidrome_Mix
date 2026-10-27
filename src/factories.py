import os

from clients.client import Client
from clients.navidrome import Navidrome
from clients.opensubsonic import OpenSubsonic
from playlists.balanced import BalancedPlaylistGenerator
from playlists.deep import DeepPlaylistGenerator
from playlists.discovery import DiscoveryPlaylistGenerator
from playlists.playlistgenerator import PlaylistGenerator
from playlists.radio import RadioPlaylistGenerator


def get_client(client_type: str) -> Client:
    base_url = os.getenv("SERVER_URL")
    assert base_url, "SERVER_URL environment variable not set"
    username = os.getenv("USERNAME")
    assert username, "USERNAME environment variable not set"
    password = os.getenv("PASSWORD")
    assert password, "PASSWORD environment variable not set"

    match client_type:
        case "opensubsonic":
            return OpenSubsonic(base_url, username, password)
        case "navidrome":
            return Navidrome(base_url, username, password)
    raise ValueError(f"Unknown client type: {client_type}")


def get_playlist_generator(mode: str) -> PlaylistGenerator:
    match mode:
        case "discovery":
            return DiscoveryPlaylistGenerator()
        case "radio":
            return RadioPlaylistGenerator()
        case "deep":
            return DeepPlaylistGenerator()
        case "balanced":
            return BalancedPlaylistGenerator()
    raise ValueError(f"Unknown mode: {mode}")
