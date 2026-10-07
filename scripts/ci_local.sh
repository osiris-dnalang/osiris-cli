#!/usr/bin/env bash
# Local CI for when GitHub Actions is unavailable. Runs the test suite on every
# Python found below with the home directory hidden (so sibling checkouts and
# ~/.osiris state cannot leak into the run), then a wheel-install smoke test.
#   scripts/ci_local.sh                 # all interpreters found
#   PYTHONS="python3.12" scripts/ci_local.sh
set -u
ROOT=$(cd "$(dirname "$0")/.." && pwd)
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
PYTHONS=${PYTHONS:-"$(for v in 3.9 3.10 3.11 3.12; do for p in "$HOME/.osiris/ci/venv-$v/bin/python" "$(command -v python$v)"; do [ -x "$p" ] && { echo "$p"; break; }; done; done)"}
git -C "$ROOT" ls-files -co --exclude-standard | grep -v '^results/' | tar -C "$ROOT" -cf - -T - | tar -xf - -C "$WORK"
status=0
for py in $PYTHONS; do
  ver=$("$py" -c 'import sys; print("%d.%d" % sys.version_info[:2])')
  if ! "$py" -c 'import pytest' 2>/dev/null; then echo "== $ver: skipped (no pytest in $py)"; continue; fi
  if unshare -r -m true 2>/dev/null; then
    real=$(cd "$(dirname "$py")/.." && pwd)
    unshare -r -m bash -c "mkdir -p /tmp/ci_py && mount --bind '$real' /tmp/ci_py && mount -t tmpfs tmpfs '$HOME' \
      && cd '$WORK' && HOME='$HOME' timeout 1200 /tmp/ci_py/bin/python -m pytest -q -p no:cacheprovider tests" > "$WORK/log_$ver" 2>&1
  else
    (cd "$WORK" && timeout 1200 "$py" -m pytest -q -p no:cacheprovider tests) > "$WORK/log_$ver" 2>&1
    echo "   (no user namespaces: home directory NOT hidden for $ver)"
  fi
  rc=$?; [ $rc -ne 0 ] && status=1
  echo "== $ver: $(tail -n 1 "$WORK/log_$ver")  [exit $rc]"
  [ $rc -ne 0 ] && grep -E '^(FAILED|ERROR)' "$WORK/log_$ver" | head -20
done
py=$(echo "$PYTHONS" | tail -n 1)
if "$py" -m pip --version >/dev/null 2>&1 && "$py" -m venv "$WORK/wv" >/dev/null 2>&1; then
  "$py" -m pip wheel -q --no-deps -w "$WORK/wheel" "$ROOT" && "$WORK/wv/bin/pip" install -q "$WORK"/wheel/*.whl \
    && (cd "$WORK" && env -u PYTHONPATH "$WORK/wv/bin/osiris" --help >/dev/null \
    && env -u PYTHONPATH "$WORK/wv/bin/python" -c "import osiris_cli, osiris_termux_console, protege, osiris_bench; print('== wheel: console', osiris_cli.__version__, '| bench tasks', len(osiris_bench.load_tasks()))") \
    || { echo "== wheel smoke FAILED"; status=1; }
fi
exit $status
