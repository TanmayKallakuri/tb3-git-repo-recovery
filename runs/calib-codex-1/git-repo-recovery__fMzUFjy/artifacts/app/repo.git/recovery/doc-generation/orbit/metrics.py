"""Run counters."""

from collections import Counter


class Metrics:
    """Counts runs and failures per job."""

    def __init__(self):
        self.runs = Counter()
        self.failures = Counter()

    def summary(self):
        """Return (job, runs, failures) rows sorted by job name."""
        return [(name, self.runs[name], self.failures[name]) for name in sorted(self.runs)]

    def record(self, result):
        self.runs[result.job.name] += 1
        if not result.ok:
            self.failures[result.job.name] += 1
