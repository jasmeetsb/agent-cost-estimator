"""Workflow Operator archetype — Moderate complexity.

Single agent that executes a structured back-office process (order fulfillment)
with heavy tool fan-out (~8 tools/turn against business systems). Matches the
calculator's Workflow Operator / Moderate column: ~4 turns/query, 40% turns with
tools, 8 tools/turn.

Intended model tier: Gemini 3.0 Flash. Deployed on gemini-2.5-flash.
The 8 tools stand in for real backend/API calls (would be fronted by Apigee +
BigQuery in production); implemented locally so the agent is deployable.
"""

from google.adk.agents import Agent
from google.adk.tools import load_memory

from .fs_state import save_note, load_note

MODEL = "gemini-2.5-flash"

_ORDERS = {
    "ORD-1001": {"item": "wireless mouse", "qty": 2, "status": "pending", "address": "ok"},
    "ORD-1002": {"item": "mechanical keyboard", "qty": 1, "status": "pending", "address": "ok"},
    "ORD-1003": {"item": "usb-c hub", "qty": 3, "status": "pending", "address": "missing_zip"},
}


def lookup_order(order_id: str) -> dict:
    """Fetch an order record by ID."""
    o = _ORDERS.get(order_id.strip().upper())
    return {"status": "ok", "order": o} if o else {"status": "error", "message": "order not found"}


def check_inventory(item: str, qty: int) -> dict:
    """Check whether `qty` of `item` is in stock."""
    in_stock = 50  # canned
    return {"status": "ok", "item": item, "requested": qty, "in_stock": in_stock, "available": qty <= in_stock}


def validate_address(order_id: str) -> dict:
    """Validate the shipping address on an order."""
    o = _ORDERS.get(order_id.strip().upper(), {})
    ok = o.get("address") == "ok"
    return {"status": "ok" if ok else "invalid", "valid": ok,
            "issue": None if ok else "missing ZIP code"}


def calculate_shipping(item: str, qty: int, express: bool) -> dict:
    """Calculate shipping cost and ETA."""
    base = 5.0 + 1.5 * qty
    cost = base * (2 if express else 1)
    return {"status": "ok", "cost_usd": round(cost, 2), "eta_days": 2 if express else 5}


def apply_discount(order_id: str, code: str) -> dict:
    """Apply a discount code to an order."""
    valid = {"SAVE10": 0.10, "WELCOME": 0.15}
    pct = valid.get(code.strip().upper())
    return {"status": "ok", "applied": bool(pct), "discount_pct": (pct or 0) * 100}


def update_order_status(order_id: str, new_status: str) -> dict:
    """Update the status of an order (e.g. confirmed, shipped)."""
    if order_id.strip().upper() in _ORDERS:
        return {"status": "ok", "order_id": order_id, "new_status": new_status}
    return {"status": "error", "message": "order not found"}


def send_notification(order_id: str, channel: str) -> dict:
    """Notify the customer about their order via a channel (email/sms)."""
    return {"status": "ok", "order_id": order_id, "channel": channel, "sent": True}


def log_transaction(order_id: str, action: str) -> dict:
    """Write an audit-log entry for an order action."""
    return {"status": "ok", "logged": f"{action} on {order_id}"}


root_agent = Agent(
    name="workflow_operator",
    model=MODEL,
    description="Order-fulfillment operator that drives a multi-step workflow across backend tools.",
    instruction=(
        "You are an order-fulfillment operator. For each order, run the workflow end to end: "
        "look up the order, check inventory, validate the address, calculate shipping, apply any "
        "discount, update the order status, send a customer notification, and log the transaction. "
        "Before processing, ALWAYS call load_memory to recall prior interactions with this customer, "
        "and use load_note (topic = order id) to check for prior order history; after "
        "completing, persist the outcome with save_note (topic = order id). "
        "Handle errors (e.g. invalid address) before proceeding, and report a concise summary."
    ),
    tools=[lookup_order, check_inventory, validate_address, calculate_shipping,
           apply_discount, update_order_status, send_notification, log_transaction,
           save_note, load_note, load_memory],
)
