"""Plots for notebooks. Matplotlib is imported lazily so import stays instant."""

from __future__ import annotations

from typing import Any


def _pyplot():
    import matplotlib.pyplot as plt

    return plt


def plot_trend(result, ax=None):
    """Draw the annual series and the Sen line implied by ``result``."""
    plt = _pyplot()
    if ax is None:
        _, ax = plt.subplots(figsize=(7, 3.5))
    if result.annual:
        years = [year for year, value in result.annual if value is not None]
        values = [value for _, value in result.annual if value is not None]
        if years:
            ax.plot(years, values, color="#d95c43", linewidth=1.4, label=result.label)
            ax.scatter(years, values, s=9, color="#d95c43")
            if result.per_decade is not None and len(years) > 1:
                mean_year = sum(years) / len(years)
                mean_value = sum(values) / len(values)
                slope = result.per_decade / 10.0
                line = [mean_value + slope * (year - mean_year) for year in years]
                ax.plot(years, line, color="#3b3b3b", linestyle="--", linewidth=1.2)
    ax.set_title(f"{result.label} - {result.region_id}")
    ax.set_ylabel(result.unit)
    ax.grid(alpha=0.3)
    return ax


def plot_variable(variable, ax=None):
    """Monthly values as a thin line with the annual means on top."""
    plt = _pyplot()
    if ax is None:
        _, ax = plt.subplots(figsize=(7, 3.5))
    frame = variable.load()
    ax.plot(frame["date"], frame["value"], color="#b9b7ad", linewidth=0.8)
    annual = variable.annual()
    if annual:
        years = [year for year, value in annual if value is not None]
        values = [value for _, value in annual if value is not None]
        ax.plot(years, values, color="#d95c43", linewidth=1.6)
    ax.set_title(f"{variable.label} - {variable.region.name}")
    ax.set_ylabel(variable.units)
    ax.grid(alpha=0.3)
    return ax


def figure_for(plotter, *args, **kwargs) -> Any:
    """Return the figure that owns a freshly built axes."""
    ax = plotter(*args, **kwargs)
    return ax.figure
