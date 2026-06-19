"""Create a shared Vertex AI Search datastore + ingest a synthetic enterprise corpus.

One shared datastore (`agent-knowledge`) holds ~24 synthetic documents spanning
the domains the RAG-using archetypes need: product/support KB (chatbot), ops &
analytics playbooks (orchestrator), and reference briefs (researcher). "Shared
where it makes sense" per the agreed plan.

Run once: python scripts/setup_rag.py
"""

import json
import time

from google.api_core.client_options import ClientOptions
from google.cloud import discoveryengine_v1 as de
from google.cloud import storage

PROJECT = "jsb-genai-sa"
LOCATION = "global"
STAGING_BUCKET = "jsb-genai-sa-staging"      # holds the .txt corpus + import manifest
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
    # ---- finance domain (financial_advisor RAG) ----
    ("fin-valuation", "Equity valuation methods", "Common valuation approaches: discounted cash flow (DCF) on free cash flow, comparable-company multiples (P/E, EV/EBITDA, P/S), and dividend discount models. DCF is sensitive to the discount rate and terminal growth assumptions."),
    ("fin-risk", "Portfolio risk concepts", "Key risk measures: beta (market sensitivity), volatility (standard deviation of returns), Sharpe ratio (excess return per unit risk), max drawdown, and value-at-risk (VaR). Diversification reduces idiosyncratic risk, not market risk."),
    ("fin-strategies", "Trading strategy archetypes", "Strategy families: momentum (trend-following), mean-reversion, value, and dollar-cost averaging. Position sizing and stop-losses manage downside. Backtesting must account for transaction costs and survivorship bias."),
    ("fin-execution", "Order execution and costs", "Execution venues and order types (market, limit, VWAP/TWAP algos) affect slippage. Implementation shortfall measures the gap between decision price and realized price. Spreads widen in low-liquidity names."),
    ("fin-macro", "Macro indicators for investors", "Watch the Fed funds rate, CPI/PCE inflation, yield-curve shape (inversion signals recession risk), unemployment, and earnings revisions. Rate cuts tend to support equity multiples; rate hikes compress them."),
    ("fin-semis", "Sector brief: semiconductors", "Semiconductor demand is driven by AI accelerators, data-center capex, and inventory cycles. Risks: cyclicality, customer concentration, export controls, and capital intensity of fabs. Leaders compete on process-node leadership and packaging."),
    # ---- marketing / branding domain (marketing_agency RAG) ----
    ("mkt-brand", "Brand strategy basics", "A brand strategy defines positioning, target audience, value proposition, voice/tone, and visual identity. Consistency across touchpoints builds recognition. A positioning statement names the audience, category, benefit, and reason-to-believe."),
    ("mkt-naming", "Naming and domains", "Good product names are short, pronounceable, distinctive, and trademark-clearable. Check domain availability (.com first) and social handles. Avoid names that limit future expansion or carry negative connotations in key markets."),
    ("mkt-channels", "Marketing channels & funnel", "Channels map to the funnel: awareness (social, content, PR), consideration (email, retargeting, webinars), conversion (landing pages, promos), retention (lifecycle email, loyalty). Track CAC, LTV, and channel ROAS."),
    ("mkt-landing", "Landing page best practices", "A high-converting hero section has one clear value proposition, a single primary CTA, social proof, and minimal friction. Above-the-fold clarity and fast load times drive conversion; test headlines and CTAs with A/B experiments."),
    ("mkt-content", "Content & SEO guidance", "Content marketing targets search intent with pillar pages + clusters. Optimize titles, meta descriptions, and internal links. Repurpose long-form into social snippets. Measure organic traffic, dwell time, and assisted conversions."),
    ("mkt-social", "Social campaign guidance", "Match format to platform (short video, carousels, threads). A campaign needs a hook, a consistent visual system, a hashtag, and a clear CTA. Post timing and frequency depend on audience; measure engagement rate and shares, not just reach."),
    # ---- FOMC / monetary-policy domain (fomc_research RAG) ----
    ("fomc-mandate", "FOMC dual mandate", "The Federal Open Market Committee sets US monetary policy toward a dual mandate: maximum employment and price stability (2% PCE inflation target). It meets eight times a year and issues a post-meeting statement plus a Summary of Economic Projections (SEP) quarterly."),
    ("fomc-tools", "Monetary policy tools", "Primary tool is the federal funds target range. Supporting tools: interest on reserve balances (IORB), the overnight reverse repo (ON RRP) facility, and the balance sheet (QE/QT). Forward guidance shapes expectations about the future path of rates."),
    ("fomc-dots", "SEP and the dot plot", "The SEP includes the 'dot plot' — each participant's projection for the appropriate fed funds rate at year-ends and longer run. The median dot is watched as a signal of the expected rate path, though it is not a committee commitment."),
    ("fomc-inflation", "Reading inflation data", "The FOMC watches PCE and core PCE (ex food and energy) most closely, plus CPI, wage growth, and inflation expectations (TIPS breakevens, surveys). Sticky services inflation and shelter lag goods disinflation. Above-target prints argue for tighter policy."),
    ("fomc-curve", "Yield curve and policy", "The yield curve reflects rate expectations plus term premium. An inverted 2s10s curve has historically preceded recessions. Cuts steepen the curve via the front end; QT can raise long-end yields. The neutral rate (r*) anchors the longer-run dot."),
    ("fomc-statement", "Parsing the statement", "Compare the new statement to the prior one word-for-word: changes to the characterization of growth, employment, and inflation, the policy-rate sentence, and the balance-sheet language. The vote tally and any dissents signal committee conviction."),
    # ---- data-engineering domain (plumber_agent RAG) ----
    ("de-dataflow", "Dataflow / Apache Beam", "Dataflow runs Apache Beam pipelines (batch + streaming) with autoscaling and dynamic work rebalancing. Use windowing + triggers for streaming aggregations. Prefer the Beam SQL / DataFrame APIs for transforms; sink to BigQuery via the Storage Write API."),
    ("de-bigquery", "BigQuery for analytics", "BigQuery is serverless columnar storage + compute. Partition by date and cluster by high-cardinality filter columns to cut scanned bytes (cost). Use materialized views for repeated aggregations; avoid SELECT *. Load via batch load jobs or streaming inserts."),
    ("de-dbt", "dbt transformations", "dbt models are SELECT statements compiled to tables/views with ref() lineage. Use staging → intermediate → marts layering, tests (unique, not_null, relationships), and incremental models for large fact tables. Document models and expose lineage."),
    ("de-dataproc", "Dataproc / Spark", "Dataproc runs managed Spark/Hadoop. Use ephemeral job-scoped clusters or serverless Spark to control cost. Tune executor memory + shuffle partitions; persist to GCS/BigQuery in columnar formats (Parquet). Prefer serverless for bursty batch jobs."),
    ("de-orchestration", "Pipeline orchestration", "Orchestrate with Cloud Composer (Airflow) or Workflows: define DAGs with idempotent tasks, retries with backoff, and SLAs. Separate ingestion, transformation, and publish stages. Backfills should be parameterized by date and safe to re-run."),
    ("de-quality", "Data quality & observability", "Validate schema, freshness, volume, and distribution. Emit metrics to Cloud Monitoring and set alerts on freshness/row-count anomalies. Quarantine bad rows rather than failing the whole batch. Track lineage for impact analysis on upstream changes."),
    # ---- brand-guideline domain (on_brand_genmedia RAG) ----
    ("brand-palette", "Brand color palette", "The primary palette is deep teal (#0B5563) and warm sand (#E9DCC9), with charcoal (#222) for text and a coral (#FF6B5C) accent for CTAs only. Maintain WCAG AA contrast. Do not introduce off-palette colors in generated imagery."),
    ("brand-logo", "Logo usage rules", "Keep clear space around the logo equal to the height of the mark. Never stretch, recolor, add shadows, or place the logo on busy backgrounds. Use the monochrome version on photography. Minimum size 24px digital."),
    ("brand-typography", "Typography system", "Headlines use a geometric sans (e.g., 'Poppins' SemiBold); body uses a humanist sans ('Inter' Regular). Sentence case for headings, never ALL CAPS for long strings. Generous line height (1.5) for body."),
    ("brand-imagery", "Imagery & art direction", "Photography is bright, natural-light, candid, with people in real environments. Avoid stocky/staged shots, heavy filters, and clutter. Generated images should feel warm and optimistic, leave negative space for text, and stay on the brand palette."),
    ("brand-voice", "Brand voice & tone", "Voice is friendly, clear, and confident — never jargon-heavy or pushy. Speak to the customer's goal, not features. Short sentences. Optimistic but honest. Avoid hype words ('revolutionary', 'game-changing')."),
    ("brand-social", "Social asset specs", "Instagram hero 1080x1350 (4:5); story 1080x1920 (9:16); banner 1080x566. Keep the logo in a corner with clear space, key message in the top third, CTA bottom. On-palette backgrounds; legible at thumbnail size."),
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


def _import(doc_client, bucket, ds_path, corpus_subset):
    """Ingest unstructured docs via GCS + a JSONL manifest (data_schema="document").

    Inline raw_bytes import is rejected by these GENERIC/CONTENT_REQUIRED datastores
    ("document.data is a required field"). The reliable path for unstructured text is:
    upload each doc as a .txt to GCS, then import a JSONL manifest whose lines carry
    each doc's id + content.uri. Title is carried in struct_data for richer ranking.
    """
    ds_id = ds_path.split("/")[-1]
    prefix = f"rag_corpus/{ds_id}"
    manifest_lines = []
    for did, title, text in corpus_subset:
        blob_name = f"{prefix}/{did}.txt"
        bucket.blob(blob_name).upload_from_string(text, content_type="text/plain")
        gcs_uri = f"gs://{STAGING_BUCKET}/{blob_name}"
        manifest_lines.append(json.dumps({
            "id": did,
            "structData": {"title": title},
            "content": {"mimeType": "text/plain", "uri": gcs_uri},
        }))
    manifest_name = f"{prefix}/_import.jsonl"
    bucket.blob(manifest_name).upload_from_string(
        "\n".join(manifest_lines), content_type="application/jsonl")
    manifest_uri = f"gs://{STAGING_BUCKET}/{manifest_name}"

    branch = f"{ds_path}/branches/default_branch"
    op = doc_client.import_documents(request=de.ImportDocumentsRequest(
        parent=branch,
        gcs_source=de.GcsSource(input_uris=[manifest_uri], data_schema="document"),
        reconciliation_mode=de.ImportDocumentsRequest.ReconciliationMode.INCREMENTAL,
    ))
    print(f"importing {len(corpus_subset)} docs into {ds_id} (manifest={manifest_uri})...")
    resp = op.result(timeout=600)
    meta = op.metadata
    errs = list(resp.error_samples)
    print(f"  success={getattr(meta, 'success_count', '?')} "
          f"failure={getattr(meta, 'failure_count', '?')}")
    for e in errs[:5]:
        print("  ERROR:", e.message)
    if errs:
        raise RuntimeError(f"{ds_id}: import reported {len(errs)} error sample(s)")


def _verify(doc_client, search_client, ds_path, sample_query, expected):
    """List documents and run a sample search so the script self-verifies ingestion."""
    ds_id = ds_path.split("/")[-1]
    branch = f"{ds_path}/branches/default_branch"
    docs = list(doc_client.list_documents(
        request=de.ListDocumentsRequest(parent=branch, page_size=100)))
    serving = f"{ds_path}/servingConfigs/default_search"
    try:
        resp = search_client.search(de.SearchRequest(
            serving_config=serving, query=sample_query, page_size=3))
        hits = [h.document.id for h in resp.results]
    except Exception as e:  # serving config may take a moment to become queryable
        hits = f"search-pending ({type(e).__name__})"
    status = "OK" if len(docs) == expected else "MISMATCH"
    print(f"  verify[{ds_id}]: {len(docs)}/{expected} docs ({status}); "
          f"sample q='{sample_query}' -> {hits}")
    return len(docs)


def main():
    ds_client = de.DataStoreServiceClient(client_options=_CO)
    doc_client = de.DocumentServiceClient(client_options=_CO)
    search_client = de.SearchServiceClient(client_options=_CO)
    bucket = storage.Client(project=PROJECT).bucket(STAGING_BUCKET)
    parent = f"projects/{PROJECT}/locations/{LOCATION}/collections/default_collection"

    public = [d for d in CORPUS if d[0].startswith(PUBLIC_PREFIXES)]

    # Full/internal datastore — researcher + orchestrator (all docs).
    full_path = _ensure_datastore(ds_client, parent, DATA_STORE_ID, "Agent Knowledge (synthetic, internal)")
    _import(doc_client, bucket, full_path, CORPUS)

    # Customer-safe datastore — chatbot only (KB + product docs; NO internal ops/policy/research).
    pub_path = _ensure_datastore(ds_client, parent, PUBLIC_DATA_STORE_ID, "Agent Knowledge (synthetic, customer-safe)")
    _import(doc_client, bucket, pub_path, public)

    print(f"imported. full={DATA_STORE_ID} ({len(CORPUS)} docs), "
          f"public={PUBLIC_DATA_STORE_ID} ({len(public)} docs)")
    print("verifying (indexing may lag a few minutes before search returns hits):")
    _verify(doc_client, search_client, full_path, "churn analysis playbook", len(CORPUS))
    _verify(doc_client, search_client, pub_path, "how do I reset my password", len(public))


if __name__ == "__main__":
    main()
