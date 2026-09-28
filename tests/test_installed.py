"""The tests that can tell the two wheels apart.

`test_stats.py` passes for both layouts and always will: it imports from
`src/`, where the lookup table sits beside the module that reads it.
Nothing about a source tree can answer the question "will this file be
reachable after installation", because in a source tree it already is.

So these tests do the only thing that answers it. They build both wheels,
install each into a throwaway virtualenv, and ask the installed package —
from a fresh interpreter, in a separate process — whether it can reach
its own data file.

That is expensive: a venv and a pip install per wheel. They are marked
`installed` so `make test` can run the fast suite and `make test-all`
can run everything. The expense is the reason this kind of test is rare,
and the reason this class of bug ships.
"""

from __future__ import annotations

import json
import subprocess
import sys
import venv
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
BUILD = REPO / "build.py"

pytestmark = pytest.mark.installed


def _wheel(kind: str) -> Path:
    """Build both wheels and return the one asked for.

    Args:
        kind: "good" or "bad".

    Returns:
        The built wheel's path.
    """
    subprocess.run(
        [sys.executable, str(BUILD)], cwd=REPO, check=True, capture_output=True
    )
    wheels = sorted((REPO / "dist" / kind).glob("*.whl"))
    assert wheels, f"build.py produced no {kind} wheel"
    return wheels[0]


def _install(kind: str, into: Path) -> Path:
    """Create a virtualenv and install one wheel into it.

    Args:
        kind: "good" or "bad".
        into: Directory to build the virtualenv in.

    Returns:
        The virtualenv's interpreter.
    """
    venv.create(into, with_pip=True)
    python = into / "bin" / "python"
    if not python.exists():  # pragma: no cover - Windows layout
        python = into / "Scripts" / "python.exe"
    subprocess.run(
        [str(python), "-m", "pip", "install", "-q", str(_wheel(kind))],
        check=True,
        capture_output=True,
    )
    return python


def _probe(python: Path, snippet: str) -> subprocess.CompletedProcess[str]:
    """Run one snippet in the installed environment.

    A separate process is not fastidiousness: importing the installed
    copy into this interpreter would find the source tree first and
    quietly answer the wrong question.

    Args:
        python: The virtualenv interpreter.
        snippet: Code to run.

    Returns:
        The completed process, not checked — the failing case is the
        interesting one.
    """
    return subprocess.run(
        [str(python), "-c", snippet], capture_output=True, text=True
    )


@pytest.fixture(scope="module")
def good(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """An interpreter with the good wheel installed.

    Returns:
        Its path.
    """
    return _install("good", tmp_path_factory.mktemp("good") / "venv")


@pytest.fixture(scope="module")
def bad(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """An interpreter with the bad wheel installed.

    Returns:
        Its path.
    """
    return _install("bad", tmp_path_factory.mktemp("bad") / "venv")


class TestBothWheelsLookFine:
    """Everything that does not read a file passes either way."""

    @pytest.mark.parametrize("which", ["good", "bad"])
    def test_it_imports(self, which: str, request: pytest.FixtureRequest) -> None:
        """Neither wheel fails at import, so neither fails at smoke test."""
        python = request.getfixturevalue(which)
        result = _probe(python, "import tinystat; print(tinystat.__version__)")
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == "1.0.0"

    @pytest.mark.parametrize("which", ["good", "bad"])
    def test_the_pure_functions_work(
        self, which: str, request: pytest.FixtureRequest
    ) -> None:
        """mean and stdev touch no files, so the bad wheel computes them.

        This is what makes the defect survive review. The functions a
        reviewer spot-checks are exactly the ones that cannot fail.
        """
        python = request.getfixturevalue(which)
        result = _probe(
            python,
            "import tinystat;"
            "print(round(tinystat.mean([10.2,10.4,10.1,10.3]),4),"
            "round(tinystat.stdev([10.2,10.4,10.1,10.3]),4))",
        )
        assert result.returncode == 0, result.stderr
        assert result.stdout.split() == ["10.25", "0.1291"]

    @pytest.mark.parametrize("which", ["good", "bad"])
    def test_pip_is_satisfied(
        self, which: str, request: pytest.FixtureRequest
    ) -> None:
        """`pip check` passes on both: the archives are valid."""
        python = request.getfixturevalue(which)
        result = subprocess.run(
            [str(python), "-m", "pip", "check"], capture_output=True, text=True
        )
        assert result.returncode == 0, result.stdout + result.stderr


class TestOnlyOneOfThemWorks:
    """The question a source-tree test cannot ask."""

    def test_the_good_wheel_reaches_its_table(self, good: Path) -> None:
        """The whole contract, in one call."""
        result = _probe(good, "import tinystat; print(tinystat.t_critical(10, 0.05))")
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == "2.228"

    def test_the_bad_wheel_cannot(self, bad: Path) -> None:
        """FileNotFoundError, at runtime, from a valid installed wheel."""
        result = _probe(bad, "import tinystat; tinystat.t_critical(10, 0.05)")
        assert result.returncode != 0
        assert "FileNotFoundError" in result.stderr

    def test_the_bad_wheel_shipped_the_file_anyway(self, bad: Path) -> None:
        """It is not missing. It is somewhere nothing looks.

        The distinction matters: a missing file is a build bug anyone
        would catch, and a file installed to the wrong scheme key looks
        like a successful build in every report you have.
        """
        venv_root = bad.parent.parent
        landed = list(venv_root.rglob("t-table.json"))
        assert landed, "the table did not install at all — different bug"
        assert not any("site-packages" in str(p) for p in landed), (
            "expected the bad wheel to install its table outside site-packages"
        )

    def test_the_two_wheels_carry_identical_source(self) -> None:
        """The difference is placement, not content.

        If this ever fails the demonstration is worthless, because a
        reader could attribute the failure to the code rather than to
        where it was put.
        """
        import zipfile

        contents = {}
        for kind in ("good", "bad"):
            with zipfile.ZipFile(_wheel(kind)) as archive:
                contents[kind] = {
                    Path(n).name: archive.read(n)
                    for n in archive.namelist()
                    if n.endswith(".py")
                }
        assert contents["good"] == contents["bad"]


class TestTheDataFileIsRealData:
    """Guard the fixture itself, so the demo cannot rot."""

    def test_the_table_has_both_levels(self) -> None:
        """0.05 and 0.01, as the docs promise."""
        table = json.loads((REPO / "src/tinystat/data/t-table.json").read_text())
        assert {"0.05", "0.01"} <= set(table)

    def test_the_published_values_are_the_published_values(self) -> None:
        """Spot-check against any statistics textbook."""
        table = json.loads((REPO / "src/tinystat/data/t-table.json").read_text())
        assert table["0.05"]["1"] == 12.706
        assert table["0.05"]["10"] == 2.228
        assert table["0.05"]["inf"] == 1.96
