#!/usr/bin/env python3
"""
vision_indexer.py -- incremental, hash-based indexer over Termux's shared
screenshot storage, feeding OSIRIS's sprint backlog.

Real Gemini REST calls can't take "the whole screenshots folder" in one
request, so this hashes every image found under ~/storage/pictures and
~/storage/dcim (same broad-search approach /vision latest's discovery
already uses -- not hardcoded to one "Screenshots" subfolder name, since
that varies by device/OEM), keeps a local index of what's already been
digested (~/.osiris/vision_index.json, keyed by content hash so a renamed-
but-unchanged file doesn't get reprocessed and a changed file does), and
sends only new/changed images to Gemini in small batches.

On-demand only -- this never runs on its own; it's invoked by /vision
sync-sprint in the REPL.
"""
import hashlib
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gemini_bridge  # noqa: E402

VISION_INDEX_PATH = os.path.join(os.path.expanduser("~"), ".osiris", "vision_index.json")
BATCH_SIZE = 4
_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")

NO_CONTEXT_SENTINEL = "NO_ARCHITECTURAL_CONTEXT"

# The shared screenshot folder is the whole device's history, not an OSIRIS
# design folder -- an earlier prompt that assumed every image was a terminal
# or blueprint turned unrelated web-browsing screenshots into UI/UX stories
# (court-record page layouts, 2026-09-23). Relevance is judged per image.
SYSTEM_PROMPT = (
    "You are the OSIRIS Systems Architect. You are given a batch of screenshots "
    "from a phone's shared screenshot folder. MOST of them are likely unrelated to "
    "OSIRIS. Judge each image individually.\n\n"
    "An image is RELEVANT only if it shows terminal output, source code, an error "
    "traceback, or a software/system architecture diagram or blueprint. Standard "
    "web browsing, websites, documents, social media, and other unrelated apps are "
    "NOT relevant -- ignore them completely, including their UI/UX, and never "
    "invent stories about them.\n\n"
    "For each concrete, actionable engineering problem visible in a RELEVANT image, "
    "output one line in EXACTLY this format:\n"
    "STORY: As a user, I want <X> so that <Y> | COMPLEXITY: <1-3>\n\n"
    f"If the image is unrelated to terminal outputs, code, or system architecture "
    f"(e.g., standard web browsing or unrelated apps), explicitly return "
    f"'{NO_CONTEXT_SENTINEL}' and do not generate User Stories. If no image in the "
    f"batch is relevant, output exactly {NO_CONTEXT_SENTINEL} and nothing else.\n"
    "Output nothing else -- no preamble, no markdown, no summary paragraph."
)


def _find_storage_images():
    """Same broad-search approach as osiris's _find_latest_screenshot(), but
    returns every image found, not just the newest one."""
    storage_root = os.path.join(os.path.expanduser("~"), "storage")
    if not os.path.isdir(storage_root):
        return [], "~/storage not found -- run 'termux-setup-storage' first and grant the permission prompt."
    roots = [os.path.join(storage_root, d) for d in ("pictures", "dcim")]
    roots = [p for p in roots if os.path.isdir(p)]
    if not roots:
        return [], "~/storage exists but has neither a pictures/ nor dcim/ link."

    found = []
    for root in roots:
        for dirpath, _dirnames, filenames in os.walk(root):
            for fn in filenames:
                if fn.lower().endswith(_IMAGE_EXTS):
                    found.append(os.path.join(dirpath, fn))
    return found, None


def _hash_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_index():
    if not os.path.exists(VISION_INDEX_PATH):
        return {}
    try:
        with open(VISION_INDEX_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_index(index):
    os.makedirs(os.path.dirname(VISION_INDEX_PATH), exist_ok=True)
    tmp = VISION_INDEX_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)
    os.replace(tmp, VISION_INDEX_PATH)


def find_unprocessed(max_images=None):
    """Returns [(path, hash), ...] for images whose current content hash
    isn't already marked processed in the index -- new files, and files
    whose content changed since they were last indexed."""
    images, err = _find_storage_images()
    if err:
        return [], err
    index = _load_index()
    unprocessed = []
    for path in images:
        try:
            h = _hash_file(path)
        except OSError:
            continue
        entry = index.get(path)
        if entry is None or entry.get("hash") != h or not entry.get("processed"):
            unprocessed.append((path, h))
    if max_images:
        unprocessed = unprocessed[:max_images]
    return unprocessed, None


def digest_batch(pairs):
    """pairs: [(path, hash), ...], real number of images sent in ONE actual
    Gemini request (not N calls stitched together). Marks each processed in
    the index only after a successful response -- a failed batch stays
    unprocessed so a retry picks it back up."""
    if not pairs:
        return ""
    paths = [p for p, _h in pairs]
    digest = gemini_bridge.query_with_images(SYSTEM_PROMPT, "Analyze this batch.", paths, timeout=90)
    index = _load_index()
    for path, h in pairs:
        index[path] = {"hash": h, "processed": True, "digested_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    _save_index(index)
    return digest


def run_incremental(max_total=12):
    """Processes up to max_total unprocessed images in BATCH_SIZE-sized real
    Gemini calls. Returns (combined_digest_text, processed_paths, error_or_None)
    -- error is set only on a hard stop (no key, no storage); a batch that
    fails mid-run just stops there and returns what succeeded so far."""
    if not gemini_bridge.is_configured():
        return "", [], "GEMINI_API_KEY not set -- vision indexing needs it (local models can't do vision here)."
    unprocessed, err = find_unprocessed(max_images=max_total)
    if err:
        return "", [], err
    if not unprocessed:
        return "", [], "no new/unprocessed images found"

    all_digest = []
    all_processed = []
    for i in range(0, len(unprocessed), BATCH_SIZE):
        batch = unprocessed[i:i + BATCH_SIZE]
        try:
            digest = digest_batch(batch)
        except gemini_bridge.GeminiUnavailable as e:
            reason = f"Gemini call failed mid-run (processed {len(all_processed)} of {len(unprocessed)} before this): {e}"
            return "\n".join(all_digest), all_processed, (reason if not all_processed else None)
        all_digest.append(digest)
        all_processed.extend(p for p, _h in batch)
    return "\n".join(all_digest), all_processed, None


if __name__ == "__main__":
    digest, processed, error = run_incremental()
    if error:
        print(f"[!] {error}")
    else:
        print(f"Processed {len(processed)} image(s):")
        for p in processed:
            print(f"  {p}")
        print("\nDigest:\n" + digest)
