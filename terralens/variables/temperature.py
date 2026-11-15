"""2 m air temperature (MERRA-2 M2TMNXSLV)."""

from __future__ import annotations

from .base import Variable


class Temperature(Variable):
    """Warmth of the air at about head height, in degrees Celsius."""

    variable_id = "t2m"
    alias = "temperature"
