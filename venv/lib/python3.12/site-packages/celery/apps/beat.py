"""Beat command-line program.

This module is the 'program-version' of :mod:`celery.beat`.

It does everything necessary to run that module
as an actual application, like installing signal handlers
and so on.
"""
import numbers
import socket
import sys
from datetime import datetime

from celery import VERSION_BANNER, beat, platforms
from celery.utils.imports import qualname
from celery.utils.log import LOG_LEVELS, get_logger
from celery.utils.time import humanize_seconds

__all__ = ('Beat',)

STARTUP_INFO_FMT = """
LocalTime -> {timestamp}
Configuration ->
    . broker -> {conninfo}
    . loader -> {loader}
    . scheduler -> {scheduler}
{scheduler_info}
    . logfile -> {logfile}@%{loglevel}
    . maxinterval -> {hmax_interval} ({max_interval}s)
""".strip()

logger = get_logger('celery.beat')


class Beat:
    """Beat as a service."""

    Service = beat.Service
    app = None

    def __init__(self, max_interval=None, app=None,
                 socket_timeout=30, pidfile=None, no_color=None,
                 loglevel='WARN', logfile=None, schedule=None,
                 scheduler=None,
                 scheduler_cls=None,  # XXX use scheduler
                 redirect_stdouts=None,
                 redirect_stdouts_level=None, **kwargs):
        self.app = app = app or self.app
        either = self.app.either
        self.loglevel = loglevel
        self.logfile = logfile
        self.schedule = either('beat_schedule_filename', schedule)
        self.scheduler_cls = either(
            'beat_scheduler', scheduler, scheduler_cls)
        self.redirect_stdouts = either(
            'worker_redirect_stdouts', redirect_stdouts)
        self.redirect_stdouts_level = either(
            'worker_redirect_stdouts_level', redirect_stdouts_level)

        self.max_interval = max_interval
        self.socket_timeout = socket_timeout
        self.no_color = no_color
        self.colored = app.log.colored(
            self.logfile,
            enabled=not no_color if no_color is not None else no_color,
        )
        self.pidfile = pidfile

        if not isinstance(self.loglevel, numbers.Integral):
            self.loglevel = LOG_LEVELS[self.loglevel.upper()]

    def run(self):
        print(str(self.colored.cyan(
            f'celery beat v{VERSION_BANNER} is starting.')))
        self.init_loader()
        self.set_process_title()
        self.start_scheduler()

    def setup_logging(self, colorize=None):
        if colorize is None and self.no_color is not None:
            colorize = not self.no_color
        self.app.log.setup(self.loglevel, self.logfile,
                           self.redirect_stdouts, self.redirect_stdouts_level,
                           colorize=colorize)

    def start_scheduler(self):
        if self.pidfile:
            platforms.create_pidlock(self.pidfile)
        service = self.Service(
            app=self.app,
            max_interval=self.max_interval,
            scheduler_cls=self.scheduler_cls,
            schedule_filename=self.schedule,
        )

        print(self.banner(service))

        self.setup_logging()
        if self.socket_timeout:
            logger.debug('Setting default socket timeout to %r',
                         self.socket_timeout)
            socket.setdefaulttimeout(self.socket_timeout)
        try:
            self.install_sync_handler(service)
            service.start()
        except Exception as exc:
            logger.critical('beat raised exception %s: %r',
                            exc.__class__, exc,
                            exc_info=True)
            raise

    def banner(self, service):
        c = self.colored
        return str(
            c.blue('__    ', c.magenta('-'),
                   c.blue('    ... __   '), c.magenta('-'),
                   c.blue('        _\n'),
                   c.reset(self.startup_info(service))),
        )

    def init_loader(self):
        # Run the worker init handler.
        # (Usually imports task modules and such.)
        self.app.loader.init_worker()
        self.app.finalize()

    def startup_info(self, service):
        scheduler = service.get_scheduler(lazy=True)
        return STARTUP_INFO_FMT.format(
            conninfo=self.app.connection().as_uri(),
            timestamp=datetime.now().replace(microsecond=0),
            logfile=self.logfile or '[stderr]',
            loglevel=LOG_LEVELS[self.loglevel],
            loader=qualname(self.app.loader),
            scheduler=qualname(scheduler),
            scheduler_info=scheduler.info,
            hmax_interval=humanize_seconds(scheduler.max_interval),
            max_interval=scheduler.max_interval,
        )

    def set_process_title(self):
        arg_start = 'manage' in sys.argv[0] and 2 or 1
        platforms.set_process_title(
            'celery beat', info=' '.join(sys.argv[arg_start:]),
        )

    def install_sync_handler(self, service):
        """Install a `SIGTERM` + `SIGINT` handler saving the schedule."""
        def _sync(signum, frame):
            service.sync()
            raise SystemExit()
        platforms.signals.update(SIGTERM=_sync, SIGINT=_sync)
