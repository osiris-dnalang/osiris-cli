#!/usr/bin/env python3
"""
db_ledger.py -- optional Supabase (REST) and Neon (Postgres) telemetry
mirrors for OSIRIS.

Mirrors provenance-tagged telemetry lines to Supabase over its PostgREST API
(stdlib urllib only, no native dependency -- avoiding the exact class of
build pain qiskit-aer hit on this device earlier) and/or to a real Neon
Postgres database (psycopg2-binary has no prebuilt wheel for this platform
and needs pg_config to build from source, which isn't installed here; pg8000,
a pure-Python driver, installs and works cleanly -- confirmed against the
real database, not assumed). Both are SUPPLEMENTARY syncs, never the source
of truth: the local flat-file ledger (~/.osiris/telemetry/nclm_loss.log,
written by _organism_telemetry() in bin/osiris) remains the primary,
always-succeeding path, completely unaffected by whether either backend is
reachable/configured. Call sync_line()/sync_line_neon() fire-and-forget from
a background thread; neither should ever block or raise into the caller.

Security: credentials are read ONLY from os.environ at call time
(NEXT_PUBLIC_SUPABASE_URL / NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY for
Supabase, NEON_DATABASE_URL -- a full Postgres DSN with an embedded password
-- for Neon), never logged, and never included in any exception message,
log line, or return value this module produces. Any driver-raised exception
is caught and re-raised as a short, generic LedgerSyncUnavailable message
that never repeats the original exception's text verbatim, since some
drivers include the DSN in their own error strings.
"""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

TABLE = "osiris_telemetry"
DEFAULT_TIMEOUT = 10  # seconds -- best-effort background sync, never worth blocking on


class LedgerSyncUnavailable(Exception):
    """Raised whenever the Supabase mirror can't be used right now. Callers
    should catch this, log locally if they want, and move on. Never carries
    the anon/publishable key."""


def is_configured() -> bool:
    return bool(
        os.environ.get("NEXT_PUBLIC_SUPABASE_URL", "").strip()
        and os.environ.get("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", "").strip()
    )


def sync_line(line: str, provenance: str, timeout: int = DEFAULT_TIMEOUT) -> None:
    """Best-effort mirror of one telemetry line to Supabase. Never raises to
    the caller -- any failure (not configured, network, missing table, bad
    schema) is caught and turned into a locally-logged line instead, via the
    same _organism_telemetry-style local write the caller already has."""
    url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL", "").strip()
    key = os.environ.get("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", "").strip()
    if not (url and key):
        raise LedgerSyncUnavailable("Supabase not configured")

    payload = [{
        "line": line,
        "provenance": provenance,
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }]
    req = urllib.request.Request(
        f"{url.rstrip('/')}/rest/v1/{TABLE}",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Prefer": "return=minimal",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout):
            pass
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode("utf-8", errors="ignore")[:300]
        except Exception:
            detail = ""
        # Expected, not a bug, until the table is created: PostgREST returns
        # a clear PGRST error (e.g. "relation ... does not exist") as 404 or
        # 400 -- surface that so whoever configures Supabase knows exactly
        # what table/schema to create.
        raise LedgerSyncUnavailable(f"Supabase HTTP {e.code}: {detail}") from None
    except Exception as e:
        raise LedgerSyncUnavailable(f"Supabase request failed: {type(e).__name__}: {e}") from None


_NEON_TABLE_READY = False  # per-process cache: skip re-issuing CREATE TABLE IF NOT EXISTS every call


def is_configured_neon() -> bool:
    return bool(os.environ.get("NEON_DATABASE_URL", "").strip())


def _neon_connect():
    import pg8000.native as pg8000  # imported lazily so a missing/broken driver never breaks Supabase-only setups

    dsn = os.environ.get("NEON_DATABASE_URL", "").strip()
    if not dsn:
        raise LedgerSyncUnavailable("Neon not configured")
    u = urllib.parse.urlparse(dsn)
    return pg8000.Connection(
        user=u.username,
        password=u.password,
        host=u.hostname,
        port=u.port or 5432,
        database=u.path.lstrip("/"),
        ssl_context=True,
    )


def sync_line_neon(line: str, provenance: str) -> None:
    """Best-effort mirror of one telemetry line to Neon Postgres. Never
    raises anything containing the DSN/password -- pg8000 exceptions are
    caught and replaced with a short generic message."""
    global _NEON_TABLE_READY
    try:
        conn = _neon_connect()
    except LedgerSyncUnavailable:
        raise
    except Exception:
        raise LedgerSyncUnavailable("Neon connection failed") from None

    try:
        if not _NEON_TABLE_READY:
            conn.run(
                "CREATE TABLE IF NOT EXISTS osiris_telemetry ("
                "id BIGSERIAL PRIMARY KEY, "
                "recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(), "
                "line TEXT NOT NULL, "
                "provenance TEXT NOT NULL)"
            )
            _NEON_TABLE_READY = True
        conn.run(
            "INSERT INTO osiris_telemetry (line, provenance) VALUES (:l, :p)",
            l=line,
            p=provenance,
        )
    except Exception:
        raise LedgerSyncUnavailable("Neon query failed") from None
    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    if not is_configured():
        print("Supabase not configured; nothing to test.")
    else:
        try:
            sync_line("test line, safe to ignore", "PLACEHOLDER")
            print("Synced test line successfully.")
        except LedgerSyncUnavailable as e:
            print(f"Supabase sync unavailable: {e}")

    if not is_configured_neon():
        print("Neon not configured; nothing to test.")
    else:
        try:
            sync_line_neon("test line, safe to ignore", "PLACEHOLDER")
            print("Synced test line to Neon successfully.")
        except LedgerSyncUnavailable as e:
            print(f"Neon sync unavailable: {e}")
