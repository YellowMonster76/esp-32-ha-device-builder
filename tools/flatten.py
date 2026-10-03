"""Flatten device files into single paste-ready YAML files, keeping comments.

A device file here is `packages:` (base + board + project) plus its own
settings. Device Builder is happiest with one self-contained file, so this
merges them the way ESPHome merges packages, but as text, so every comment
survives:

- substitutions: combined; a later file's value replaces an earlier one's,
  in the earlier position (so the board's explanation sits above the device's
  actual value),
- mapping sections found in several files (esphome:, api:, wifi:): entries
  combined (a key defined twice is an error),
- list sections: items combined; a `- id: !extend X` item is folded into the
  item with `id: X` (a single-line value replaces the original; anything else
  defined twice is an error),
- `packages:` is dropped.

Output goes to single-file/<device>.yaml with a "generated" header listing the
secrets it needs. Anything it can't merge cleanly stops with an error rather
than guessing. After generating, prove the result with:
  python tools/compare_configs.py cyd-bus-display.yaml single-file/cyd-bus-display.yaml

  python tools/flatten.py                  # every device file at the top level
  python tools/flatten.py cyd-light-panel-8tile.yaml
  python tools/flatten.py --check          # exit 1 if single-file/ is out of date
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "single-file"
KEY_RE = re.compile(r"^([a-z_][a-z0-9_]*):")          # top-level key
CHILD_KEY_RE = re.compile(r"^  ([A-Za-z0-9_]+):")     # key at indent 2
ITEM_KEY_RE = re.compile(r"^    ([A-Za-z0-9_]+):")    # key at indent 4 (inside a list item)
INCLUDE_RE = re.compile(r"^\s+\w+:\s*!include\s+(\S+)\s*$")


class FlattenError(Exception):
    pass


def indent_of(line):
    return len(line) - len(line.lstrip(" "))


def is_content(line):
    s = line.strip()
    return bool(s) and not s.startswith("#")


def parse(path):
    """Split a YAML file into (preamble, {key: [lines]}) at top-level keys.
    Comments and blank lines directly above a key belong to that key."""
    lines = path.read_text(encoding="utf-8").splitlines()
    preamble, blocks, pending, cur = [], {}, [], None
    for line in lines:
        m = KEY_RE.match(line)
        if m:
            cur = m.group(1)
            if cur in blocks:
                raise FlattenError(f"{path.name}: top-level key {cur!r} appears twice")
            if not blocks:                      # comments before the first key
                preamble, pending = pending, []
            blocks[cur] = pending + [line]
            pending = []
        elif cur and line.startswith((" ", "\t")):
            blocks[cur].extend(pending)
            pending = []
            blocks[cur].append(line)
        elif not line.strip() or line.startswith("#"):
            pending.append(line)
        else:
            raise FlattenError(f"{path.name}: can't parse line: {line!r}")
    if cur:
        blocks[cur].extend(pending)
    else:
        preamble = pending
    return strip_blank(preamble), {k: strip_blank(v, top=False) for k, v in blocks.items()}


def strip_blank(lines, top=True):
    while lines and not lines[-1].strip():
        lines = lines[:-1]
    if top:
        while lines and not lines[0].strip():
            lines = lines[1:]
    return lines


def split_header(block):
    """-> (comments above the key, key line, child lines)."""
    i = next(i for i, l in enumerate(block) if KEY_RE.match(l))
    return block[:i], block[i], block[i + 1:]


def is_list(children):
    first = next((l for l in children if is_content(l)), None)
    return first is not None and first.lstrip().startswith("- ")


def reindent_comments(comments, n=2):
    return [(" " * n + l.lstrip()) if l.strip() else l for l in strip_blank(comments)]


# ---- substitutions -----------------------------------------------------------
def merge_substitutions(blocks, sources):
    out, where = [], {}                 # where[key] = index in out
    for src, block in zip(sources, blocks):
        _, header, children = split_header(block)
        if not out:
            out.append(header)
        section = [f"  # --- from {src} ---"] if len(blocks) > 1 else []
        new_keys = {}                   # key -> index within section
        pending = []
        for i, line in enumerate(children):
            m = CHILD_KEY_RE.match(line)
            if m:
                nxt = next((l for l in children[i + 1:] if is_content(l)), None)
                if nxt is not None and indent_of(nxt) > 2:
                    raise FlattenError(f"{src}: substitution {m.group(1)!r} isn't a one-line value")
                key = m.group(1)
                if key in where or key in new_keys:
                    if key in new_keys:
                        raise FlattenError(f"{src}: substitution {key!r} defined twice")
                    # override: new value, original position, say where it's from
                    out[where[key]] = line if "#" in line else f"{line}  # set in {src}"
                    pending = []
                    continue
                section.extend(pending)
                pending = []
                new_keys[key] = len(section)
                section.append(line)
            elif is_content(line):
                raise FlattenError(f"{src}: unexpected substitutions line {line!r}")
            else:
                pending.append(line)
        section.extend(pending)
        section = strip_blank(section, top=False)
        if new_keys:
            if len(out) > 1:
                out.append("")
            offset = len(out)           # positions are known only once placed
            out.extend(section)
            for key, local in new_keys.items():
                where[key] = offset + local
    return out


# ---- mappings ----------------------------------------------------------------
def child_keys(children):
    return [m.group(1) for l in children if (m := CHILD_KEY_RE.match(l))]


def merge_mapping(key, blocks, sources):
    comments, header, children = split_header(blocks[0])
    out = comments + [header] + children
    seen = set(child_keys(children))
    for src, block in zip(sources[1:], blocks[1:]):
        c, _, ch = split_header(block)
        dup = seen & set(child_keys(ch))
        if dup:
            raise FlattenError(f"{key}: {sorted(dup)} defined in more than one file ({src})")
        seen |= set(child_keys(ch))
        out = strip_blank(out, top=False)
        out += [""] + reindent_comments(c) + [f"  # (from {src})"] + ch
    return out


# ---- lists -------------------------------------------------------------------
def split_items(children, src):
    """-> (lines before the first item, [item lines]); comments above an item
    belong to it."""
    lead, items, pending = [], [], []
    for line in children:
        if re.match(r"^  - ", line):
            items.append(pending + [line])
            pending = []
        elif items and (indent_of(line) >= 4 and line.strip()):
            items[-1].extend(pending)
            pending = []
            items[-1].append(line)
        elif not is_content(line):
            pending.append(line)
        elif not items:
            lead.append(line)
        else:
            raise FlattenError(f"{src}: can't place list line {line!r}")
    if items:
        items[-1].extend(pending)
    else:
        lead.extend(pending)
    return lead, items


def item_id(item):
    for line in item:
        m = re.match(r"^  (?:- |  )id:\s*(!extend\s+)?(\S+)\s*$", line)
        if m:
            return bool(m.group(1)), m.group(2)
    return False, None


def entries(lines):
    """Split item lines at indent-4 keys -> [[key, comments_above, [lines]]].
    Comment/blank lines directly above a key belong to it; key None = the
    item's first line(s) before any indent-4 key."""
    out, pending = [], []
    for line in lines:
        m = ITEM_KEY_RE.match(line)
        if m:
            out.append([m.group(1), pending, [line]])
            pending = []
        elif not is_content(line):
            pending.append(line)
        elif out:
            out[-1][2].extend(pending + [line])
            pending = []
        else:
            out.append([None, pending, [line]])
            pending = []
    if out:
        out[-1][2].extend(pending)
    return out


def fold_extend(target, ext, src, xid):
    body = [l for l in ext if not re.match(r"^  - id:\s*!extend", l)]
    tgt = entries(target)
    for key, pre, lines in entries(body):
        if key is None:
            raise FlattenError(f"{src}: !extend {xid}: unexpected line {lines[0]!r}")
        pre = [("    " + l.lstrip()) if l.strip() else l for l in strip_blank(pre)]
        hit = next((e for e in tgt if e[0] == key), None)
        if hit is None:
            tgt.append([key, pre + [f"    # (from {src})"], lines])
        elif all(not is_content(l) for l in hit[2][1:]) and all(not is_content(l) for l in lines[1:]):
            new = hit[2][0].split(":")[0] + ":" + lines[0].split(":", 1)[1].split("#")[0].rstrip()
            hit[1] = hit[1] + pre
            hit[2] = [f"{new}  # set in {src}"] + hit[2][1:]
        else:
            raise FlattenError(f"{src}: !extend {xid} redefines {key!r}, which isn't a one-line value")
    return [l for _, pre, ls in tgt for l in pre + ls]


def merge_list(key, blocks, sources):
    comments, header, children = split_header(blocks[0])
    lead, items = split_items(children, sources[0])
    for src, block in zip(sources[1:], blocks[1:]):
        c, _, ch = split_header(block)
        l2, it2 = split_items(ch, src)
        if any(is_content(l) for l in l2):
            raise FlattenError(f"{src}: {key}: content before the first item")
        for n, item in enumerate(it2):
            ext, xid = item_id(item)
            if ext:
                idx = next((i for i, t in enumerate(items) if item_id(t) == (False, xid)), None)
                if idx is None:
                    raise FlattenError(f"{src}: !extend {xid}: no {key} item with that id")
                extra = reindent_comments(c) if n == 0 else []
                items[idx] = fold_extend(items[idx], extra + item, src, xid)
            else:
                items.append((reindent_comments(c) if n == 0 else []) + item)
    return comments + [header] + lead + [l for it in items for l in it]


# ---- one device --------------------------------------------------------------
def flatten(device):
    dev_pre, dev_blocks = parse(device)
    if "packages" not in dev_blocks:
        raise FlattenError(f"{device.name}: no packages: block, nothing to flatten")
    sources = []
    for line in dev_blocks["packages"]:
        m = INCLUDE_RE.match(line)
        if m:
            sources.append(m.group(1))
        elif is_content(line) and not KEY_RE.match(line):
            raise FlattenError(f"{device.name}: only `name: !include path` packages are supported: {line!r}")
    parsed = [(s, *parse((device.parent / s).resolve())) for s in sources]
    parsed.append((device.name, [], {k: v for k, v in dev_blocks.items() if k != "packages"}))

    order, seen = [], set()               # (source index, key) of first appearance
    for i, (_, _, blocks) in enumerate(parsed):
        for k in blocks:
            if k not in seen:
                seen.add(k)
                order.append((i, k))

    body, last_src = [], None
    for i, key in order:
        having = [(s, b[key]) for s, _, b in parsed if key in b]
        srcs, blocks = [s for s, _ in having], [b for _, b in having]
        if key == "substitutions":
            merged = merge_substitutions(blocks, srcs)
        elif len(blocks) == 1:
            merged = blocks[0]
        elif is_list(split_header(blocks[0])[2]):
            merged = merge_list(key, blocks, srcs)
        else:
            merged = merge_mapping(key, blocks, srcs)
        if i != last_src and parsed[i][1]:      # the source's own header, once
            body += ["", ""] + parsed[i][1]
        last_src = i
        body += [""] + strip_blank(merged)

    code = "\n".join(l.split("#")[0] for l in body if not l.lstrip().startswith("#"))
    secrets = sorted(set(re.findall(r":\s*!secret\s+([A-Za-z0-9_]+)", code)))
    head = [
        "# " + "=" * 77,
        f"#  GENERATED single-file version of {device.name}.",
        "#  Paste the whole file into ESPHome Device Builder. Don't edit it here:",
        "#  edit the source files, then run `python tools/flatten.py`.",
        "#",
        "#  Built from:",
    ] + [f"#    {s}" for s in sources + [device.name]] + [
        "#",
        "#  Secrets it needs in Device Builder's secrets.yaml:",
    ] + [f"#    {s}" for s in secrets] + [
        "# " + "=" * 77,
        "",
    ] + dev_pre
    return "\n".join(head + body).rstrip() + "\n"


def device_files():
    return sorted(p for p in ROOT.glob("*.yaml")
                  if not p.name.startswith("secrets") and "packages:" in p.read_text(encoding="utf-8"))


def main(argv):
    check = "--check" in argv
    names = [a for a in argv if not a.startswith("--")]
    devices = [ROOT / n for n in names] if names else device_files()
    OUT_DIR.mkdir(exist_ok=True)
    stale = []
    for dev in devices:
        try:
            text = flatten(dev)
        except FlattenError as e:
            sys.exit(f"ERROR: {e}")
        out = OUT_DIR / dev.name
        if check:
            if not out.exists() or out.read_text(encoding="utf-8") != text:
                stale.append(out.name)
        else:
            out.write_text(text, encoding="utf-8", newline="\n")
            print(f"written {out.relative_to(ROOT)} ({text.count(chr(10))} lines)")
    if check:
        print("out of date: " + ", ".join(stale) if stale else "single-file/ is up to date")
        sys.exit(1 if stale else 0)


if __name__ == "__main__":
    main(sys.argv[1:])
