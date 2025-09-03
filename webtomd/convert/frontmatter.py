from __future__ import annotations

from typing import Dict, Optional


def _yaml_escape(value: str) -> str:
    if any(ch in value for ch in [":", "-", "#", "\n", "\r"]):
        return "|\n  " + "\n  ".join(value.splitlines())
    return f"'{value.replace("'", "''")}'"


def compose_front_matter(meta: Dict[str, str]) -> str:
    if not meta:
        return ""
    lines = ["---"]
    for k, v in meta.items():
        if isinstance(v, list):
            lines.append(f"{k}:")
            for item in v:
                lines.append(f"  - {_yaml_escape(str(item))}")
        else:
            lines.append(f"{k}: {_yaml_escape(str(v))}")
    lines.append("---\n")
    return "\n".join(lines)

