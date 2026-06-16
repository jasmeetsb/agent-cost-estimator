# SKU Usage Summary — `workflow-operator (archetype)` (workflow_operator)

- **Source:** google/adk-samples · **Model:** gemini-2.5-flash · **Engine:** `1344577926200295424`
- **Use case:** Order-fulfillment workflow operator · **Complexity:** Archetype: Workflow Operator / Moderate
- **Unit:** 1 interaction = 2-turn conversation + memory-write (15.3 model calls avg). Deployed on Vertex AI Agent Engine (GEAP).
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

Deployed to Agent Engine; per run = 2-turn conversation in one session + add_session_to_memory; **80 runs** for variability; 300s Monitoring settle; token usage from the model response (`usage_metadata`, exact), runtime + Memory Bank usage from Cloud Monitoring (per-engine).
Reproduce: `python scripts/exp_sample.py --package workflow_operator --runs 80 --settle 300`

## 4. SKU usage per interaction (PRIMARY)

Measured usage quantities per interaction (avg over 80 runs), with run-to-run range and variability.

| SKU dimension | Unit | Typical | Range | Variability |
|---|---|---|---|---|
| Gemini input tokens | tokens | 21146 | 3343–74345 | High |
| Gemini output tokens (incl. thinking) | tokens | 1528 | 583–3502 | Medium |
| Model calls | calls | 15.3 | — | Medium |
| Agent Runtime — vCPU | vCPU-seconds | 52.8 | — | — |
| Agent Runtime — memory | GiB-seconds | 84.0 | — | — |
| Sessions | events appended | 30.6 | — | Medium |
| Memory Bank — generation | tokens | 0 | — | — |
| Memory Bank — memories written | memories | 0.0 | — | — |
| Memory Bank — retrievals | reads | 0.0 | — | — |
| Firestore — document writes | writes | 1.50 | — | — |
| Firestore — document reads | reads | 1.00 | — | — |

_Memory retrievals = 0: this agent has no preload_memory tool — it writes memories from the session but doesn't read them back._

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
| Gemini tokens | 0.0102 |
| Agent Runtime | 0.0033 |
| Memory Bank + Sessions | 0.0077 |
| Firestore (120w/80r over 80 runs) | 0.0000004 |
| Model Armor (derived: 22675 tok scanned @ $0.10/1M) | 0.002267 |
| **Total (measured SKUs)** | **0.0234** (range 0.0141–0.0415) |

## 7. Test workload & sample interactions

**80 interactions** (288 total user turns), fresh user_id per interaction. Interactions cycle **5 distinct conversation scenarios** of varying length (2-turn×16, 3-turn×16, 4-turn×32, 5-turn×16) — real-world interactions differ in length and topic, so this spreads coverage rather than repeating one script.

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

**Sample interaction (first run):**

- **Turn 1** (10221 in / 849 out tokens) — user: *Process order ORD-1001 end to end and apply discount code SAVE10 with express shipping.*
  - reply preview: Order ORD-1001 processed successfully. - Item: wireless mouse, Quantity: 2 - Inventory: In stock - Address: Valid - Shipping: Express shipping, Cost: $16, ETA: 2 days - Discount: SAVE10 applied (10% o…
- **Turn 2** (10865 in / 593 out tokens) — user: *Now process order ORD-1003 — flag any issues before shipping.*
  - reply preview: Order ORD-1003 cannot be processed at this time due to an issue with the shipping address. Address validation failed because of a "missing ZIP code". Please correct the address before attempting to pr…

Full transcripts: `data/transcript_workflow_operator.jsonl` (one JSON record per turn; full input, output_text, every tool call+response, per-step usage). **Not committed** (data/ is gitignored — runtime artifact).