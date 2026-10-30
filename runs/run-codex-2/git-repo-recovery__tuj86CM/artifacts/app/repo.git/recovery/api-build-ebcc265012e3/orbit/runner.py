"""Run a job's command line and report the outcome."""

import logging
import subprocess

log = logging.getLogger("orbit.runner")


class Result:
    """Outcome of one run: the exit code and the captured output."""

    def __init__(self, job, code, output, errors=""):
        self.job = job
        self.code = code
        self.output = output
        self.errors = errors

    @property
    def ok(self):
        return self.code == 0


class Runner:
    """Runs commands synchronously, retrying failures when a policy is set."""

    def __init__(self, timeout=300, metrics=None, policy=None, clock=None):
        self.timeout = timeout
        self.metrics = metrics
        self.policy = policy
        self.clock = clock

    def run(self, job):
        """Run the job, retrying failures according to the policy."""
        attempt = 1
        while True:
            result = self.run_once(job)
            delay = self.policy.delay(attempt) if self.policy and not result.ok else None
            if delay is None:
                return result
            log.info("retry %s in %ss", job.name, delay)
            self.clock.sleep(delay)
            attempt += 1

    def run_once(self, job):
        """Run the command once and record the result in the metrics."""
        log.info("start %s", job.name)
        try:
            proc = subprocess.run(job.command, capture_output=True, text=True, timeout=job.timeout or self.timeout)
        except subprocess.TimeoutExpired:
            log.warning("timeout %s", job.name)
            result = Result(job, 124, "")
            if self.metrics:
                self.metrics.record(result)
            return result
        log.info("done %s exit=%d", job.name, proc.returncode)
        result = Result(job, proc.returncode, proc.stdout, proc.stderr)
        if self.metrics:
            self.metrics.record(result)
        return result
