"""The half of the library that needs a file.

`t_critical` looks its answer up in `data/t-table.json`, shipped in this
package. Every interesting thing about wheel layout follows from that
one sentence: the table has to be somewhere, and only one somewhere
survives installation attached to this module.

`importlib.resources` is the only supported way to reach it. Reading
`Path(__file__).parent / "data"` happens to work for a plain install
and breaks inside a zipimport or any loader that does not put your
package on a real filesystem, which is why the stdlib grew this API.
"""

import json
from importlib.resources import files

#: Where the table lives, relative to this package.
TABLE = "data/t-table.json"

_cache = None


def _table():
    """The parsed lookup table, read once.

    Returns:
        Alpha, as a string, to degrees-of-freedom to critical value.

    Raises:
        FileNotFoundError: The data file did not ship inside the
            package. This is the failure this example exists to show:
            the wheel installed, the import worked, and the table is
            not reachable from the code that needs it.
    """
    global _cache
    if _cache is None:
        _cache = json.loads(files("tinystat").joinpath(TABLE).read_text())
    return _cache


def t_critical(df, alpha=0.05):
    """The two-tailed critical value of Student's t.

    Args:
        df: Degrees of freedom, one less than the sample size.
        alpha: Significance level; 0.05 and 0.01 are tabulated.

    Returns:
        The critical value. Between tabulated rows it takes the next df
        BELOW, which errs wide — the safe direction, since the other way
        would claim more confidence than the table supports. Past the
        last row it takes the `inf` value, because t converges on the
        normal there and holding df=30's figure forever would be wide
        without being more correct.

    Raises:
        KeyError: The significance level is not tabulated.
        FileNotFoundError: The table did not ship with the package.
    """
    rows = _table()[str(alpha)]
    tabulated = sorted(int(key) for key in rows if key != "inf")
    if df > tabulated[-1]:
        return rows["inf"]
    for key in reversed(tabulated):
        if key <= df:
            return rows[str(key)]
    return rows[str(tabulated[0])]
