#!/usr/bin/env python3
import sys

import yaml

import mixer
from globals import CONFIG_FILE
from utils import today


def generate(name: str, generator: str):
    mixer.run(name, generator)


def try_generate(name: str, generator: str, frequency: str, forced: bool):
    if forced:
        generate(name, generator)
        return

    if frequency == "daily":
        generate(name, generator)

    if frequency == "weekly" and today().weekday() == 0:
        generate(name, generator)


def daily_run(forced: bool):
    with open(CONFIG_FILE) as file:
        data = yaml.load(file, Loader=yaml.SafeLoader)
        playlists = data["playlists"]
        for playlist in playlists:
            try_generate(playlist["name"], playlist["generator"], playlist["frequency"], forced)


if __name__ == "__main__":
    if len(sys.argv) > 0 and sys.argv[1].lower() == "--force":
        daily_run(True)
        sys.exit()

    daily_run(False)
