# Troubleshooting

## `t_critical` raises `FileNotFoundError`, the other three functions work

```
FileNotFoundError: .../site-packages/tinystat/data/t-table.json
```

The lookup table did not install beside the code. `mean`, `stdev` and
anything else that only does arithmetic is unaffected; `t_critical` and
`confidence_interval` are not, because the second one calls the first.

Check where the table actually landed:

```python
from importlib.resources import files
print(files("tinystat").joinpath("data/t-table.json").is_file())
```

`False` means the wheel routed `data/` through the PEP 427 `.data`
scheme, which installs to the environment root rather than into the
package. Look for the file at `<venv>/data/t-table.json`. It shipped, it
installed, and nothing can read it.

Rebuild with the table inside the import package:

```
tinystat/data/t-table.json          reachable
tinystat-1.0.0.data/data/...        not reachable
```

This repository builds both on purpose — `make demo` shows the two side
by side.

## `ValueError: need at least two observations`

`stdev` and `confidence_interval` use Bessel's correction, so a single
observation has no defined sample standard deviation. Pass two or more.

## `t_critical` returns a wider interval than your stats table

The table is tabulated for `alpha` of 0.05 and 0.01 only. Where `df` is
not tabulated the next lower row is used, which errs conservative on
purpose: a slightly wider interval rather than a falsely narrow one.

## The confidence interval looks too wide for a large sample

`t_critical` tops out at the largest tabulated `df`. For large samples
the t distribution converges on the normal, so the interval is correct
but marginally conservative.
