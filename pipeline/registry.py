"""Compatibility shim for :mod:`terralens._registry`.

The variable registry is package data now, because the library needs it and the
wheel must not install a top-level ``pipeline`` package.
"""

from terralens._registry import VARIABLES, Variable

__all__ = ["VARIABLES", "Variable"]
