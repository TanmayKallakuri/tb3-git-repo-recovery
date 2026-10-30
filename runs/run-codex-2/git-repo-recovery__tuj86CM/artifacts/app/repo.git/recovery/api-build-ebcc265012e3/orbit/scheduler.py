"""The scheduler: holds the job table and decides what runs on each tick."""

from orbit.cache import WarmupCache
from orbit.cron import next_run, parse


class Scheduler:
    """Keeps the jobs and the next run time of each of them."""

    def __init__(self, clock, runner, store=None, jitter=0, notifier=None):
        self.notifier = notifier
        self.cache = WarmupCache()
        self.jitter = jitter
        self.clock = clock
        self.runner = runner
        self.store = store
        self.jobs = {}
        self.specs = {}
        self.next_run = store.load() if store else {}

    def add(self, job):
        """Register a job; its schedule is validated here."""
        self.specs[job.name] = parse(job.schedule)
        self.jobs[job.name] = job
        self.cache.warm([job])

    def remove(self, name):
        self.jobs.pop(name, None)
        self.next_run.pop(name, None)

    def due(self, now):
        """Return the jobs whose next run time has passed."""
        return [
            job
            for name, job in sorted(self.jobs.items())
            if job.enabled and self.next_run.get(name, 0) <= now
        ]

    def tick(self):
        now = self.clock.now()
        for job in self.due(now):
            result = self.runner.run(job)
            if self.notifier and result is not None:
                self.notifier.notify(result)
            self.next_run[job.name] = next_run(self.specs[job.name], now) + self.jitter
        if self.store:
            self.store.save(self.next_run)
