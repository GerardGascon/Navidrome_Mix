from clients.client import Client
from clients.navidrome import Navidrome
from playlists.balanced import BalancedPlaylistGenerator
from playlists.deep import DeepPlaylistGenerator
from playlists.discovery import DiscoveryPlaylistGenerator
from playlists.playlistgenerator import PlaylistGenerator
from playlists.radio import RadioPlaylistGenerator

def get_client(client_type: str) -> Client:
    match client_type:
        case "navidrome":
            return Navidrome()
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