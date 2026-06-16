# SKU Usage Summary — `workflow-operator (archetype)` (workflow_operator)

- **Source:** google/adk-samples · **Model:** gemini-2.5-flash · **Engine:** `2142278010198294528`
- **Use case:** Order-fulfillment workflow operator · **Complexity:** Archetype: Workflow Operator / Moderate
- **Unit:** 1 interaction = 2–5-turn (varying) conversation + memory-write (14.0 model calls avg), averaged over **118 interactions**. Deployed on Vertex AI Agent Engine (GEAP).
- **Focus:** measured **usage per SKU**; dollar cost is a secondary derived view (§6).

## 1. Architecture

```mermaid
graph TB
    User([User]) --> Op
    subgraph Engine["Agent Engine — workflow_operator"]
        direction TB
        Op["operator_agent (Gemini 2.5 Flash)"]
        Op --> T1[lookup_order]
        Op --> T2[check_inventory]
        Op --> T3[validate_address]
        Op --> T4[calculate_shipping]
        Op --> T5[apply_discount]
        Op --> T6[update_order_status]
        Op --> T7[send_notification]
        Op --> T8[log_transaction]
    end
    subgraph Core["Always-on Agent Platform SKUs"]
        direction LR
        Gemini[("Gemini 2.5 Flash<br/>per-token (high tool fan-out)")]
        Runtime[("Agent Runtime<br/>vCPU + memory-sec")]
        Sess[("Sessions<br/>per event appended")]
        MB[("Memory Bank<br/>per memory + gen tokens")]
    end
    Engine -.-> Core
    T1 -.->|prod: via| Backend[(BigQuery / Apigee-fronted APIs)]
```

Single agent that drives an order-fulfillment workflow end to end with heavy tool fan-out (archetype: Workflow Operator, Moderate). 8 tools — lookup_order, check_inventory, validate_address, calculate_shipping, apply_discount, update_order_status, send_notification, log_transaction. Tool-fan-out-driven: measured ~12.5 model calls / ~25 session events per 2-turn interaction (highest tool churn of the four archetypes). Tools stand in for backend/API calls (Apigee + BigQuery in prod).

**Pattern:** Single agent + heavy tool fan-out (8 tools)

## 2. SKUs (products) consumed

Gemini tokens; Agent Runtime (vCPU + memory); Sessions; Memory Bank. (Backend tool calls mocked — would bill BigQuery + Apigee in production.)

(Sessions + Agent Runtime are automatic on Agent Engine; Memory Bank generation exercised via add_session_to_memory. Search grounding / Imagen used by the agent but usage not yet metered here — see §7.)

## 3. How usage was measured

Deployed to Agent Engine; per run = 2–5-turn (varying) conversation in one session + add_session_to_memory; **118 runs** for variability; 300s Monitoring settle; token usage from the model response (`usage_metadata`, exact), runtime + Memory Bank usage from Cloud Monitoring (per-engine).
Reproduce: `python scripts/exp_sample.py --package workflow_operator --runs 118 --settle 300`

## 4. SKU usage per interaction (PRIMARY)

Measured usage quantities per interaction (avg over 118 runs), with run-to-run range and variability.

| SKU dimension | Unit | Typical | Range | Variability |
|---|---|---|---|---|
| Gemini input tokens | tokens | 20107 | 3343–74345 | High |
| Gemini output tokens (incl. thinking) | tokens | 1485 | 419–3502 | High |
| Model calls | calls | 14.0 | — | Medium |
| Agent Runtime — vCPU | vCPU-seconds | 25.3 | — | — |
| Agent Runtime — memory | GiB-seconds | 46.8 | — | — |
| Sessions | events appended | 27.9 | — | Medium |
| Memory Bank — generation | tokens | 2549 | — | — |
| Memory Bank — memories written | memories | 1.1 | — | — |
| Memory Bank — retrievals | reads | 0.7 | — | — |
| Firestore — document writes | writes | 1.42 | — | — |
| Firestore — document reads | reads | 1.23 | — | — |


## 5. Grounding & media usage

- **Google Search grounding:** 0 measured. The agent does not use google_search in this workload; would bill ~$14/1K grounded turns if used.
- **Image generation (Imagen):** 0 images measured (from response events). Would bill ~$0.04/image if used.

## 5b. Caveats on usage capture

- vCPU/GiB-seconds are amortized over the measurement window (utilization-dependent).
- Memory storage (stored-memory count over time) is export-only.
- Grounding count is project-wide (no per-engine label); image count is event-based.
- Still uncaptured: Cloud Trace, Logging, Storage.

## 6. Secondary: derived cost (usage × catalog list price)

Provided for reference only. List price, not actual billed; **usage above is the primary output.**

| SKU | $/interaction |
|---|---|
| Gemini tokens | 0.0097 |
| Agent Runtime | 0.0029 |
| Memory Bank + Sessions | 0.0081 |
| Firestore (168w/145r over 118 runs) | 0.0000004 |
| Memory Bank retrieval (0.67 memories retrieved/intxn @ $0.5/1K) | 0.000335 |
| Model Armor (derived: 21591 tok scanned @ $0.10/1M) | 0.002159 |
| **Total (measured SKUs)** | **0.0232** (range 0.0132–0.0416) |

## 7. Test workload & sample interactions

**85 interactions** (426 total user turns), fresh user_id per interaction. Interactions cycle **10 distinct conversation scenarios** of varying length (2-turn×16, 3-turn×16, 4-turn×32, 5-turn×16, 15-turn×1, 24-turn×1, 32-turn×2, 35-turn×1) — real-world interactions differ in length and topic, so this spreads coverage rather than repeating one script.

**Scenario 1** (2 turns):

| Turn | User query |
|---|---|
| 1 | Process order ORD-1001 end to end and apply discount code SAVE10 with express shipping. |
| 2 | Now process order ORD-1003 — flag any issues before shipping. |

**Scenario 2** (3 turns):

| Turn | User query |
|---|---|
| 1 | Process order ORD-1002 with standard shipping. |
| 2 | Apply the WELCOME discount and recalculate shipping. |
| 3 | Send the customer an email confirmation and log it. |

**Scenario 3** (4 turns):

| Turn | User query |
|---|---|
| 1 | Check inventory for the items in order ORD-1001. |
| 2 | Validate the address and calculate express shipping. |
| 3 | Apply SAVE10 and update the status to confirmed. |
| 4 | Notify the customer by SMS and log the transaction. |

**Scenario 4** (4 turns):

| Turn | User query |
|---|---|
| 1 | Look up order ORD-1003 and tell me its current state. |
| 2 | The address issue is fixed — re-validate it. |
| 3 | Calculate standard shipping and apply WELCOME. |
| 4 | Confirm the order and notify by email. |

**Scenario 5** (5 turns):

| Turn | User query |
|---|---|
| 1 | Start processing order ORD-1001. |
| 2 | Check inventory and confirm availability. |
| 3 | Validate the shipping address. |
| 4 | Apply SAVE10 with express shipping and update status. |
| 5 | Notify the customer and write the audit log. |

**Scenario 6** (15 turns):

| Turn | User query |
|---|---|
| 1 | Process order ORD-1001 end to end and apply discount code SAVE10 with express shipping. |
| 2 | Now process order ORD-1003 — flag any issues before shipping. |
| 3 | Process order ORD-1001 end to end and apply discount code SAVE10 with express shipping. |
| 4 | Now process order ORD-1003 — flag any issues before shipping. |
| 5 | Process order ORD-1001 end to end and apply discount code SAVE10 with express shipping. |
| 6 | Process order ORD-1001 end to end and apply discount code SAVE10 with express shipping. |
| 7 | Now process order ORD-1003 — flag any issues before shipping. |
| 8 | Process order ORD-1001 end to end and apply discount code SAVE10 with express shipping. |
| 9 | Now process order ORD-1003 — flag any issues before shipping. |
| 10 | Process order ORD-1001 end to end and apply discount code SAVE10 with express shipping. |
| 11 | Now process order ORD-1003 — flag any issues before shipping. |
| 12 | Process order ORD-1001 end to end and apply discount code SAVE10 with express shipping. |
| 13 | Now process order ORD-1003 — flag any issues before shipping. |
| 14 | Process order ORD-1001 end to end and apply discount code SAVE10 with express shipping. |
| 15 | Now process order ORD-1003 — flag any issues before shipping. |

**Scenario 7** (24 turns):

| Turn | User query |
|---|---|
| 1 | Process order ORD-1002 with standard shipping. |
| 2 | Apply the WELCOME discount and recalculate shipping. |
| 3 | Send the customer an email confirmation and log it. |
| 4 | Process order ORD-1002 with standard shipping. |
| 5 | Apply the WELCOME discount and recalculate shipping. |
| 6 | Send the customer an email confirmation and log it. |
| 7 | Process order ORD-1002 with standard shipping. |
| 8 | Apply the WELCOME discount and recalculate shipping. |
| 9 | Send the customer an email confirmation and log it. |
| 10 | Process order ORD-1002 with standard shipping. |
| 11 | Apply the WELCOME discount and recalculate shipping. |
| 12 | Send the customer an email confirmation and log it. |
| 13 | Process order ORD-1002 with standard shipping. |
| 14 | Apply the WELCOME discount and recalculate shipping. |
| 15 | Send the customer an email confirmation and log it. |
| 16 | Process order ORD-1002 with standard shipping. |
| 17 | Apply the WELCOME discount and recalculate shipping. |
| 18 | Send the customer an email confirmation and log it. |
| 19 | Process order ORD-1002 with standard shipping. |
| 20 | Apply the WELCOME discount and recalculate shipping. |
| 21 | Send the customer an email confirmation and log it. |
| 22 | Process order ORD-1002 with standard shipping. |
| 23 | Apply the WELCOME discount and recalculate shipping. |
| 24 | Send the customer an email confirmation and log it. |

**Scenario 8** (32 turns):

| Turn | User query |
|---|---|
| 1 | Check inventory for the items in order ORD-1001. |
| 2 | Validate the address and calculate express shipping. |
| 3 | Apply SAVE10 and update the status to confirmed. |
| 4 | Notify the customer by SMS and log the transaction. |
| 5 | Check inventory for the items in order ORD-1001. |
| 6 | Validate the address and calculate express shipping. |
| 7 | Apply SAVE10 and update the status to confirmed. |
| 8 | Notify the customer by SMS and log the transaction. |
| 9 | Check inventory for the items in order ORD-1001. |
| 10 | Validate the address and calculate express shipping. |
| 11 | Apply SAVE10 and update the status to confirmed. |
| 12 | Notify the customer by SMS and log the transaction. |
| 13 | Check inventory for the items in order ORD-1001. |
| 14 | Validate the address and calculate express shipping. |
| 15 | Apply SAVE10 and update the status to confirmed. |
| 16 | Notify the customer by SMS and log the transaction. |
| 17 | Check inventory for the items in order ORD-1001. |
| 18 | Validate the address and calculate express shipping. |
| 19 | Apply SAVE10 and update the status to confirmed. |
| 20 | Notify the customer by SMS and log the transaction. |
| 21 | Check inventory for the items in order ORD-1001. |
| 22 | Validate the address and calculate express shipping. |
| 23 | Apply SAVE10 and update the status to confirmed. |
| 24 | Notify the customer by SMS and log the transaction. |
| 25 | Check inventory for the items in order ORD-1001. |
| 26 | Validate the address and calculate express shipping. |
| 27 | Apply SAVE10 and update the status to confirmed. |
| 28 | Notify the customer by SMS and log the transaction. |
| 29 | Check inventory for the items in order ORD-1001. |
| 30 | Validate the address and calculate express shipping. |
| 31 | Apply SAVE10 and update the status to confirmed. |
| 32 | Notify the customer by SMS and log the transaction. |

**Scenario 9** (32 turns):

| Turn | User query |
|---|---|
| 1 | Look up order ORD-1003 and tell me its current state. |
| 2 | The address issue is fixed — re-validate it. |
| 3 | Calculate standard shipping and apply WELCOME. |
| 4 | Confirm the order and notify by email. |
| 5 | Look up order ORD-1003 and tell me its current state. |
| 6 | The address issue is fixed — re-validate it. |
| 7 | Calculate standard shipping and apply WELCOME. |
| 8 | Confirm the order and notify by email. |
| 9 | Look up order ORD-1003 and tell me its current state. |
| 10 | The address issue is fixed — re-validate it. |
| 11 | Calculate standard shipping and apply WELCOME. |
| 12 | Confirm the order and notify by email. |
| 13 | Look up order ORD-1003 and tell me its current state. |
| 14 | The address issue is fixed — re-validate it. |
| 15 | Calculate standard shipping and apply WELCOME. |
| 16 | Confirm the order and notify by email. |
| 17 | Look up order ORD-1003 and tell me its current state. |
| 18 | The address issue is fixed — re-validate it. |
| 19 | Calculate standard shipping and apply WELCOME. |
| 20 | Confirm the order and notify by email. |
| 21 | Look up order ORD-1003 and tell me its current state. |
| 22 | The address issue is fixed — re-validate it. |
| 23 | Calculate standard shipping and apply WELCOME. |
| 24 | Confirm the order and notify by email. |
| 25 | Look up order ORD-1003 and tell me its current state. |
| 26 | The address issue is fixed — re-validate it. |
| 27 | Calculate standard shipping and apply WELCOME. |
| 28 | Confirm the order and notify by email. |
| 29 | Look up order ORD-1003 and tell me its current state. |
| 30 | The address issue is fixed — re-validate it. |
| 31 | Calculate standard shipping and apply WELCOME. |
| 32 | Confirm the order and notify by email. |

**Scenario 10** (35 turns):

| Turn | User query |
|---|---|
| 1 | Start processing order ORD-1001. |
| 2 | Check inventory and confirm availability. |
| 3 | Validate the shipping address. |
| 4 | Apply SAVE10 with express shipping and update status. |
| 5 | Notify the customer and write the audit log. |
| 6 | Start processing order ORD-1001. |
| 7 | Check inventory and confirm availability. |
| 8 | Validate the shipping address. |
| 9 | Apply SAVE10 with express shipping and update status. |
| 10 | Notify the customer and write the audit log. |
| 11 | Start processing order ORD-1001. |
| 12 | Check inventory and confirm availability. |
| 13 | Validate the shipping address. |
| 14 | Apply SAVE10 with express shipping and update status. |
| 15 | Notify the customer and write the audit log. |
| 16 | Start processing order ORD-1001. |
| 17 | Check inventory and confirm availability. |
| 18 | Validate the shipping address. |
| 19 | Apply SAVE10 with express shipping and update status. |
| 20 | Notify the customer and write the audit log. |
| 21 | Start processing order ORD-1001. |
| 22 | Check inventory and confirm availability. |
| 23 | Validate the shipping address. |
| 24 | Apply SAVE10 with express shipping and update status. |
| 25 | Notify the customer and write the audit log. |
| 26 | Start processing order ORD-1001. |
| 27 | Check inventory and confirm availability. |
| 28 | Validate the shipping address. |
| 29 | Apply SAVE10 with express shipping and update status. |
| 30 | Notify the customer and write the audit log. |
| 31 | Start processing order ORD-1001. |
| 32 | Check inventory and confirm availability. |
| 33 | Validate the shipping address. |
| 34 | Apply SAVE10 with express shipping and update status. |
| 35 | Notify the customer and write the audit log. |

**Sample interaction (first run):**

- **Turn 1** (10221 in / 849 out tokens) — user: *Process order ORD-1001 end to end and apply discount code SAVE10 with express shipping.*
  - reply preview: Order ORD-1001 processed successfully. - Item: wireless mouse, Quantity: 2 - Inventory: In stock - Address: Valid - Shipping: Express shipping, Cost: $16, ETA: 2 days - Discount: SAVE10 applied (10% o…
- **Turn 2** (10865 in / 593 out tokens) — user: *Now process order ORD-1003 — flag any issues before shipping.*
  - reply preview: Order ORD-1003 cannot be processed at this time due to an issue with the shipping address. Address validation failed because of a "missing ZIP code". Please correct the address before attempting to pr…

Full transcripts: `data/transcript_workflow_operator.jsonl` (one JSON record per turn; full input, output_text, every tool call+response, per-step usage). **Not committed** (data/ is gitignored — runtime artifact).