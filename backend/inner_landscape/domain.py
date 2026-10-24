from __future__ import annotations

import copy
import math
import re
import uuid
from datetime import datetime, timezone
from typing import Any

REGIONS = ("sky", "ridge", "water")
CLIENTS = ("demo-jamie", "demo-alex", "demo-robin")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def event(
    session: dict, kind: str, text: str, source: str = "coordinator", **extra: Any
) -> dict:
    item = dict(
        event_id=str(uuid.uuid4()),
        session_id=session["id"],
        cycle_id=session["cycle"],
        source=source,
        schema_version=1,
        at=now(),
        type=kind,
        text=text,
        **extra,
    )
    session["events"].append(item)
    return item


def validate_workspace(value: dict) -> dict:
    if not isinstance(value, dict) or value.get("version") != 1:
        raise ValueError("Unsupported workspace schema")
    if not isinstance(value.get("notes"), dict) or not isinstance(
        value.get("sessions"), list
    ):
        raise ValueError("Invalid workspace")
    if len(value["sessions"]) > 100 or len(value["notes"]) > 10:
        raise ValueError("Demo workspace limit reached")
    if any(
        k not in CLIENTS or not isinstance(v, str) or len(v) > 10000
        for k, v in value["notes"].items()
    ):
        raise ValueError("Invalid notes")
    seen = set()
    active = 0
    for s in value["sessions"]:
        if (
            s.get("clientId") not in CLIENTS
            or not isinstance(s.get("id"), str)
            or not 1 <= len(s["id"]) <= 100
            or s["id"] in seen
        ):
            raise ValueError("Invalid or duplicate session")
        seen.add(s["id"])
        if (
            s.get("status") not in ("active", "paused", "completed")
            or s.get("region") not in REGIONS
        ):
            raise ValueError("Invalid session state")
        active += s["status"] != "completed"
        if any(
            type(s.get("depth", {}).get(r)) is not int or not 0 <= s["depth"][r] <= 3
            for r in REGIONS
        ):
            raise ValueError("Invalid region depth")
        if (
            type(s.get("remaining")) not in (int, float)
            or not math.isfinite(s["remaining"])
            or not 0 <= s["remaining"] <= 30
        ):
            raise ValueError("Invalid cycle timer")
        if type(s.get("cycle")) is not int or not 1 <= s["cycle"] <= 1000:
            raise ValueError("Invalid cycle")
        if type(s.get("pendingCycle")) is not bool:
            raise ValueError("Invalid cycle state")
        for key, limit in (
            ("goal", 150),
            ("preNotes", 10000),
            ("postNotes", 10000),
            ("exclusions", 500),
        ):
            if not isinstance(s.get(key), str) or len(s[key]) > limit:
                raise ValueError("Invalid session field: " + key)
        if not isinstance(s.get("events"), list) or len(s["events"]) > 10000:
            raise ValueError("Invalid events")
        for e in s["events"]:
            if (
                not isinstance(e, dict)
                or not isinstance(e.get("text"), str)
                or len(e["text"]) > 5000
                or not isinstance(e.get("type"), str)
                or not isinstance(e.get("at"), str)
            ):
                raise ValueError("Invalid event")
    if active > 1:
        raise ValueError("Only one unfinished session is allowed")
    return copy.deepcopy(value)


def participant_view(s: dict) -> dict:
    # An allowlist, not a blacklist: private therapist fields cannot leak later.
    allowed = (
        "id",
        "status",
        "cycle",
        "remaining",
        "pendingCycle",
        "region",
        "depth",
        "media",
        "proposal",
        "spatialDecision",
        "source_hash",
    )
    result = {k: copy.deepcopy(s[k]) for k in allowed if k in s}
    result["events"] = [
        copy.deepcopy(e)
        for e in s["events"]
        if e["type"]
        in ("guide", "reflection", "selection", "decision", "cycle", "control")
    ]
    return result


def propose(s: dict) -> dict:
    dwell = s.get("attention", {})
    if s.get("attentionAt"):
        try:
            if (
                datetime.now(timezone.utc) - datetime.fromisoformat(s["attentionAt"])
            ).total_seconds() > 10:
                dwell = {}
        except ValueError:
            dwell = {}
    # Treat explicit region exclusions conservatively; arbitrary therapeutic topic
    # boundaries remain in guide context and practitioner supervision.
    excluded = {
        r
        for r in REGIONS
        if re.search(
            r"\b(?:no|avoid|exclude)\s+(?:the\s+)?" + r + r"\b",
            s.get("exclusions", "").lower(),
        )
    }
    allowed = [r for r in REGIONS if r not in excluded]
    if not allowed:
        return {
            "region": None,
            "reason": "All regions excluded; ask the practitioner",
            "requires_confirmation": True,
            "cycle": s["cycle"],
        }
    choice = (
        max(allowed, key=lambda r: dwell.get(r, 0))
        if any(dwell.values())
        else (s["region"] if s["region"] in allowed else allowed[0])
    )
    # Deliberately explainable baseline. Voice semantics remain with the guide;
    # neither pulse nor private notes enter the decision.
    return {
        "region": choice,
        "reason": "Most recent head-directed dwell"
        if any(dwell.values())
        else "Current explicitly selected region; no head tracking available",
        "requires_confirmation": True,
        "source": "heuristic",
        "cycle": s["cycle"],
        "at": now(),
    }


def command(s: dict, name: str, payload: dict, source: str) -> None:
    if s["status"] == "completed":
        raise ValueError("Session is completed")
    if name == "pause":
        s["status"] = "paused"
        event(s, "control", "Session paused", source)
    elif name == "stop":
        s["status"] = "completed"
        s["completedAt"] = now()
        event(s, "control", "Session finished", source)
    elif name == "resume":
        s["status"] = "active"
        event(s, "control", "Session resumed", source)
    elif name == "tracking_lost":
        s["status"] = "paused"
        s["attention"] = {}
        event(s, "control", "Head tracking lost; explicit resume required", source)
    elif name == "attention":
        if s["status"] != "active":
            raise ValueError("Resume before reporting attention")
        dwell = payload.get("dwell", {})
        if set(dwell) - set(REGIONS):
            raise ValueError("Unknown region")
        if (
            any(
                type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 30
                for v in dwell.values()
            )
            or sum(dwell.values()) > 31
        ):
            raise ValueError("Invalid attention window")
        if payload.get("cycle") != s["cycle"]:
            raise ValueError("Stale attention cycle")
        s["attention"] = dwell
        s["attentionAt"] = now()
        s["proposal"] = propose(s)
    elif name in ("spatial_decision", "spatial_select"):
        from .region_zoom import decision, manual_decision
        if s["status"] != "active" or not s.get("source_hash"):
            raise ValueError("Active session with a source image required")
        if s.get("spatialDecision", {}).get("cycle") == s["cycle"]:
            raise ValueError("Decision already frozen for this cycle")
        s["spatialDecision"] = (manual_decision if name == "spatial_select" else decision)(payload, s["cycle"], s["source_hash"])
        event(s, "decision", "Spatial attention frozen", source, cell=s["spatialDecision"]["cell"])
    elif name == "select":
        r = payload.get("region")
        if s["status"] != "active" or r not in REGIONS:
            raise ValueError("Invalid region selection")
        s["region"] = r
        event(s, "selection", "Confirmed " + r, source, region=r)
    elif name == "next":
        if s["status"] != "active" or not s["pendingCycle"]:
            raise ValueError("Current cycle has not ended")
        s["cycle"] += 1
        s["remaining"] = 30
        s["pendingCycle"] = False
        s["attention"] = {}
        s.pop("spatialDecision", None)
        event(s, "cycle", "Next cycle explicitly confirmed", source)
    elif name == "window_finished":
        if payload.get("cycle") != s["cycle"]:
            raise ValueError("Stale cycle")
        s["remaining"] = 0
        s["pendingCycle"] = True
        s["proposal"] = propose(s)
        event(s, "cycle", "Exploration window finished", source)
    else:
        raise ValueError("Unknown command")
