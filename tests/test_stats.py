"""Unit tests for the statistics, run against the source tree.

Every test in this file passes whichever wheel you would have built from
this source, because none of them involves a wheel. They import
`tinystat` from `src/` where `data/t-table.json` is sitting right next to
`tables.py`, and in a source tree everything is adjacent and everything
works.

That is not a criticism of these tests. It is the point of the
repository: this is the test suite a careful author writes, it has real
coverage of the behaviour, and it is structurally incapable of noticing
that one of the two wheels is broken. What catches that is in
`test_installed.py`, and it is a different kind of test — it needs a
build and an install before it can ask its question.
"""

import math

import pytest

import tinystat


class TestMean:
    """The arithmetic mean."""

    def test_it_averages(self):
        """The obvious case."""
        assert tinystat.mean([1, 2, 3, 4]) == 2.5

    def test_a_single_observation_is_its_own_mean(self):
        """No division subtlety at n=1."""
        assert tinystat.mean([7.5]) == 7.5

    def test_an_empty_sample_is_refused(self):
        """Undefined, and said so rather than raising ZeroDivisionError."""
        with pytest.raises(ValueError, match="empty sample"):
            tinystat.mean([])


class TestStdev:
    """The sample standard deviation."""

    def test_it_uses_bessels_correction(self):
        """n-1, not n — the sample estimator, not the population one.

        For [2, 4, 4, 4, 5, 5, 7, 9] the population deviation is 2.0 and
        the sample deviation is larger. Getting this wrong is the
        classic statistics bug and it is off by only a few percent,
        which is why it wants a test with a known answer.
        """
        assert tinystat.stdev([2, 4, 4, 4, 5, 5, 7, 9]) == pytest.approx(2.13809, abs=1e-5)

    def test_identical_observations_have_no_spread(self):
        """A degenerate but legal sample."""
        assert tinystat.stdev([3.0, 3.0, 3.0]) == 0.0

    def test_one_observation_is_refused(self):
        """n-1 would be a division by zero; it is an error, not an inf."""
        with pytest.raises(ValueError, match="at least two"):
            tinystat.stdev([1.0])


class TestTCritical:
    """The lookup, which is the only thing here that reads a file."""

    def test_a_tabulated_value(self):
        """df=10 at alpha=0.05 is 2.228 in every published table."""
        assert tinystat.t_critical(10, 0.05) == 2.228

    def test_the_one_percent_level(self):
        """The second tabulated alpha."""
        assert tinystat.t_critical(10, 0.01) == 3.169

    def test_an_untabulated_df_rounds_conservative(self):
        """df=7 is absent, so it takes df=5 — the wider interval.

        Rounding the other way would report more confidence than the
        table supports, which is the direction that matters.
        """
        assert tinystat.t_critical(7, 0.05) == tinystat.t_critical(5, 0.05)

    def test_large_samples_approach_the_normal(self):
        """Beyond the table, t converges on z = 1.96."""
        assert tinystat.t_critical(10_000, 0.05) == 1.96

    def test_an_untabulated_alpha_is_refused(self):
        """Only 0.05 and 0.01 ship; anything else is a KeyError."""
        with pytest.raises(KeyError):
            tinystat.t_critical(10, 0.10)


class TestConfidenceInterval:
    """The function a caller actually reaches for."""

    def test_it_brackets_the_mean(self):
        """The interval is centred on the mean and has width."""
        sample = [10.2, 10.4, 10.1, 10.3]
        low, high = tinystat.confidence_interval(sample)
        centre = tinystat.mean(sample)
        assert low < centre < high
        assert (centre - low) == pytest.approx(high - centre)

    def test_a_stricter_alpha_widens_it(self):
        """99% has to cover more than 95%."""
        sample = [10.2, 10.4, 10.1, 10.3, 10.2, 10.5]
        narrow = tinystat.confidence_interval(sample, alpha=0.05)
        wide = tinystat.confidence_interval(sample, alpha=0.01)
        assert wide[0] < narrow[0] and wide[1] > narrow[1]

    def test_the_arithmetic_is_the_textbook_formula(self):
        """mean ± t* · s/√n, recomputed independently here."""
        sample = [10.2, 10.4, 10.1, 10.3]
        low, high = tinystat.confidence_interval(sample, alpha=0.05)
        expected = tinystat.t_critical(3, 0.05) * tinystat.stdev(sample) / math.sqrt(4)
        assert (high - low) / 2 == pytest.approx(expected)

    def test_one_observation_is_refused(self):
        """No spread, no interval."""
        with pytest.raises(ValueError, match="at least two"):
            tinystat.confidence_interval([1.0])
