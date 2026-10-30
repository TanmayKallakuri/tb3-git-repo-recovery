"""The job model."""

from dataclasses import dataclass, field


@dataclass
class Job:
    """A periodic job: a name, a cron expression and a command line."""

    name: str
    schedule: str
    command: list[str]
    enabled: bool = True
    tags: list[str] = field(default_factory=list)
    timeout: int = 300
    attempts: int = 1

    def __post_init__(self):
        if not self.name or "/" in self.name:
            raise ValueError(f"bad job name: {self.name!r}")

    def describe(self):
        """Return the one-line form used by the CLI listing."""
        state = "on" if self.enabled else "off"
        return f"{self.name:<20} {self.schedule:<16} {state}"
