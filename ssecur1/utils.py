import json
import re
from typing import Any

from ssecur1.db import ClientModel


def loads_json(raw: str | None, fallback: Any) -> Any:
    if not raw:
        return fallback
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return fallback


def question_payload(options_json: str | None) -> dict[str, Any]:
    parsed = loads_json(options_json, [])
    if isinstance(parsed, dict):
        options = parsed.get("options", [])
        logic = parsed.get("logic", {})
        return {
            "options": options if isinstance(options, list) else [],
            "logic": logic if isinstance(logic, dict) else {},
        }
    if isinstance(parsed, list):
        return {"options": parsed, "logic": {}}
    return {"options": [], "logic": {}}


def slugify(value: str) -> str:
    return value.strip().lower().replace(" ", "-")


def dom_token(value: str) -> str:
    token = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    return token.strip("-") or "item"


def build_client_children_map(rows: list[ClientModel]) -> dict[int, list[int]]:
    children_map: dict[int, list[int]] = {}
    for row in rows:
        if row.parent_client_id is not None:
            children_map.setdefault(int(row.parent_client_id), []).append(int(row.id))
    return children_map


def collect_descendant_client_ids(children_map: dict[int, list[int]], root_id: int) -> set[int]:
    collected: set[int] = set()
    stack = [root_id]
    while stack:
        current = stack.pop()
        for child_id in children_map.get(current, []):
            if child_id in collected:
                continue
            collected.add(child_id)
            stack.append(child_id)
    return collected


def parse_int(value: str) -> int | None:
    cleaned = re.sub(r"[^\d]", "", value or "")
    return int(cleaned) if cleaned else None


def parse_brl_amount(value: str) -> int | None:
    cleaned = (value or "").strip()
    if not cleaned:
        return None
    digits = re.sub(r"[^\d]", "", cleaned)
    return int(digits) if digits else None


def format_brl_amount(value: int | None) -> str:
    if value is None:
        return "-"
    formatted = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"


def dimension_maturity_label(score: int) -> str:
    if score <= 10:
        return "Reativo"
    if score <= 15:
        return "Dependente"
    if score <= 20:
        return "Independente"
    return "Interdependente"
