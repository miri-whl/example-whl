#!/usr/bin/env python3
"""Build two wheels from one source tree, differing only in layout.

Both wheels contain byte-identical Python source. Both install without a
warning. One of them works.

The difference is where the three non-code directories go:

    good:  tinystat/data/t-table.json        inside the import package
    bad:   tinystat-1.0.0.data/data/data/t-table.json   the PEP 427 data scheme

`.data/data/` is a real part of the wheel format and it has a real use —
files whose consumer is the ENVIRONMENT, like a man page or a shell
completion. Its failure mode is that it looks like the obvious home for
"data files", and a package's own data files are not that. They install
to the environment root, detached from the code that reads them, and
`importlib.resources` cannot see them.

Nothing here uses a build backend. A wheel is a ZIP with a RECORD, and
writing it by hand is the only way to be sure no tool quietly fixed the
mistake we are trying to demonstrate.

Usage:
    python build.py            # both wheels, into dist/good and dist/bad
    python build.py good       # just the one that works
    python build.py bad        # just the one that does not
"""

from __future__ import annotations

import base64
import hashlib
import shutil
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).parent
SRC = HERE / "src" / "tinystat"
DIST = HERE / "dist"



def _project() -> dict:
    """Name and version, read from pyproject.toml.

    Carried in one place rather than two. This does NOT make the file a
    build backend: nothing here consults `[build-system]`, because the
    whole point is to write both archives by hand.

    Returns:
        The `[project]` table.
    """
    try:
        import tomllib
    except ModuleNotFoundError:  # pragma: no cover - Python 3.9/3.10
        import tomli as tomllib  # type: ignore[no-redef]
    with (HERE / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)["project"]


NAME = _project()["name"]
VERSION = _project()["version"]
DIST_INFO = f"{NAME}-{VERSION}.dist-info"
DATA_DIR = f"{NAME}-{VERSION}.data"

#: The directories that are not Python source. Where these land is the
#: entire difference between the two wheels.
CARRIED = ("data", "docs", "examples")

METADATA = f"""Metadata-Version: 2.1
Name: {NAME}
Version: {VERSION}
Summary: {_project()["description"]}
Author: miri-whl
License-Expression: MIT
Requires-Python: >=3.9
Description-Content-Type: text/markdown

See https://github.com/miri-whl/example-whl
"""

WHEEL = """Wheel-Version: 1.0
Generator: example-whl build.py
Root-Is-Purelib: true
Tag: py3-none-any
"""


def _record_row(path: str, payload: bytes) -> str:
    """One RECORD line: path, hash, size.

    Args:
        path: The member's path inside the archive.
        payload: Its bytes.

    Returns:
        The RECORD row, with the urlsafe-base64 sha256 the spec asks for.
    """
    digest = hashlib.sha256(payload).digest()
    encoded = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return f"{path},sha256={encoded},{len(payload)}"


def _members(good: bool) -> dict[str, bytes]:
    """Every member of one wheel, keyed by archive path.

    Args:
        good: True to place carried files inside the import package,
            False to route them through the `.data` scheme.

    Returns:
        Archive path to file bytes.
    """
    members: dict[str, bytes] = {}
    for source in sorted(SRC.rglob("*")):
        if source.is_dir() or "__pycache__" in source.parts:
            continue
        relative = source.relative_to(SRC)
        top = relative.parts[0]
        if top in CARRIED and not good:
            # The PEP 427 data scheme. Installs to the environment root.
            archive_path = f"{DATA_DIR}/data/{relative.as_posix()}"
        else:
            archive_path = f"{NAME}/{relative.as_posix()}"
        members[archive_path] = source.read_bytes()
    members[f"{DIST_INFO}/METADATA"] = METADATA.encode()
    members[f"{DIST_INFO}/WHEEL"] = WHEEL.encode()
    members[f"{DIST_INFO}/top_level.txt"] = f"{NAME}\n".encode()
    return members


def build(good: bool) -> Path:
    """Write one wheel.

    Args:
        good: Which layout to use.

    Returns:
        The wheel's path.
    """
    label = "good" if good else "bad"
    out = DIST / label
    out.mkdir(parents=True, exist_ok=True)
    wheel_path = out / f"{NAME}-{VERSION}-py3-none-any.whl"

    members = _members(good)
    rows = [_record_row(path, payload) for path, payload in members.items()]
    rows.append(f"{DIST_INFO}/RECORD,,")
    with zipfile.ZipFile(wheel_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path, payload in members.items():
            archive.writestr(path, payload)
        archive.writestr(f"{DIST_INFO}/RECORD", "\n".join(rows) + "\n")
    return wheel_path


def main() -> None:
    """Build the wheels named on the command line, or both.

    Raises:
        SystemExit: An argument that is not `good` or `bad`.
    """
    wanted = sys.argv[1:] or ["good", "bad"]
    unknown = [arg for arg in wanted if arg not in ("good", "bad")]
    if unknown:
        raise SystemExit(f"unknown wheel {unknown[0]!r}: expected 'good' or 'bad'")

    # Only clear what is being rebuilt, so `build.py bad` does not
    # silently delete the good wheel someone is comparing against.
    for label in wanted:
        target = DIST / label
        if target.exists():
            shutil.rmtree(target)

    for label in wanted:
        path = build(label == "good")
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
        table = next(n for n in names if n.endswith("t-table.json"))
        print(f"{label:4} {path.relative_to(HERE)}")
        print(f"       {len(names)} members · table at {table}")


if __name__ == "__main__":
    main()
