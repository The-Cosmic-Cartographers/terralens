"""Compatibility shim for :mod:`terralens._stats`.

The statistics now live with the installable package so the wheel does not
need a top-level ``analysis`` package. Repo code and tests can keep importing
``analysis.stats`` unchanged.
"""

from terralens import _stats as _impl
from terralens._stats import *  # noqa: F403,F401


def __getattr__(name):
    return getattr(_impl, name)
