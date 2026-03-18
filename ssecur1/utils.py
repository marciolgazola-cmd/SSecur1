import json
import re
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from ssecur1.db import ClientModel


BRAZIL_TZ = ZoneInfo("America/Sao_Paulo")


def loads_json(raw: str | None, fallback: Any) -> Any:
    if not raw:
        return fallback
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return fallback


def now_brasilia() -> datetime:
    return datetime.now(BRAZIL_TZ)


def utc_naive_to_brasilia(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=ZoneInfo("UTC"))
    return value.astimezone(BRAZIL_TZ)


def format_display_date(value: str | datetime | None) -> str:
    if value in {None, "", "-"}:
        return "-"
    if isinstance(value, datetime):
        local_value = utc_naive_to_brasilia(value)
        return local_value.strftime("%d-%m-%Y") if local_value else "-"
    raw = str(value).strip()
    if not raw:
        return "-"
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw, fmt).strftime("%d-%m-%Y")
        except ValueError:
            continue
    return raw


def format_display_datetime(value: str | datetime | None, include_seconds: bool = False) -> str:
    if value in {None, "", "-"}:
        return "-"
    if isinstance(value, datetime):
        local_value = utc_naive_to_brasilia(value)
    else:
        raw = str(value).strip()
        if not raw:
            return "-"
        parsed = None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d-%m-%Y %H:%M:%S", "%d-%m-%Y %H:%M"):
            try:
                parsed = datetime.strptime(raw, fmt)
                break
            except ValueError:
                continue
        if parsed is None:
            try:
                parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            except ValueError:
                return raw
        local_value = utc_naive_to_brasilia(parsed)
    if not local_value:
        return "-"
    return local_value.strftime("%d-%m-%Y %H:%M:%S" if include_seconds else "%d-%m-%Y %H:%M")


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
