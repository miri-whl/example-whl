"""tinystat — small-sample statistics, in about a hundred lines.

The point of this package is not the statistics. It is that
:func:`t_critical` reads a lookup table from a file shipped alongside
the code, which is the commonest thing a small library does and the
thing a wheel most easily gets wrong.
"""

from .core import mean, stdev
from .tables import t_critical

__version__ = "1.0.0"
__all__ = ["mean", "stdev", "t_critical", "confidence_interval"]


def confidence_interval(sample, alpha=0.05):
    """The two-sided confidence interval for a sample's mean.

    Args:
        sample: The observations.
        alpha: Significance level; 0.05 gives a 95% interval.

    Returns:
        A (low, high) tuple.

    Raises:
        ValueError: The sample has fewer than two observations.
    """
    if len(sample) < 2:
        raise ValueError("need at least two observations")
    centre = mean(sample)
    margin = t_critical(len(sample) - 1, alpha) * stdev(sample) / len(sample) ** 0.5
    return (centre - margin, centre + margin)
