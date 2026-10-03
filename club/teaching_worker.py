"""Sequential durable queue runner; no automatic retry of charged work."""
import signal
import threading

import click

from .teaching import claim_job
from .teaching_drafts import process_claim


def run_worker(app, database, *, poll_seconds, max_jobs, stop, emit):
    processed = 0
    while not stop.is_set():
        # Close the connection after each job/poll, including on exceptions.
        with app.app_context():
            connection = database()
            claim = claim_job(connection)
            if claim:
                outcome = process_claim(app, connection, claim)
                processed += 1
                emit('Job processing: ' + outcome)
        if max_jobs and processed >= max_jobs:
            break
        if not claim:
            stop.wait(poll_seconds)
    return processed


def register_worker(app, database):
    @app.cli.command('process-teaching-worker')
    @click.option('--poll-seconds', type=click.IntRange(1, 60), default=5, show_default=True)
    @click.option('--max-jobs', type=click.IntRange(0, 1000), default=0,
                  help='Stop after this many claimed jobs; zero runs until signalled.')
    def worker(poll_seconds, max_jobs):
        """Drain queued uploads, waiting for new work until SIGTERM/SIGINT."""
        stop = threading.Event()
        previous = {}

        def shutdown(signum, frame):
            # Finish the in-flight job, but never claim another after shutdown.
            stop.set()

        try:
            for signum in (signal.SIGTERM, signal.SIGINT):
                previous[signum] = signal.signal(signum, shutdown)
            click.echo('Teaching worker started; sequential processing, explicit retries only.')
            processed = run_worker(app, database, poll_seconds=poll_seconds,
                                   max_jobs=max_jobs, stop=stop, emit=click.echo)
            click.echo(f'Teaching worker stopped; jobs processed: {processed}.')
        finally:
            for signum, handler in previous.items():
                signal.signal(signum, handler)
