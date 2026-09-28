# example-whl — two wheels, one source tree, one of them works

`tinystat` is a small statistics library: means, standard deviations, and
confidence intervals for small samples. It is about a hundred lines and
the statistics are not the point.

The point is `t_critical()`, which reads its answer out of a lookup table
shipped alongside the code. That is the commonest thing a small library
does, and it is the thing a wheel most easily gets wrong.

This repository builds **two wheels from the same source**. The Python
files inside them are byte-identical. Both install without a warning.
One of them raises `FileNotFoundError` the first time you ask it a real
question.

```bash
git clone https://github.com/miri-whl/example-whl
cd example-whl
make setup && make demo
```

Or take them one at a time:

| | |
|---|---|
| `make good` | build the working wheel, install it, watch it work |
| `make bad` | build the broken wheel, install it, watch it fail |
| `make demo` | both, side by side |
| `make build` | write both wheels into `dist/` and stop |
| `make test` | the unit tests — fast, and pass for either wheel |
| `make test-all` | adds the install round-trip, which tells them apart |
| `make probe` | all five `.data` scheme keys: where each lands, what is reachable |

`build.py` takes the same argument if you would rather not use make:
`python build.py bad` writes only that one, and leaves the other where it
is so you still have something to compare against.

## What you will see

```
───────────── good wheel ─────────────
pip install: OK (no warnings, no errors)
  import       OK, version 1.0.0
  mean         10.2500
  stdev        0.1291
  t_critical   2.228
  95% CI       10.0446 to 10.4554
  the table actually installed to:
               <venv>/lib/python3.13/site-packages/tinystat/data/t-table.json

───────────── bad wheel ─────────────
pip install: OK (no warnings, no errors)
  import       OK, version 1.0.0
  mean         10.2500
  stdev        0.1291
  t_critical   FileNotFoundError
               looked in <venv>/lib/python3.13/site-packages/tinystat/data/t-table.json
  the table actually installed to:
               <venv>/data/t-table.json
```

Read the last two lines of the bad run together. The file is **in the
virtualenv**. It shipped, it installed, `pip` was satisfied, and the
code that needs it looks three directories away.

Note also which functions survive. `mean` and `stdev` are fine, because
they touch nothing. A test suite that exercises them passes. The failure
is reserved for the one function that reads a file, and it arrives at
runtime, in your user's environment, not in your CI.

## The one line that differs

Both wheels are written by [`build.py`](build.py) — by hand, as ZIP
archives, with no build backend, so that nothing can quietly correct the
mistake being demonstrated. The only difference is where three
directories are placed:

| | good wheel | bad wheel |
|---|---|---|
| the lookup table | `tinystat/data/t-table.json` | `tinystat-1.0.0.data/data/data/t-table.json` |
| installs to | inside the import package | the environment root |
| `importlib.resources` | finds it | cannot see it |

`.data/` is a real part of the wheel format, specified by PEP 427, and it
has a legitimate use: files whose consumer is **the environment** — a man
page, a shell completion, a systemd unit. Its trap is that it reads like
the obvious home for "data files", and a package's own data files are not
that. They belong with the code that reads them.

## The test suite is the other half of the story

```
make test        15 tests, 0.01s   — and they pass for BOTH wheels
make test-all    27 tests, 4.6s    — these can tell them apart
```

`make test` runs the unit tests. They import `tinystat` from `src/`,
where the lookup table sits beside the module that reads it, and they
have real coverage: Bessel's correction against a known answer, the
conservative rounding direction, the refusal cases. They are the tests a
careful author writes, and **they are structurally incapable of noticing
that one of the two wheels is broken**, because nothing about a source
tree can answer "will this file be reachable after installation" — in a
source tree it already is.

`make test-all` adds `tests/test_installed.py`, which builds both wheels,
installs each into a throwaway virtualenv, and asks the installed package
in a separate process whether it can reach its own data file. That costs
a venv and a pip install per wheel, which is why this kind of test is
rare, and why this class of bug ships.

It also asserts the thing that makes the demonstration honest: the `.py`
members of both wheels are byte-identical. If that ever fails, a reader
could blame the code instead of its placement.

## Why it is not caught

Nothing is wrong with the source. Nothing is wrong with the wheel: it is
a valid archive with a correct `RECORD`, and `pip check` is happy. The
format has no opinion about whether the files you shipped can be reached
by the code you shipped them for, and neither does any tool in the
default path between your editor and your user.

The test that catches it is one line long, and it is the only one worth
adding:

```bash
# from a FRESH interpreter, not your source tree
python -c "from importlib.resources import files; print(files('tinystat').joinpath('data/t-table.json').read_text()[:40])"
```

Run against the installed package, not the checkout. In a checkout
everything is adjacent and everything works, which is exactly why this
class of bug reaches users.

## Layout

```
src/tinystat/
  __init__.py          public API: mean, stdev, t_critical, confidence_interval
  core.py              the functions that touch no files
  tables.py            t_critical — reads data/t-table.json via importlib.resources
  data/t-table.json    Student's t critical values
  docs/api.md          the API reference
  examples/quickstart.py
tests/
  test_stats.py        unit tests — pass for either wheel
  test_installed.py    builds, installs, and probes — tells them apart
build.py               writes both wheels from the tree above
probe_schemes.py       where all five .data scheme keys install, and
                       which of them the installed package can reach
demo.sh                installs both and shows the difference
Makefile               setup, build, test, test-all, demo, clean
pyproject.toml         metadata; build.py reads name and version from it
```

There is deliberately no `[build-system]` table. `pip install .` would
give you the good layout and hide the lesson, so both archives are
written by hand.

## Releases

Tagging `v*` builds both wheels, runs the full suite as a gate, and
attaches them to a GitHub release with a `SHA256SUMS`. Both carry the
same distribution name and version, so they are told apart by the
**build tag** — the optional fourth field of the wheel filename, which
exists for exactly this and must begin with a digit:

```
tinystat-1.0.0-1good-py3-none-any.whl
tinystat-1.0.0-2bad-py3-none-any.whl
```

Both are valid, installable wheels. You can point pip straight at the
broken one and watch it fail without cloning anything:

```bash
pip install https://github.com/miri-whl/example-whl/releases/latest/download/tinystat-1.0.0-2bad-py3-none-any.whl
python -c "import tinystat; tinystat.t_critical(10)"
```

**Not on PyPI, deliberately.** One of these is engineered to raise
`FileNotFoundError`. It does not belong on an index that people install
from by name.

## Licence

MIT. Copy it, break it, use it to demonstrate the same point to somebody
else.
