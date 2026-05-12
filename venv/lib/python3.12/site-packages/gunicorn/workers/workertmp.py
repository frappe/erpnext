# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license.
# See the NOTICE for more information.

import os
import platform
import tempfile

from gunicorn import util

PLATFORM = platform.system()
IS_CYGWIN = PLATFORM.startswith('CYGWIN')


class WorkerTmp(object):

    def __init__(self, cfg):
        old_umask = os.umask(cfg.umask)
        fdir = cfg.worker_tmp_dir
        if fdir and not os.path.isdir(fdir):
            raise RuntimeError("%s doesn't exist. Can't create workertmp." % fdir)
        fd, name = tempfile.mkstemp(prefix="wgunicorn-", dir=fdir)
        os.umask(old_umask)

        # change the owner and group of the file if the worker will run as
        # a different user or group, so that the worker can modify the file
        if cfg.uid != os.geteuid() or cfg.gid != os.getegid():
            util.chown(name, cfg.uid, cfg.gid)

        # unlink the file so we don't leak tempory files
        try:
            if not IS_CYGWIN:
                util.unlink(name)
            # In Python 3.8, open() emits RuntimeWarning if buffering=1 for binary mode.
            # Because we never write to this file, pass 0 to switch buffering off.
            self._tmp = os.fdopen(fd, 'w+b', 0)
        except Exception:
            os.close(fd)
            raise

        self.spinner = 0

    def notify(self):
        self.spinner = (self.spinner + 1) % 2
        os.fchmod(self._tmp.fileno(), self.spinner)

    def last_update(self):
        return os.fstat(self._tmp.fileno()).st_ctime

    def fileno(self):
        return self._tmp.fileno()

    def close(self):
        return self._tmp.close()
