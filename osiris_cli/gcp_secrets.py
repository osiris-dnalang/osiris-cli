"""Read OSIRIS's keys from Google Secret Manager instead of plaintext ~/.env.

Opt-in: with OSIRIS_SECRETS_SOURCE=gcp and OSIRIS_GCP_PROJECT set (in the environment or ~/.env),
every secret in that project labelled osiris=env and named OSIRIS_<VAR> is read with your gcloud
login and exported as <VAR>, unless <VAR> is already set (the shell and ~/.env still win).
Read-only: this module never creates, changes or deletes a secret, and never prints a value.
"""
import base64
import json
import os
import urllib.error
import urllib.request

API = "https://secretmanager.googleapis.com/v1"
PREFIX = "OSIRIS_"
last_result = {"loaded": [], "skipped": [], "error": None}


def _get(url, token, project, timeout):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}", "x-goog-user-project": project})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read() or b"{}")


def load_into_environ(project=None, token=None, timeout=5.0, fetch=_get):
    """Export labelled secrets into os.environ. Returns the names loaded; never raises."""
    from osiris_cli import gemini_gateway as gw
    last_result.update(loaded=[], skipped=[], error=None)
    try:
        project = project or gw.gcp_settings()[0]
        if not project:
            last_result["error"] = "OSIRIS_GCP_PROJECT not set"
            return []
        token = token or gw._gcp_token()
        if not token:
            last_result["error"] = "no gcloud access token"
            return []
        listing = fetch(f"{API}/projects/{project}/secrets?filter=labels.osiris%3Denv&pageSize=100", token, project, timeout)
        for s in listing.get("secrets", []):
            sid = s["name"].rsplit("/", 1)[-1]
            if not sid.startswith(PREFIX):
                continue
            var = sid[len(PREFIX):]
            if os.environ.get(var):
                last_result["skipped"].append(var)
                continue
            data = fetch(f"{API}/{s['name']}/versions/latest:access", token, project, timeout)
            os.environ[var] = base64.b64decode(data["payload"]["data"]).decode("utf-8")
            last_result["loaded"].append(var)
    except (urllib.error.URLError, OSError, ValueError, KeyError) as e:
        last_result["error"] = type(e).__name__
    return list(last_result["loaded"])


def wanted():
    """True when the user opted in (OSIRIS_SECRETS_SOURCE=gcp in the environment or ~/.env)."""
    from osiris_cli import gemini_gateway as gw
    return (os.environ.get("OSIRIS_SECRETS_SOURCE") or gw.load_env().get("OSIRIS_SECRETS_SOURCE", "")).strip() == "gcp"
