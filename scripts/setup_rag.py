"""Create a shared Vertex AI Search datastore + ingest a synthetic enterprise corpus.

One shared datastore (`agent-knowledge`) holds ~24 synthetic documents spanning
the domains the RAG-using archetypes need: product/support KB (chatbot), ops &
analytics playbooks (orchestrator), and reference briefs (researcher). "Shared
where it makes sense" per the agreed plan.

Run once: python scripts/setup_rag.py
"""

import time

from google.api_core.client_options import ClientOptions
from google.cloud import discoveryengine_v1 as de

PROJECT = "jsb-genai-sa"
LOCATION = "global"
DATA_STORE_ID = "agent-knowledge"            # full/internal — researcher + orchestrator
PUBLIC_DATA_STORE_ID = "agent-knowledge-public"  # customer-safe — chatbot only
# Customer-safe docs (support KB + product). Internal docs (ops-/res-/policy-)
# are EXCLUDED from the chatbot's datastore to avoid cross-trust-boundary exposure.
PUBLIC_PREFIXES = ("kb-", "prod-")
_CO = ClientOptions(api_endpoint=f"{LOCATION}-discoveryengine.googleapis.com"
                    if LOCATION != "global" else "discoveryengine.googleapis.com")

# Synthetic corpus: (id, title, text). Spans support / product / ops / research.
CORPUS = [
    ("kb-pw-reset", "Password reset", "To reset your password go to Settings > Security > Reset Password. A reset link is emailed and expires in 30 minutes. Enterprise SSO users reset via their IdP."),
    ("kb-refunds", "Refund policy", "Refunds are processed within 5-7 business days to the original payment method. Digital goods are refundable within 14 days if unused. Contact support to initiate."),
    ("kb-shipping", "Shipping options", "Standard shipping is 3-5 business days; express is 1-2 business days. Free standard shipping on orders over $50. International shipping varies by region."),
    ("kb-cancel", "Cancellation", "Subscriptions can be cancelled anytime from Account > Subscriptions > Cancel. Access continues until the end of the billing period; no partial refunds."),
    ("kb-sso", "SSO and SAML", "Single sign-on (SAML 2.0 and OIDC) is available on the Enterprise tier. Configure via Admin > Security > SSO. Supports Okta, Azure AD, and Google Workspace."),
    ("kb-export", "Data export", "Export your data as CSV or JSON from Account > Data > Export. Large exports are emailed as a download link. API export is available on Pro and Enterprise."),
    ("kb-pricing", "Pricing tiers", "Starter is free (1 user, community support). Pro is $29/user/month (SSO-no, API-yes). Enterprise is custom (SSO, SLA, dedicated support)."),
    ("kb-integrations", "Integrations", "We support REST APIs, webhooks, Slack, and Zapier. Native connectors for Salesforce and HubSpot are on Enterprise. See docs.example.com/integrations."),
    ("prod-overview", "Product overview", "The platform provides workflow automation, analytics dashboards, and an agent API. Core objects are Projects, Workflows, and Reports."),
    ("prod-api-limits", "API rate limits", "API limits: Starter 60 req/min, Pro 600 req/min, Enterprise 6000 req/min. Exceeding limits returns HTTP 429. Use exponential backoff."),
    ("prod-roles", "Roles and permissions", "Roles: Viewer (read), Editor (read/write), Admin (manage users + billing). Custom roles available on Enterprise via IAM-style policies."),
    ("ops-incident", "Incident response playbook", "On a Sev-1: page on-call, open an incident channel, post status every 30 min, assign an incident commander, and write a postmortem within 48 hours."),
    ("ops-churn", "Churn analysis playbook", "Churn drivers ranked: onboarding friction, missing integrations, price sensitivity. Cross-reference cancellation reasons with support-ticket themes and usage decline."),
    ("ops-ticket-triage", "Support ticket triage", "Triage by severity and topic. Route billing to Finance, outages to SRE, how-to to Tier-1. Target first response: Sev-1 15 min, Sev-2 2 h, Sev-3 1 day."),
    ("ops-roster", "Staffing & roster guidance", "Maintain >=2 agents per shift, <=3 consecutive shifts per person, and honor time-off requests. Use historical volume to forecast staffing by hour."),
    ("ops-metrics", "Key business metrics", "Track MRR, net revenue retention, activation rate, weekly active accounts, and ticket volume per 100 accounts. Review trends weekly."),
    ("res-smr", "Brief: small modular reactors", "SMRs are <300 MWe fission reactors built factory-fabricated for on-site assembly. Promise: lower upfront cost, scalability. Barriers: licensing, first-of-a-kind costs, fuel supply."),
    ("res-ssb", "Brief: solid-state batteries", "Solid-state batteries replace liquid electrolyte with a solid, enabling higher energy density and safety. Hurdles: dendrite formation, manufacturing scale, cost."),
    ("res-dac", "Brief: direct air capture", "Direct air capture chemically removes CO2 from ambient air. Costs are high ($300-600/ton) vs point-source. Scalability depends on cheap clean energy and storage."),
    ("res-transformers", "Brief: efficient transformers", "Efficiency research spans sparse attention, mixture-of-experts, quantization, and distillation. Edge deployment favors quantization + small-model distillation."),
    ("res-rag", "Brief: retrieval-augmented generation", "RAG grounds LLM outputs in retrieved documents, reducing hallucination. Vector search over embeddings is the common retrieval substrate; hybrid (keyword+vector) improves recall."),
    ("res-vectordb", "Brief: vector databases", "Vector databases index embeddings for similarity search (ANN). Used in RAG, recommendations, dedup. Trade-offs: recall vs latency, index build cost, memory."),
    ("policy-security", "Security policy", "All data encrypted in transit (TLS 1.2+) and at rest. Least-privilege IAM. Secrets in a managed vault. Quarterly access reviews. SOC 2 Type II certified."),
    ("policy-data", "Data handling policy", "PII is classified and access-logged. Data residency available on Enterprise. Retention default 13 months; configurable. Deletion requests honored within 30 days."),
]


def _ensure_datastore(ds_client, parent, ds_id, display):
    path = f"{parent}/dataStores/{ds_id}"
    try:
        ds_client.get_data_store(name=path)
        print("datastore exists:", ds_id)
    except Exception:
        op = ds_client.create_data_store(
            parent=parent, data_store_id=ds_id,
            data_store=de.DataStore(
                display_name=display,
                industry_vertical=de.IndustryVertical.GENERIC,
                solution_types=[de.SolutionType.SOLUTION_TYPE_SEARCH],
                content_config=de.DataStore.ContentConfig.CONTENT_REQUIRED,
            ),
        )
        print("creating datastore:", ds_id)
        op.result(timeout=300)
        time.sleep(10)
    return path


def _import(doc_client, ds_path, corpus_subset):
    branch = f"{ds_path}/branches/default_branch"
    docs = [de.Document(id=did, content=de.Document.Content(
                mime_type="text/plain", raw_bytes=text.encode("utf-8")))
            for did, _, text in corpus_subset]
    op = doc_client.import_documents(request=de.ImportDocumentsRequest(
        parent=branch,
        inline_source=de.ImportDocumentsRequest.InlineSource(documents=docs),
        reconciliation_mode=de.ImportDocumentsRequest.ReconciliationMode.INCREMENTAL,
    ))
    print(f"importing {len(docs)} docs into {ds_path.split('/')[-1]}...")
    op.result(timeout=600)


def main():
    ds_client = de.DataStoreServiceClient(client_options=_CO)
    doc_client = de.DocumentServiceClient(client_options=_CO)
    parent = f"projects/{PROJECT}/locations/{LOCATION}/collections/default_collection"

    public = [d for d in CORPUS if d[0].startswith(PUBLIC_PREFIXES)]

    # Full/internal datastore — researcher + orchestrator (all docs).
    full_path = _ensure_datastore(ds_client, parent, DATA_STORE_ID, "Agent Knowledge (synthetic, internal)")
    _import(doc_client, full_path, CORPUS)

    # Customer-safe datastore — chatbot only (KB + product docs; NO internal ops/policy/research).
    pub_path = _ensure_datastore(ds_client, parent, PUBLIC_DATA_STORE_ID, "Agent Knowledge (synthetic, customer-safe)")
    _import(doc_client, pub_path, public)

    print(f"done. full={DATA_STORE_ID} ({len(CORPUS)} docs), "
          f"public={PUBLIC_DATA_STORE_ID} ({len(public)} docs)")


if __name__ == "__main__":
    main()
