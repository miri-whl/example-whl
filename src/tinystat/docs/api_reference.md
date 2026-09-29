# tinystat API

## `mean(sample)`
The arithmetic mean. Raises `ValueError` on an empty sample.

## `stdev(sample)`
Sample standard deviation with Bessel's correction (`n-1`). Needs two
observations.

## `t_critical(df, alpha=0.05)`
Two-tailed critical value of Student's t, read from `data/t-table.json`.
Tabulated for `alpha` of 0.05 and 0.01. Where `df` is not tabulated the
next lower row is used, which errs conservative (a wider interval).

## `confidence_interval(sample, alpha=0.05)`
Two-sided interval for the mean. Returns `(low, high)`.

```python
import tinystat
tinystat.confidence_interval([10.2, 10.4, 10.1, 10.3])
```

Note that `t_critical` is the only function that touches the filesystem.
If the package was built so that `data/t-table.json` installs outside the
import package, the first three functions work and this one raises
`FileNotFoundError` — with nothing wrong in the source.
