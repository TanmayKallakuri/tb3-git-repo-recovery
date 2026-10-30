"""Parse five-field cron expressions into sets of allowed values."""

import time

from orbit.errors import OrbitError

FIELDS = ("minute", "hour", "day", "month", "weekday")
RANGES = {
    "minute": (0, 59),
    "hour": (0, 23),
    "day": (1, 31),
    "month": (1, 12),
    "weekday": (0, 7),
}


class CronError(OrbitError, ValueError):
    """Raised for an expression that cannot be parsed."""


def _number(value, text):
    if not value.isdigit():
        raise CronError(f"bad value: {text}")
    return int(value)


def parse_field(text, low, high):
    """Expand one field ("*", "5", "1-5", "*/15", "1,3,5") into a set."""
    values = set()
    for part in text.split(","):
        if not part:
            raise CronError(f"empty field: {text}")
        step = 1
        if "/" in part:
            part, step = part.split("/", 1)
            step = _number(step, text)
        if part == "*":
            start, end = low, high
        elif "-" in part:
            start, end = (_number(x, text) for x in part.split("-", 1))
        else:
            start = end = _number(part, text)
        if start < low or end > high or start > end:
            raise CronError(f"value out of range: {text}")
        if step < 1:
            raise CronError(f"bad step: {text}")
        values.update(range(start, end + 1, step))
    if high == 7 and 7 in values:
        values.discard(7)
        values.add(0)
    return values


def parse(expression):
    """Parse "*/15 9-17 * * 1-5" into a dict of value sets keyed by field."""
    parts = expression.split()
    if len(parts) != len(FIELDS):
        raise CronError(f"expected {len(FIELDS)} fields, got {len(parts)}")
    return {
        name: parse_field(text, *RANGES[name])
        for name, text in zip(FIELDS, parts)
    }


def matches(spec, when):
    """True when the struct_time `when` is allowed by every field of `spec`."""
    weekday = (when.tm_wday + 1) % 7
    return (
        when.tm_min in spec["minute"]
        and when.tm_hour in spec["hour"]
        and when.tm_mday in spec["day"]
        and when.tm_mon in spec["month"]
        and weekday in spec["weekday"]
    )


def next_run(spec, after):
    """Return the first minute strictly after `after` (epoch seconds) that matches."""
    candidate = int(after // 60 + 1) * 60
    limit = candidate + 2 * 366 * 24 * 3600
    while candidate < limit:
        if matches(spec, time.gmtime(candidate)):
            return candidate
        candidate += 60
    raise CronError("no run time within a year")
