"""Command-line interface."""

import argparse
import sys


def build_parser():
    """Build the argument parser for the orbit command."""
    parser = argparse.ArgumentParser(prog="orbit", description="Run periodic jobs.")
    parser.add_argument("--verbose", action="store_true", help="debug logging")
    parser.add_argument("--config", default="orbit.toml", help="job table (default: orbit.toml)")
    parser.add_argument("--state", default="orbit.state.json", help="state file")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("version", help="print the version")
    listing = sub.add_parser("list", help="list the jobs")
    listing.add_argument("--tag", help="only jobs with this tag")
    once = sub.add_parser("run", help="run one job now")
    once.add_argument("name")
    once.add_argument("--dry-run", action="store_true", help="print the command instead of running it")
    sub.add_parser("daemon", help="run the scheduler loop")
    sub.add_parser("history", help="show the recent runs")
    return parser


def load_jobs(args):
    """Load the job table named by the arguments."""
    from orbit.config import load

    return load(args.config)


def daemon(jobs):
    """Run the scheduler loop until interrupted."""
    from orbit.clock import Clock
    from orbit.runner import Runner
    from orbit.scheduler import Scheduler

    import os

    lock = "orbit.lock"
    if os.path.exists(lock):
        raise SystemExit(f"another daemon holds {lock}")
    open(lock, "w").close()
    clock = Clock()
    from orbit.notify import Notifier

    notifier = Notifier()
    sched = Scheduler(clock, Runner(), notifier=notifier)
    for job in jobs:
        sched.add(job)
    import signal

    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt))
    try:
        while True:
            sched.tick()
            clock.sleep(30)
    except KeyboardInterrupt:
        os.remove(lock)
        return 0


def main(argv=None):
    """Entry point: parse the arguments and dispatch."""
    args = build_parser().parse_args(argv)
    from orbit.log import setup

    setup(args.verbose)
    if args.command == "version":
        from orbit import __version__

        print(__version__)
        return 0
    if args.command == "list":
        jobs = [j for j in load_jobs(args) if not args.tag or args.tag in j.tags]
        if not jobs:
            print("no jobs configured")
        for job in sorted(jobs, key=lambda j: j.name):
            print(job.describe())
        return 0
    if args.command == "run":
        from orbit.runner import Runner

        for job in load_jobs(args):
            if job.name == args.name:
                if args.dry_run:
                    print(" ".join(job.command))
                    return 0
                return 0 if Runner().run(job).ok else 2
        print(f"no such job: {args.name}", file=sys.stderr)
        return 1
    if args.command == "daemon":
        return daemon(load_jobs(args))
    if args.command == "history":
        from orbit.table import table
        from orbit.storage import StateStore

        rows = StateStore(args.state).load().get("history", [])
        print(table(rows, ["job", "when", "exit"]))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
