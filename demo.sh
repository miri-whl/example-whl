#!/usr/bin/env bash
# Install both wheels and show what differs. Nothing here is contrived:
# the two wheels are built from one source tree by build.py, and the
# Python source inside them is byte-identical.
set -u

here="$(cd "$(dirname "$0")" && pwd)"

# With no argument, show both side by side. With one, show just that.
kinds=("$@")
if [ ${#kinds[@]} -eq 0 ]; then kinds=(good bad); fi

python3 "$here/build.py" "${kinds[@]}" >/dev/null

for kind in "${kinds[@]}"; do
  venv="$(mktemp -d)/venv"
  python3 -m venv "$venv"
  "$venv/bin/pip" install -q "$here/dist/$kind/tinystat-1.0.0-py3-none-any.whl" 2>/dev/null

  echo "───────────── $kind wheel ─────────────"
  echo "pip install: OK (no warnings, no errors)"
  VENV_ROOT="$venv" "$venv/bin/python" - <<'PY'
import os
import tinystat

root = os.environ["VENV_ROOT"]
sample = [10.2, 10.4, 10.1, 10.3]
print(f"  import       OK, version {tinystat.__version__}")
print(f"  mean         {tinystat.mean(sample):.4f}")
print(f"  stdev        {tinystat.stdev(sample):.4f}")
# Each call is probed on its own. One try around both would stop at the
# first failure and hide the interesting half: confidence_interval opens
# no file in its life and goes down anyway, because it asks t_critical
# for a number.
try:
    print(f"  t_critical   {tinystat.t_critical(10, 0.05)}")
except FileNotFoundError as error:
    print("  t_critical   FileNotFoundError")
    print(f"               looked in {error.filename.replace(root, '<venv>')}")
try:
    low, high = tinystat.confidence_interval(sample)
    print(f"  95% CI       {low:.4f} to {high:.4f}")
except FileNotFoundError:
    print("  95% CI       FileNotFoundError")
    print("               opens no file itself; it calls t_critical")
PY
  echo "  the table actually installed to:"
  find "$venv" -name t-table.json 2>/dev/null | sed "s|$venv|               <venv>|"
  echo
done
