# Security Policy

`tinystat` is a teaching artifact. It exists so that a wheel built two
ways can be measured side by side, and it is published for people to
read and run, not to depend on.

**Do not install it into anything that matters.** `dist/bad/` contains a
wheel that is broken on purpose: `t_critical()` and
`confidence_interval()` raise `FileNotFoundError` after a clean install,
because the lookup table they read is routed through the PEP 427 `.data`
scheme and lands outside the import package. That is the defect this
repository exists to demonstrate. It is not a vulnerability and it will
not be fixed.

## Supported versions

| Version | Supported |
|---|---|
| 1.0.0 | Yes — the current teaching artifact |

There is one version and there is unlikely to be another. If the
demonstration changes, the version will move with it.

## Reporting a vulnerability

Open an issue at
[github.com/miri-whl/example-whl/issues](https://github.com/miri-whl/example-whl/issues).

Public disclosure is appropriate here: nothing in this repository holds
secrets, authenticates anyone, or runs anywhere but a throwaway
virtualenv on the reader's own machine. If you find something that is
genuinely dangerous rather than deliberately broken, say so in the issue
and it will be dealt with in the open.

Please do report:

- anything in `build.py`, `demo.sh` or `probe_schemes.py` that could
  damage a reader's machine or environment, rather than the temporary
  directory each one creates and removes;
- a dependency of the development environment carrying a known
  advisory;
- anything in the published wheels beyond the two Python packages and
  the files this README describes.

Please do not report that the bad wheel fails. It is meant to.
