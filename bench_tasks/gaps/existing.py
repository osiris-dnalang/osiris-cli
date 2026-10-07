"""gaps -- pull 'capability gap' descriptions out of logged prompts."""
import re

_GAP_RE = re.compile(r"capability gap[:\s]*(.{0,160})", re.IGNORECASE)


def extract_gaps(prompts):
    """Returns the gap text found in each prompt that mentions one."""
    found = []
    for text in prompts:
        m = _GAP_RE.search(text)
        if m:
            gap = m.group(1).strip().rstrip(".")
            if gap:
                found.append(gap)
    return found
