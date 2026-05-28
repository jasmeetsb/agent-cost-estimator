"""Validate grounding + image collectors with workloads designed to trigger them.

- financial_advisor: an explicit "search the web for current info" prompt → grounding.
- marketing_agency: an explicit "generate the logo image" prompt → Imagen.

Captures raw events (prints part shapes), runs the event-based extractors, then
settles and reads the Cloud Monitoring grounding metric over the window.
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import vertexai
from vertexai import agent_engines

from agent_cost_estimator.usage import (
    collect_grounding_usage, extract_grounding_from_events, extract_image_count,
    price_grounding_and_media,
)

PROJECT, LOCATION = "jsb-genai-sa", "us-central1"
DATA = Path(__file__).resolve().parents[1] / "data"

TRIGGERS = {
    "financial_advisor": "Search the web for the most recent news and current price of NVDA "
                         "stock as of today, and cite the web sources you used.",
    "marketing_agency": "Generate the actual logo image for an oat-milk startup called OatJoy "
                        "(warm, friendly style) and return the generated image.",
}


def run_agent(pkg, msg):
    dep = json.loads((DATA / f"deployment_{pkg}.json").read_text())
    engine = agent_engines.get(dep["resource_name"])
    sid_obj = engine.create_session(user_id="validate")
    sid = sid_obj.get("id") if isinstance(sid_obj, dict) else sid_obj.id
    events = []
    for ev in engine.stream_query(user_id="validate", session_id=sid, message=msg):
        events.append(ev)
    # Show raw signal shapes.
    has_gm = False
    part_kinds = {}
    for ev in events:
        if isinstance(ev, dict):
            if ev.get("grounding_metadata") or (ev.get("content") or {}).get("grounding_metadata"):
                has_gm = True
            for p in (ev.get("content") or {}).get("parts") or []:
                for k in p:
                    part_kinds[k] = part_kinds.get(k, 0) + 1
    print(f"  events={len(events)} grounding_metadata_present={has_gm} part_kinds={part_kinds}")
    print(f"  extract_grounding_from_events={extract_grounding_from_events(events)} "
          f"extract_image_count={extract_image_count(events)}")
    return events


def main():
    vertexai.init(project=PROJECT, location=LOCATION)
    win_start = datetime.now(timezone.utc) - timedelta(seconds=60)

    print("== financial_advisor (grounding trigger) ==")
    run_agent("financial_advisor", TRIGGERS["financial_advisor"])
    print("== marketing_agency (image trigger) ==")
    run_agent("marketing_agency", TRIGGERS["marketing_agency"])

    settle = 300
    print(f"\nWaiting {settle}s for Monitoring ingestion (grounding metric)...")
    time.sleep(settle)
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    w0, w1 = win_start.strftime(fmt), datetime.now(timezone.utc).strftime(fmt)
    g = collect_grounding_usage(PROJECT, w0, w1)
    print("\n=== VALIDATION RESULT ===")
    print("window:", [w0, w1])
    print("Cloud Monitoring grounded web-search requests:", g["web_search_requests"])
    print("priced:", json.dumps(price_grounding_and_media(g["web_search_requests"], 0), indent=2))


if __name__ == "__main__":
    main()
