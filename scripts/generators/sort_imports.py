#!/usr/bin/env python3
"""Sorts and de-duplicates the import block of generated Java files (Google style).

Static imports come first, then a blank line, then all other imports in ASCII order. Run by
`render_template` in scripts/common.sh because template placeholders make the order of the
`org.purplebean.kmip.{{pdot}}.{{NAME}}` import depend on the substituted values.

Usage: sort_imports.py <file.java>...
"""
import re
import sys


def sort_imports(path):
    lines = open(path, encoding="utf-8").read().split("\n")
    idx = [i for i, line in enumerate(lines) if re.match(r"import\s+[\w.*]+\s*;|import static\s", line)]
    if not idx:
        return
    first, last = idx[0], idx[-1]
    block = lines[first:last + 1]
    imports = [line for line in block if line.startswith("import ")]
    if any(line.strip() and not line.startswith("import ") for line in block):
        return  # something other than imports in the block: leave the file alone
    static = sorted({line for line in imports if line.startswith("import static ")})
    normal = sorted({line for line in imports if not line.startswith("import static ")},
                    key=lambda line: line[len("import "):-1])
    out = static + ([""] if static and normal else []) + normal
    lines[first:last + 1] = out
    open(path, "w", encoding="utf-8").write("\n".join(lines))


for p in sys.argv[1:]:
    sort_imports(p)
