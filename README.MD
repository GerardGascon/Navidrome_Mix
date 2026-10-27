# Navidrome Mix Generator

Automatically generates Daily and Weekly playlists in Navidrome using several mix-generation modes.

## Overview

This application generates four types of mixes:

- **Discovery**: prioritizes tracks that have never or rarely been played.
- **Personal Radio**: favors familiar and starred tracks.
- **Deep Library**: strongly favors rarely/never-played tracks.
- **Balanced**: combines discovery, familiarity, favorites, and randomness.

Each mix contains the number of tracks configured by `PLAYLIST_SIZE`.

The playlists are persistent. Running the generator again updates the existing playlist rather than creating a new dated
playlist.

## Deployment

To deploy the app, docker compose is recommended. Use this script as a reference for you setup:

```yaml
services:
  navidrome_mix:
    image: ghcr.io/gerardgascon/daily-mixer:latest
    env_file:
      - .env
    environment:
      - NAVIDROME_URL=${NAVIDROME_URL}
      - NAVIDROME_USER=${NAVIDROME_USER}
      - NAVIDROME_PASSWORD=${NAVIDROME_PASSWORD}
      - PLAYLIST_SIZE=50
      - MAX_PER_ARTIST=2
      - MAX_PER_ALBUM=1
      - SONG_MIN_LENGTH=60
      - AVOID_GENERATED_DAYS=30
      - POOL_SIZE=3000
    volumes:
      - ./data:/data
    restart: unless-stopped
```

You will also need to set up the data directory for the automatic playlist generation. Create a file located under
`data/config.yaml`:

```yaml
playlists:
  - name: "Daily Mix 1"
    generator: "discovery"
    frequency: "daily"
  - name: "Daily Mix 2"
    generator: "radio"
    frequency: "daily"
  - name: "Daily Mix 3"
    generator: "deep"
    frequency: "daily"
  - name: "Daily Mix 4"
    generator: "balanced"
    frequency: "daily"
  - name: "Discovery Weekly"
    generator: "discovery"
    frequency: "weekly"
```

These are the values possible:

**generator**

- **discovery**: prioritizes tracks that have never or rarely been played.
- **radio**: favors familiar and starred tracks.
- **deep**: strongly favors rarely/never-played tracks.
- **balanced**: combines discovery, familiarity, favorites, and randomness.

**frequency**

- **daily**: gets generated each day.
- **weekly**: gets generated the first day of each week.

## Environment variables

| variable             | default     | description                                                                                  |
|----------------------|-------------|----------------------------------------------------------------------------------------------|
| CLIENT_TYPE          | `navidrome` | Select the server type where the playlists will be created. Possible values are: `navidrome` |
| NAVIDROME_URL        |             | Accessible url from your instance.                                                           |
| NAVIDROME_USER       |             | Your username.                                                                               |
| NAVIDROME_PASSWORD   |             | Your password.                                                                               |
| PLAYLIST_SIZE        | 50          | An integer representing the size of the playlists created.                                   |
| MAX_PER_ARTIST       | 2           | Max songs an artist has in a playlist.                                                       |
| MAX_PER_ALBUM        | 1           | Max songs from the same album in a playlist.                                                 |
| SONG_MIN_LENGTH      | 60          | Minimum length for a song to be included in the processing.                                  |
| AVOID_GENERATED_DAYS | 30          | Amount of days before a song is repeated in a playlist.                                      |
| POOL_SIZE            | 3000        | Size of the pool of random songs.                                                            |
| EXECUTE_ON_START     | false       | Execute playlist generation on startup.                                                      |
