#!/usr/bin/env python3
"""
Batch-update all markdown files with ASCII art frame header and co-authorship.
This script is idempotent -- it only adds headers to files that don't already have them.
"""

import os
import glob

HEADER_MARKER = "co-authored by: devin phillip davis + OSIRIS dna::}{::lang NCLM"

SECTION_FRAME = """```
+===================================================================+
|  //\\\\ ::}{:: OSIRIS dna::}{::lang NCLM ::}{:: //\\\\               |
|  \\\\// ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ \\\\//               |
|       | {title:<40} |                      |
|  //\\\\ ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ //\\\\               |
|  \\\\// ::}{:: TORSION-LOCKED INSULATION ::}{:: \\\\//                |
+===================================================================+
|  co-authored by: devin phillip davis + OSIRIS dna::}{::lang NCLM  |
+===================================================================+
```

"""

FOOTER = """
---

```
+===================================================================+
|  co-authored by: devin phillip davis + OSIRIS dna::}{::lang NCLM  |
|  ::}{:: TORSION FRAME ::}{:: POLARIZED INSULATION BOUNDARY ::}{:: |
+===================================================================+
```
"""

# Files already updated (skip these)
SKIP_FILES = {
    "README.md",
    "OSIRIS_README.md",
    "paper.md",
    "REVIEWER_REBUTTAL.md",
}

def get_title_from_filename(filename):
    """Convert filename to a display title"""
    name = os.path.splitext(os.path.basename(filename))[0]
    name = name.replace("_", " ").replace("-", " ")
    # Truncate to fit in the frame
    if len(name) > 40:
        name = name[:37] + "..."
    return name

def update_file(filepath):
    """Add ASCII art frame header to a markdown file"""
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    # Skip if already has the header
    if HEADER_MARKER in content:
        print(f"  SKIP (already has header): {filepath}")
        return False

    title = get_title_from_filename(filepath)
    header = SECTION_FRAME.format(title=title)

    new_content = header + content + FOOTER
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"  UPDATED: {filepath}")
    return True

def main():
    base = "/workspaces/osiris-cli"
    updated = 0
    skipped = 0

    # Find all .md files
    patterns = [
        os.path.join(base, "*.md"),
        os.path.join(base, "physics", "*.md"),
        os.path.join(base, "quantum_discovery", "*.md"),
        os.path.join(base, "osiris-cli", "*.md"),
        os.path.join(base, "osiris-cli", "docs", "*.md"),
        os.path.join(base, "osiris-unified-substrate", "*.md"),
        os.path.join(base, "discoveries", "*.md"),
    ]

    all_files = []
    for pattern in patterns:
        all_files.extend(glob.glob(pattern))

    # Sort for consistent ordering
    all_files.sort()

    print(f"\nFound {len(all_files)} markdown files\n")

    for filepath in all_files:
        basename = os.path.basename(filepath)
        relpath = os.path.relpath(filepath, base)

        # Skip files already manually updated
        if relpath in SKIP_FILES or basename in SKIP_FILES:
            print(f"  SKIP (manual update): {relpath}")
            skipped += 1
            continue

        if update_file(filepath):
            updated += 1
        else:
            skipped += 1

    print(f"\nDone: {updated} updated, {skipped} skipped\n")

if __name__ == "__main__":
    main()
