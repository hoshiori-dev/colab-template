"""Runs in the Colab kernel. Reports whether the code executed before it raised.

`colab exec` and `colab install` exit 0 whatever the kernel did; the kernel itself keeps
the last uncaught exception in sys.last_value. colab.py reads the line printed here.
"""

import sys


def _status():
    error = getattr(sys, "last_value", None)
    if error is None:
        return 0
    if isinstance(error, SystemExit):
        return error.code if isinstance(error.code, int) else int(error.code is not None)
    return 1


print(f"[vm] status: {_status()}", flush=True)
del _status
