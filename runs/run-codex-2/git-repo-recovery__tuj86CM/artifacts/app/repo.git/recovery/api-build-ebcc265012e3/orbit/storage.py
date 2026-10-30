"""Persist the scheduler state in a JSON file."""

import json
import os


class StateStore:
    """Reads and writes the next-run table atomically."""

    def __init__(self, path):
        self.path = path

    def load(self):
        """Return the saved state, or an empty dict when there is none."""
        if not os.path.exists(self.path):
            return {}
        with open(self.path, encoding="utf-8") as fh:
            return json.load(fh)

    def append_history(self, name, when, code):
        """Record one finished run in the history list."""
        state = self.load()
        state.setdefault("history", []).append([name, when, code])
        self.save(state)

    def save(self, state):
        """Write the state through a temporary file and rename it into place."""
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2, sort_keys=True)
        os.replace(tmp, self.path)
