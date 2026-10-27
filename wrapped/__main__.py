"""Print the Wrapped stats for local history PDFs: python -m wrapped history.pdf [more.pdf ...]"""
import sys
from pathlib import Path

import pandas as pd

from . import ParseError, build_wrapped, parse_pdfs


def main(paths):
    if not paths:
        sys.exit(__doc__)
    try:
        tx = parse_pdfs(Path(p).read_bytes() for p in paths)
        wrapped = build_wrapped(tx)
    except ParseError as e:
        sys.exit(str(e))

    pd.set_option("display.width", 200)
    print(f"{wrapped.semester}: {len(tx)} charges from {wrapped.start:%b %d} to {wrapped.end:%b %d}\n")
    print(tx["kind"].value_counts().to_string(), "\n")
    print(wrapped.swipes, "\n")
    print(wrapped.vendors, "\n")
    print(f"Meal swipes: {wrapped.total_swipes}   Dining dollars: ${wrapped.total_spent:.2f}")
    print(f"Laundry: {wrapped.laundry}")
    print(f"Personalities: {', '.join(p.name for p in wrapped.personalities)}")


if __name__ == "__main__":
    main(sys.argv[1:])
