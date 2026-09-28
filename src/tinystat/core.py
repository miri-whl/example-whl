"""The parts that need no data file."""


def mean(sample):
    """The arithmetic mean.

    Args:
        sample: The observations.

    Returns:
        Their mean.

    Raises:
        ValueError: The sample is empty.
    """
    if not sample:
        raise ValueError("mean of an empty sample is undefined")
    return sum(sample) / len(sample)


def stdev(sample):
    """The sample standard deviation, with Bessel's correction.

    Args:
        sample: The observations.

    Returns:
        Their standard deviation.

    Raises:
        ValueError: The sample has fewer than two observations.
    """
    if len(sample) < 2:
        raise ValueError("need at least two observations")
    centre = mean(sample)
    return (sum((x - centre) ** 2 for x in sample) / (len(sample) - 1)) ** 0.5
