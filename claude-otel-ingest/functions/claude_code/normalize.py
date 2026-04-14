from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, Iterator, List, Optional


def _as_text(value: Any) -> Optional[str]:
    if value in (None, "", False):
        return None
    return str(value).strip() or None


def _as_int(value: Any, default: int = 0) -> int:
    if value in (None, "", False):
        return default
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, (int, float)):
        return int(value)
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def iter_days(start_date: date, end_date: date) -> Iterator[date]:
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


def _collapse_values(values: set[str]) -> Optional[Any]:
    cleaned = sorted(v for v in values if v)
    if not cleaned:
        return None
    if len(cleaned) == 1:
        return cleaned[0]
    return cleaned


def _new_core_metrics() -> Dict[str, Any]:
    return {
        "commits_by_claude_code": 0,
        "lines_of_code": {"added": 0, "removed": 0},
        "num_sessions": 0,
        "pull_requests_by_claude_code": 0,
    }


def _new_token_totals() -> Dict[str, int]:
    return {
        "input": 0,
        "output": 0,
        "cache_creation": 0,
        "cache_read": 0,
    }


def build_actor_usage(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    actors: Dict[str, Dict[str, Any]] = {}

    for record in records:
        if not isinstance(record, dict):
            continue

        actor_payload = record.get("actor") if isinstance(record.get("actor"), dict) else {}
        actor_type = _as_text(actor_payload.get("type"))
        email_address = _as_text(actor_payload.get("email_address"))
        api_key_name = _as_text(actor_payload.get("api_key_name"))

        if actor_type == "user_actor" or email_address:
            actor_type = "user_actor"
            actor_label = email_address or "unknown"
            actor_key = f"user:{actor_label.lower()}"
        elif actor_type == "api_actor" or api_key_name:
            actor_type = "api_actor"
            actor_label = api_key_name or "unknown"
            actor_key = f"api_key:{actor_label}"
        else:
            actor_type = actor_type or "unknown"
            actor_label = "unknown"
            actor_key = "unknown"

        entry = actors.setdefault(
            actor_key,
            {
                "actor_key": actor_key,
                "actor_type": actor_type,
                "actor_label": actor_label,
                "email_address": email_address,
                "api_key_name": api_key_name,
                "customer_type": set(),
                "subscription_type": set(),
                "organization_ids": set(),
                "terminal_types": set(),
                "_dates": set(),
                "core_metrics": _new_core_metrics(),
                "tool_actions": {},
                "_model_breakdown": {},
            },
        )

        if email_address and not entry.get("email_address"):
            entry["email_address"] = email_address
        if api_key_name and not entry.get("api_key_name"):
            entry["api_key_name"] = api_key_name

        date_value = _as_text(record.get("date"))
        if date_value:
            entry["_dates"].add(date_value)

        customer_type = _as_text(record.get("customer_type"))
        if customer_type:
            entry["customer_type"].add(customer_type)

        subscription_type = _as_text(record.get("subscription_type"))
        if subscription_type:
            entry["subscription_type"].add(subscription_type)

        organization_id = _as_text(record.get("organization_id"))
        if organization_id:
            entry["organization_ids"].add(organization_id)

        terminal_type = _as_text(record.get("terminal_type"))
        if terminal_type:
            entry["terminal_types"].add(terminal_type)

        core_metrics = record.get("core_metrics") if isinstance(record.get("core_metrics"), dict) else {}
        lines = core_metrics.get("lines_of_code") if isinstance(core_metrics.get("lines_of_code"), dict) else {}
        entry["core_metrics"]["commits_by_claude_code"] += _as_int(core_metrics.get("commits_by_claude_code"))
        entry["core_metrics"]["lines_of_code"]["added"] += _as_int(lines.get("added"))
        entry["core_metrics"]["lines_of_code"]["removed"] += _as_int(lines.get("removed"))
        entry["core_metrics"]["num_sessions"] += _as_int(core_metrics.get("num_sessions"))
        entry["core_metrics"]["pull_requests_by_claude_code"] += _as_int(core_metrics.get("pull_requests_by_claude_code"))

        tool_actions = record.get("tool_actions") if isinstance(record.get("tool_actions"), dict) else {}
        for tool_name, action_payload in tool_actions.items():
            tool = _as_text(tool_name) or "unknown"
            action = action_payload if isinstance(action_payload, dict) else {}
            tool_entry = entry["tool_actions"].setdefault(tool, {"accepted": 0, "rejected": 0})
            tool_entry["accepted"] += _as_int(action.get("accepted"))
            tool_entry["rejected"] += _as_int(action.get("rejected"))

        model_breakdown = record.get("model_breakdown") if isinstance(record.get("model_breakdown"), list) else []
        for model_payload in model_breakdown:
            if not isinstance(model_payload, dict):
                continue

            model_name = _as_text(model_payload.get("model")) or "unknown"
            model_entry = entry["_model_breakdown"].setdefault(
                model_name,
                {
                    "model": model_name,
                    "estimated_cost_by_currency": {},
                    "tokens": _new_token_totals(),
                },
            )

            estimated_cost = model_payload.get("estimated_cost") if isinstance(model_payload.get("estimated_cost"), dict) else {}
            currency = _as_text(estimated_cost.get("currency")) or "unknown"
            amount = _as_int(estimated_cost.get("amount"))
            if amount:
                model_entry["estimated_cost_by_currency"][currency] = (
                    _as_int(model_entry["estimated_cost_by_currency"].get(currency)) + amount
                )

            tokens = model_payload.get("tokens") if isinstance(model_payload.get("tokens"), dict) else {}
            for token_key in ("input", "output", "cache_creation", "cache_read"):
                model_entry["tokens"][token_key] += _as_int(tokens.get(token_key))

    results: List[Dict[str, Any]] = []
    for entry in actors.values():
        dates = sorted(entry.pop("_dates"))
        models = sorted(
            entry.pop("_model_breakdown").values(),
            key=lambda item: (
                -sum(item.get("estimated_cost_by_currency", {}).values()),
                -(item.get("tokens", {}).get("input", 0) + item.get("tokens", {}).get("output", 0)),
                item.get("model", ""),
            ),
        )
        results.append(
            {
                "actor_key": entry["actor_key"],
                "actor_type": entry["actor_type"],
                "actor_label": entry["actor_label"],
                "email_address": entry.get("email_address"),
                "api_key_name": entry.get("api_key_name"),
                "customer_type": _collapse_values(entry["customer_type"]),
                "subscription_type": _collapse_values(entry["subscription_type"]),
                "organization_ids": sorted(entry["organization_ids"]),
                "terminal_types": sorted(entry["terminal_types"]),
                "active_days": len(dates),
                "dates": dates,
                "core_metrics": entry["core_metrics"],
                "tool_actions": dict(sorted(entry["tool_actions"].items())),
                "model_breakdown": models,
            }
        )

    results.sort(
        key=lambda item: (
            -item["core_metrics"]["lines_of_code"]["added"],
            -item["core_metrics"]["num_sessions"],
            item["actor_label"],
        )
    )
    return results


def build_analytics_summary(records: List[Dict[str, Any]], by_actor: List[Dict[str, Any]]) -> Dict[str, Any]:
    totals = _new_core_metrics()
    customer_types: set[str] = set()
    subscription_types: set[str] = set()
    cost_by_currency: Dict[str, int] = {}
    model_totals: Dict[str, Dict[str, Any]] = {}

    for actor in by_actor:
        core_metrics = actor.get("core_metrics") if isinstance(actor.get("core_metrics"), dict) else {}
        lines = core_metrics.get("lines_of_code") if isinstance(core_metrics.get("lines_of_code"), dict) else {}
        totals["commits_by_claude_code"] += _as_int(core_metrics.get("commits_by_claude_code"))
        totals["lines_of_code"]["added"] += _as_int(lines.get("added"))
        totals["lines_of_code"]["removed"] += _as_int(lines.get("removed"))
        totals["num_sessions"] += _as_int(core_metrics.get("num_sessions"))
        totals["pull_requests_by_claude_code"] += _as_int(core_metrics.get("pull_requests_by_claude_code"))

        customer_type = actor.get("customer_type")
        if isinstance(customer_type, list):
            customer_types.update(_as_text(v) for v in customer_type if _as_text(v))
        else:
            value = _as_text(customer_type)
            if value:
                customer_types.add(value)

        subscription_type = actor.get("subscription_type")
        if isinstance(subscription_type, list):
            subscription_types.update(_as_text(v) for v in subscription_type if _as_text(v))
        else:
            value = _as_text(subscription_type)
            if value:
                subscription_types.add(value)

        for model_payload in actor.get("model_breakdown", []):
            if not isinstance(model_payload, dict):
                continue
            model_name = _as_text(model_payload.get("model")) or "unknown"
            model_entry = model_totals.setdefault(
                model_name,
                {
                    "model": model_name,
                    "estimated_cost_by_currency": {},
                    "tokens": _new_token_totals(),
                },
            )
            for currency, amount in (model_payload.get("estimated_cost_by_currency") or {}).items():
                currency_name = _as_text(currency) or "unknown"
                model_entry["estimated_cost_by_currency"][currency_name] = (
                    _as_int(model_entry["estimated_cost_by_currency"].get(currency_name)) + _as_int(amount)
                )
                cost_by_currency[currency_name] = _as_int(cost_by_currency.get(currency_name)) + _as_int(amount)

            tokens = model_payload.get("tokens") if isinstance(model_payload.get("tokens"), dict) else {}
            for token_key in ("input", "output", "cache_creation", "cache_read"):
                model_entry["tokens"][token_key] += _as_int(tokens.get(token_key))

    return {
        "record_count": len(records),
        "actor_count": len(by_actor),
        "customer_types": sorted(customer_types),
        "subscription_types": sorted(subscription_types),
        "totals": totals,
        "cost_by_currency": cost_by_currency,
        "model_breakdown": sorted(
            model_totals.values(),
            key=lambda item: (
                -sum(item.get("estimated_cost_by_currency", {}).values()),
                -(item.get("tokens", {}).get("input", 0) + item.get("tokens", {}).get("output", 0)),
                item.get("model", ""),
            ),
        ),
    }


def build_seat_usage(users: List[Dict[str, Any]], by_actor: List[Dict[str, Any]]) -> Dict[str, Any]:
    usage_by_email = {
        str(actor["email_address"]).strip().lower(): actor
        for actor in by_actor
        if isinstance(actor, dict) and _as_text(actor.get("email_address"))
    }
    matched_actor_keys: set[str] = set()

    seats: List[Dict[str, Any]] = []
    for user in users:
        if not isinstance(user, dict):
            continue

        email = _as_text(user.get("email"))
        usage = usage_by_email.get(email.lower()) if email else None
        if usage:
            matched_actor_keys.add(str(usage.get("actor_key")))

        seats.append(
            {
                "user_id": _as_text(user.get("id")),
                "email": email,
                "name": _as_text(user.get("name")),
                "role": _as_text(user.get("role")),
                "added_at": _as_text(user.get("added_at")),
                "has_usage": usage is not None,
                "customer_type": usage.get("customer_type") if usage else None,
                "subscription_type": usage.get("subscription_type") if usage else None,
                "active_days": _as_int(usage.get("active_days")) if usage else 0,
                "usage": usage.get("core_metrics") if usage else _new_core_metrics(),
                "models": usage.get("model_breakdown", []) if usage else [],
                "tool_actions": usage.get("tool_actions", {}) if usage else {},
                "actor_key": usage.get("actor_key") if usage else None,
            }
        )

    seats.sort(
        key=lambda item: (
            0 if item["has_usage"] else 1,
            -item["usage"]["lines_of_code"]["added"],
            -item["usage"]["num_sessions"],
            item.get("email") or "",
        )
    )

    unmatched_actors = [
        actor
        for actor in by_actor
        if isinstance(actor, dict) and _as_text(actor.get("actor_key")) not in matched_actor_keys
    ]

    return {
        "count": len(seats),
        "active_count": sum(1 for seat in seats if seat["has_usage"]),
        "inactive_count": sum(1 for seat in seats if not seat["has_usage"]),
        "records": seats,
        "unmatched_actors": unmatched_actors,
    }


__all__ = ["iter_days", "build_actor_usage", "build_analytics_summary", "build_seat_usage"]
