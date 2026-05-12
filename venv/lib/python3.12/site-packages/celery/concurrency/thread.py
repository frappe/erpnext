"""Thread execution pool."""

from concurrent.futures import ThreadPoolExecutor, wait

from .base import BasePool, apply_target

__all__ = ('TaskPool',)


class ApplyResult:
    def __init__(self, future):
        self.f = future
        self.get = self.f.result

    def wait(self, timeout=None):
        wait([self.f], timeout)


class TaskPool(BasePool):
    """Thread Task Pool."""

    body_can_be_buffer = True
    signal_safe = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.executor = ThreadPoolExecutor(max_workers=self.limit)

    def on_stop(self):
        self.executor.shutdown()
        super().on_stop()

    def on_apply(self, target, args=None, kwargs=None, callback=None,
                 accept_callback=None, **_):
        f = self.executor.submit(apply_target, target, args, kwargs,
                                 callback, accept_callback)
        return ApplyResult(f)

    def _get_info(self):
        return {
            'max-concurrency': self.limit,
            'threads': len(self.executor._threads)
            # TODO use a public api to retrieve the current number of threads
            # in the executor when available. (Currently not available).
        }
