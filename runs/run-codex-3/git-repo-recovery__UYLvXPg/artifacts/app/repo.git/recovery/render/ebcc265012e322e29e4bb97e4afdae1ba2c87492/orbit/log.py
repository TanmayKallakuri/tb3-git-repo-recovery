"""Logging setup shared by the CLI and the daemon."""

import logging


def setup(verbose=False):
    """Configure the root logger once; verbose turns on debug output."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s")
    return logging.getLogger("orbit")
