#!/usr/bin/env python3
"""Generate a small CycloneDX-style SBOM for the current Python environment."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def read_project_metadata() -> dict[str, str]:
    pyproject = PROJECT_ROOT / "pyproject.toml"
    name = "cleanmac"
    version = "0.0.0"
    for raw_line in pyproject.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("name = "):
            name = line.split("=", 1)[1].strip().strip('"')
        elif line.startswith("version = "):
            version = line.split("=", 1)[1].strip().strip('"')
    return {"name": name, "version": version}


def distribution_component(dist: metadata.Distribution) -> dict[str, Any] | None:
    name = dist.metadata.get("Name")
    version = dist.version
    if not name or not version:
        return None
    return {
        "type": "library",
        "name": name,
        "version": version,
        "purl": f"pkg:pypi/{name.lower().replace('_', '-')}@{version}",
    }


def build_sbom() -> dict[str, Any]:
    project = read_project_metadata()
    components = []
    seen = set()
    for dist in sorted(metadata.distributions(), key=lambda item: (item.metadata.get("Name") or "").lower()):
        component = distribution_component(dist)
        if component is None:
            continue
        key = (component["name"].lower(), component["version"])
        if key in seen:
            continue
        seen.add(key)
        components.append(component)

    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:{hashlib.sha256(project['name'].encode()).hexdigest()[:32]}",
        "version": 1,
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "component": {
                "type": "application",
                "name": project["name"],
                "version": project["version"],
            },
            "tools": [
                {
                    "vendor": "cleanmac",
                    "name": "scripts/generate_sbom.py",
                    "version": project["version"],
                }
            ],
        },
        "components": components,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, help="Path to write the SBOM JSON file")
    args = parser.parse_args(argv)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(build_sbom(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
