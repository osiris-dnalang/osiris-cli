import json
from pathlib import Path
from typing import Any, Dict


def load_config(config_path: str | Path) -> Dict[str, Any]:
    """Load JSON or YAML configuration files with an optional PyYAML dependency."""
    path = Path(config_path)
    suffix = path.suffix.lower()
    content = path.read_text(encoding="utf-8")

    if suffix == ".json":
        return json.loads(content)

    if suffix in {".yaml", ".yml"}:
        try:
            import yaml
        except ImportError as exc:
            raise RuntimeError(
                "YAML support requires PyYAML. Install it with 'pip install pyyaml'."
            ) from exc
        return yaml.safe_load(content) or {}

    raise ValueError(f"Unsupported config format: {path.suffix}")


def dump_json(data: Dict[str, Any], destination: str | Path) -> Path:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    return path