"""Exceptions raised by orbit."""


class OrbitError(Exception):
    """Base class for every error orbit raises on purpose."""


class ConfigError(OrbitError):
    """The job table could not be read."""
