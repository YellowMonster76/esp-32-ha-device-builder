"""Compare two ESPHome configs by their fully merged result.

Runs `esphome config` on both and compares the output as data, so key order
doesn't matter, and list items that all have an `id` are matched by id (so
moving a sensor or script to another package isn't a difference). Lists
without ids, like `interval:`, are compared in order. Use it after a refactor (e.g. splitting a single-file config
into board/project/device packages): no differences means the firmware
behaves the same.

  python tools/compare_configs.py old/cyd-bus-display.yaml cyd-bus-display.yaml

Each file is validated from its own folder, so each needs a secrets.yaml
there (or above it) with the same secret names. `substitutions` are ignored:
they're inputs, and their effect already shows in the rest of the config.
Lambda code is compared as text, so a reworded lambda shows as a difference.

Needs esphome on PATH (or set ESPHOME=path\\to\\esphome) and PyYAML.
"""
import os
import subprocess
import sys
from pathlib import Path

import yaml

ESPHOME = os.environ.get("ESPHOME", "esphome")


class _Loader(yaml.SafeLoader):
    pass


# Keep ESPHome's tags (!secret, !lambda) as plain text so they compare.
_Loader.add_multi_constructor(
    "!",
    lambda loader, tag, node: f"{tag} {loader.construct_scalar(node)}"
    if isinstance(node, yaml.ScalarNode) else loader.construct_object(node),
)


def merged(path):
    path = Path(path).resolve()
    r = subprocess.run([ESPHOME, "config", path.name], cwd=path.parent,
                       capture_output=True, text=True, encoding="utf-8")
    if "Configuration is valid" not in r.stdout + r.stderr:
        sys.exit(f"INVALID: {path}\n{(r.stdout + r.stderr)[-2000:]}")
    text = "\n".join(l for l in r.stdout.splitlines() if not l.startswith(("INFO ", "WARNING ")))
    data = yaml.load(text, Loader=_Loader)
    data.pop("substitutions", None)
    return data


def ids(items):
    """{id: item} if every item is a mapping with a unique id, else None."""
    if not items or not all(isinstance(x, dict) and "id" in x for x in items):
        return None
    keyed = {f"id={x['id']}": x for x in items}
    return keyed if len(keyed) == len(items) else None


def walk(a, b, path="", diffs=None):
    diffs = [] if diffs is None else diffs
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b), key=str):
            if k not in a:
                diffs.append(f"+ {path}/{k}: {b[k]!r}")
            elif k not in b:
                diffs.append(f"- {path}/{k}: {a[k]!r}")
            else:
                walk(a[k], b[k], f"{path}/{k}", diffs)
    elif isinstance(a, list) and isinstance(b, list) and ids(a) and ids(b):
        # Every item has an id (scripts, sensors...): match them by id, so
        # moving a component to another package (which changes the merged
        # order) doesn't count as a difference.
        walk(ids(a), ids(b), path, diffs)
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)):
            walk(x, y, f"{path}[{i}]", diffs)
    elif a != b:
        diffs.append(f"~ {path}:\n    old: {a!r}\n    new: {b!r}")
    return diffs


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    diffs = walk(merged(sys.argv[1]), merged(sys.argv[2]))
    for d in diffs:
        print(d[:600])
    print("IDENTICAL" if not diffs else f"-- {len(diffs)} difference(s)")
