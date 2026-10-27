import json

import globals


class History:
    def __init__(self, tracks: dict[str, str]):
        self.tracks = tracks

    @staticmethod
    def load():
        if not globals.HISTORY_FILE.exists():
            return History({})

        try:
            with globals.HISTORY_FILE.open("r", encoding="utf-8") as f:
                history = json.load(f)
                return History(history.get("tracks", {}))
        except Exception:
            print("WARNING: Could not read history.json; starting fresh.")
            return History({})

    def save(self):
        temporary = globals.HISTORY_FILE.with_suffix(".tmp")

        with temporary.open("w", encoding="utf-8") as f:
            json.dump({"tracks": self.tracks}, f, indent=2)

        temporary.replace(globals.HISTORY_FILE)
