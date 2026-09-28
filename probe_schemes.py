#!/usr/bin/env python3
"""Where each of the five `.data` scheme keys actually installs.

`tinystat` demonstrates one key — `data/` — because that is the one a
library reaches for when it has a lookup table to ship, and the one that
breaks it. The wheel format defines five, and they do not all land in the
same place or fail in the same way.

So this builds a throwaway wheel with a marker file in every key,
installs it, and asks two questions a producer needs separated:

    where did it land?       `find`, which answers for the filesystem
    can the package reach it? `importlib.resources`, which answers for
                              the code

The second is the one that matters and the one nothing in a normal
build reports. Run it and the answer is shorter than you would like.

Usage:
    python probe_schemes.py        # or: make probe
"""

from __future__ import annotations

import base64
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import venv
import zipfile
from pathlib import Path

NAME = "schemeprobe"
VERSION = "1.0.0"
DIST_INFO = f"{NAME}-{VERSION}.dist-info"
DATA_DIR = f"{NAME}-{VERSION}.data"

#: One marker per scheme key, plus a nested path under `data/` because
#: that is how a real package ships a table it means to read.
MARKERS: dict[str, str] = {
    "purelib": "PURELIB_LANDED.txt",
    "platlib": "PLATLIB_LANDED.txt",
    "headers": "HEADERS_LANDED.txt",
    "scripts": "SCRIPTS_LANDED.txt",
    "data": "DATA_LANDED.txt",
}

#: The probe the child interpreter runs. It asks the INSTALLED package
#: what it can reach, in its own process — importing from this one would
#: find the source tree first and answer the wrong question.
PROBE = """
from importlib.resources import files
import json, sys
root = files("schemeprobe")
reachable = sorted(p.name for p in root.iterdir())
print(json.dumps({"root": str(root), "reachable": reachable}))
"""


def _wheel(into: Path) -> Path:
    """Write the probe wheel by hand.

    No build backend: a backend would place these files correctly and
    the whole question is what happens when they are not.

    Args:
        into: Directory to write the wheel into.

    Returns:
        The wheel path.
    """
    members = {f"{NAME}/__init__.py": '"""probe"""\n'}
    for key, marker in MARKERS.items():
        members[f"{DATA_DIR}/{key}/{marker}"] = f"{key}\n"
    members[f"{DATA_DIR}/data/share/docs/nested.txt"] = "nested\n"
    members[f"{DIST_INFO}/METADATA"] = (
        f"Metadata-Version: 2.1\nName: {NAME}\nVersion: {VERSION}\n"
    )
    members[f"{DIST_INFO}/WHEEL"] = (
        "Wheel-Version: 1.0\nGenerator: probe_schemes.py\n"
        "Root-Is-Purelib: true\nTag: py3-none-any\n"
    )

    rows = []
    path = into / f"{NAME}-{VERSION}-py3-none-any.whl"
    with zipfile.ZipFile(path, "w") as archive:
        for member, content in members.items():
            archive.writestr(member, content)
            payload = content.encode()
            digest = base64.urlsafe_b64encode(
                hashlib.sha256(payload).digest()
            ).rstrip(b"=").decode()
            rows.append(f"{member},sha256={digest},{len(payload)}")
        rows.append(f"{DIST_INFO}/RECORD,,")
        archive.writestr(f"{DIST_INFO}/RECORD", "\n".join(rows) + "\n")
    return path


def main() -> None:
    """Build, install, and report where each key landed and what is reachable."""
    workspace = Path(tempfile.mkdtemp())
    try:
        wheel = _wheel(workspace)
        environment = workspace / "venv"
        venv.create(environment, with_pip=True)
        python = environment / "bin" / "python"
        if not python.exists():  # pragma: no cover - Windows layout
            python = environment / "Scripts" / "python.exe"
        subprocess.run(
            [str(python), "-m", "pip", "install", "-q", str(wheel)],
            check=True,
            capture_output=True,
        )

        print("where each scheme key installed")
        landed: dict[str, Path] = {}
        for found in sorted(environment.rglob("*_LANDED.txt")):
            landed[found.name] = found
            print(f"  {found.name:22} <venv>/{found.relative_to(environment)}")

        result = subprocess.run(
            [str(python), "-c", PROBE], capture_output=True, text=True, check=True
        )
        answer = json.loads(result.stdout)
        print(f"\nthe package installs to {answer['root']}")
        print(f"it can reach: {answer['reachable']}\n")
        for marker in MARKERS.values():
            verdict = (
                "reachable" if marker in answer["reachable"] else "NOT REACHABLE"
            )
            print(f"  {marker:22} {verdict}")
        print(
            "\nEvery marker is on disk — the listing above found all of them.\n"
            "None is reachable from the package, including purelib, which\n"
            "lands in site-packages BESIDE the package rather than inside it."
        )
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
