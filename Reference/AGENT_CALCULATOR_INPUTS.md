# GE Agent Platform — Calculator Inputs (per Agent Type)

Source: `Reference/[GE Agent Platform] Calculator inputs.xlsx` → **Inputs** tab. Agent types are columns; Product SKUs (grouped by lifecycle Phase) and their individual data-point fields are rows. Blank cell = field not applicable / not set for that agent type.

**Field category legend:** *Use Case Input* = top-level scenario assumption · *Modifiable Input* = user-tunable · *Calculated Input* = derived by the calculator · *N/A* = no SKU input.

## A. Agent Archetypes (4 archetypes × 3 complexity levels)

| Phase | Product / SKU | Data Field | Category | Conversational Chatbot<br/>(Low Complexity) | Conversational Chatbot<br/>(Moderate Complexity) | Conversational Chatbot<br/>(High Complexity) | Workflow Operator<br/>(Low Complexity) | Workflow Operator<br/>(Moderate Complexity) | Workflow Operator<br/>(High Complexity) | Autonomous Researcher<br/>(Low Complexity) | Autonomous Researcher<br/>(Moderate Complexity) | Autonomous Researcher<br/>(High Complexity) | Multi-Agent Orchestrator<br/>(Low Complexity) | Multi-Agent Orchestrator<br/>(Moderate Complexity) | Multi-Agent Orchestrator<br/>(High Complexity) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Use Case | Use Case | # of Users | Use Case Input |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | # of Queries / User / Month | Modifiable Input | 100 | 100 | 100 | 100 | 100 | 100 | 20 | 20 | 20 | 40 | 40 | 40 |
|  |  | # of Turns / Query | Modifiable Input | 2 | 3 | 4 | 3 | 4 | 5 | 2 | 3 | 4 | 5 | 7 | 10 |
|  |  | % of Query Turns with Tools & API Calls | Modifiable Input |  | 0.2 | 0.2 | 0.4 | 0.4 | 0.4 | 0.4 | 0.4 | 0.4 | 0.5 | 0.6 | 0.7 |
|  |  | # of Tools & API Calls / Query Turn | Modifiable Input |  | 3 | 3 | 8 | 8 | 8 | 8 | 8 | 8 | 25 | 35 | 45 |
|  |  | % of Query Turns with Agent Calls | Modifiable Input |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | # of Agent Calls / Query Turn | Modifiable Input |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | # of Initial Prompt Input Tokens | Modifiable Input | 300 | 300 | 300 | 500 | 500 | 500 | 2000 | 2000 | 2000 | 300 | 300 | 300 |
|  |  | # of Follow-Up Input Tokens | Modifiable Input | 150 | 150 | 150 | 250 | 250 | 250 | 500 | 500 | 500 | 150 | 150 | 150 |
|  |  | # of Average Output Tokens | Modifiable Input | 400 | 400 | 400 | 750 | 750 | 750 | 5000 | 5000 | 5000 | 400 | 400 | 400 |
| Build | Google Gemini for User Query | # of Monthly Input Tokens | Calculated Input |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | # of Monthly Output Tokens | Calculated Input |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | Gemini Model | Modifiable Input | Gemini 3.1 Flash-Lite | Gemini 3.1 Flash-Lite | Gemini 3.1 Flash-Lite | Gemini 3.0 Flash | Gemini 3.0 Flash | Gemini 3.0 Flash | Gemini 3.1 Pro (<= 200k) | Gemini 3.1 Pro (<= 200k) | Gemini 3.1 Pro (<= 200k) | Gemini 3.0 Flash | Gemini 3.0 Flash | Gemini 3.0 Flash |
|  | Google Gemini for Tools & API Calls | # of Tools & API Calls / Month | Calculated Input |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | Gemini Model | Modifiable Input |  | Gemini 3.1 Flash-Lite | Gemini 3.1 Flash-Lite | Gemini 3.1 Flash-Lite | Gemini 3.1 Flash-Lite | Gemini 3.1 Flash-Lite | Gemini 3.1 Flash-Lite | Gemini 3.1 Flash-Lite | Gemini 3.1 Flash-Lite | Gemini 3.1 Flash-Lite | Gemini 3.1 Flash-Lite | Gemini 3.1 Flash-Lite |
|  |  | # of Input Tokens / Tool & API Call | Modifiable Input |  | 200 | 200 | 250 | 250 | 250 | 250 | 250 | 250 | 300 | 300 | 300 |
|  |  | # of Output Tokens / Tool & API Call | Modifiable Input |  | 300 | 300 | 350 | 350 | 350 | 350 | 350 | 350 | 400 | 400 | 400 |
|  | Google Gemini for Agent Calls | # of Agent Calls / Month | Calculated Input |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | Gemini Model | Modifiable Input |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | # of Input Tokens / Agent Call | Modifiable Input |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | # of Output Tokens / Agent Call | Modifiable Input |  |  |  |  |  |  |  |  |  |  |  |  |
|  | Apigee for Tools & API Calls | # of Tool, API, Agent Calls / Month | Calculated Input |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | % of Tools, API, Agent Calls that Require Apigee | Modifiable Input |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | # of Environments | Modifiable Input |  | 1 | 1 | 2 | 2 | 2 | 1 | 2 | 3 | 1 | 2 | 3 |
|  |  | Environment Type | Modifiable Input |  | Intermediate | Intermediate | Intermediate | Intermediate | Intermediate | Intermediate | Intermediate | Intermediate | Comprehensive | Comprehensive | Comprehensive |
|  | BigQuery API Calls | # of Query Turns / Month | Calculated Input |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | % of Query Turns with API Calls | Modifiable Input |  | 0.3 | 0.3 | 0.6 | 0.6 | 0.6 | 0.6 | 0.6 | 0.6 | 0.75 | 0.9 | 1 |
|  |  | # of BigQuery API Calls / Query Turn | Modifiable Input |  | 1 | 1 | 2 | 2 | 2 | 2 | 2 | 2 | 4 | 6 | 8 |
|  |  | # GB of Data / API Call | Modifiable Input |  | 0.15 | 0.15 | 0.2 | 0.2 | 0.2 | 0.2 | 0.2 | 0.2 | 0.2 | 0.2 | 0.2 |
|  | Imagen for Image Generation | # of Query Turns / Month | Calculated Input |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | Imagen Model | Modifiable Input |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | % of Turns Needing Image Generation | Modifiable Input |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | # of Images Generated per Turn | Modifiable Input |  |  |  |  |  |  |  |  |  |  |  |  |
|  | Veo for Video Generation | # of Query Turns / Month | Calculated Input |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | Veo Model | Modifiable Input |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | Video Output Type | Modifiable Input |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | Video Resolution | Modifiable Input |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | % of Turns Needing Video Generationn | Modifiable Input |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | # Seconds of Video Generated per Turn | Modifiable Input |  |  |  |  |  |  |  |  |  |  |  |  |
|  | Agent Search for RAG | # of Query Turns / Month | Calculated Input |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | % of Query Turns that Require Search | Modifiable Input | 0.1 | 0.1 | 0.1 | 0.25 | 0.25 | 0.25 | 0.25 | 0.25 | 0.25 | 0.3 | 0.4 | 0.5 |
|  |  | # GBs of Data Indexed | Modifiable Input | 100 | 100 | 100 | 250 | 250 | 250 | 250 | 250 | 250 | 300 | 300 | 300 |
|  | Grounding with Google Search | # of Query Turns / Month | Calculated Input |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | % of Query Turns that Require Google Search Grounding | Modifiable Input |  | 0.05 | 0.05 |  | 0.1 | 0.1 | 0.1 | 0.1 | 0.1 | 0.05 | 0.1 | 0.15 |
|  | Grounding with Google Maps | # of Query Turns / Month | Calculated Input |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | % of Query Turns that Require Google Maps Grounding | Modifiable Input |  |  |  |  |  |  |  |  | 0.01 |  | 0.01 | 0.02 |
| Scale | Agent Runtime | # of Query Turns / Month | Calculated Input |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | # Seconds / Query Turn | Modifiable Input | 3 | 7 | 10 | 7 | 10 | 12 | 10 | 10 | 10 | 15 | 20 | 25 |
|  |  | # of vCPU | Modifiable Input | 1 | 2 | 2 | 2 | 3 | 4 | 2 | 2 | 2 | 3 | 4 | 5 |
|  |  | # of RAM | Modifiable Input | 1 | 1 | 2 | 2 | 3 | 3 | 2 | 2 | 2 | 3 | 4 | 5 |
|  | Agent Sessions | # of Query Turns / Month | Calculated Input |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | # of Events / Query Turn | Modifiable Input | 1 | 2 | 3 | 3 | 4 | 5 | 3 | 3 | 3 | 4 | 5 | 6 |
|  | Agent Sandbox: Code Execution | # of Runtime Hours / Month | Calculated Input |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | % of Usage for Code Execution | Modifiable Input |  |  | 0.3 |  | 0.3 | 0.3 |  | 0.3 | 0.3 |  | 0.3 | 0.3 |
|  |  | # of vCPU | Modifiable Input |  |  | 2 |  | 1 | 2 |  | 2 | 3 |  | 3 | 4 |
|  |  | # of RAM | Modifiable Input |  |  | 2 |  | 1 | 2 |  | 2 | 3 |  | 3 | 4 |
|  | Agent Sandbox: Computer Use | # of Runtime Hours / Month | Calculated Input |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | % of Usage for Computer Use | Modifiable Input |  | 0.3 | 0.3 |  | 0.3 | 0.3 |  | 0.3 | 0.3 |  | 0.3 | 0.3 |
|  |  | # of vCPU | Modifiable Input |  | 1 | 1 |  | 1 | 2 |  | 2 | 3 |  | 3 | 4 |
|  |  | # of RAM | Modifiable Input |  | 1 | 1 |  | 1 | 2 |  | 2 | 3 |  | 3 | 4 |
|  | Agent Memory Bank | # of Queries / Month | Calculated Input |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | # of Query Turns / Month | Calculated Input |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | # of Memories / Query | Modifiable Input | 1 | 2 | 3 | 2 | 2 | 2 | 2 | 2 | 2 | 3 | 3 | 3 |
|  |  | # of Retrieved Memories / Query Turn | Modifiable Input | 1 | 2 | 3 | 2 | 2 | 2 | 2 | 2 | 2 | 3 | 3 | 3 |
| Govern | Agent Gateway | # of Query Turns / Month | Calculated Input |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | # of RAG Searches / Month | Calculated Input |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | # of Groundings / Month | Calculated Input |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | # of API Calls / Month | Calculated Input |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | # of Agent Sandbox Calls / Month | Calculated Input |  |  |  |  |  |  |  |  |  |  |  |  |
|  | Agent Security: Model Armor | # of Tokens / Month | Calculated Input |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | % of Tokens Scanned | Modifiable Input | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
|  | Agent Security: Security Command Center | SKU Pricing Coming Soon | N/A |  |  |  |  |  |  |  |  |  |  |  |  |
|  | Agent Security: Anomaly Detection | SKU Not Yet Available | N/A |  |  |  |  |  |  |  |  |  |  |  |  |
|  | Agent Semantic Policies | SKU Not Yet Available | N/A |  |  |  |  |  |  |  |  |  |  |  |  |
|  | Agent Identity | SKU Is Included At No Cost | N/A |  |  |  |  |  |  |  |  |  |  |  |  |
|  | Agent Registry | SKU Is Included At No Cost | N/A |  |  |  |  |  |  |  |  |  |  |  |  |
| Optimize | Agent Evaluation | Gemini Model | Modifiable Input | Gemini 3.1 Flash-Lite | Gemini 3.1 Flash-Lite | Gemini 3.1 Flash-Lite | Gemini 3.1 Flash-Lite | Gemini 3.1 Flash-Lite | Gemini 3.1 Flash-Lite | Gemini 3.1 Flash-Lite | Gemini 3.1 Flash-Lite | Gemini 3.1 Flash-Lite | Gemini 3.1 Flash-Lite | Gemini 3.1 Flash-Lite | Gemini 3.1 Flash-Lite |
|  |  | # of Eval Runs / Month | Modifiable Input | 5000 | 5000 | 5000 | 10000 | 10000 | 10000 | 10000 | 10000 | 10000 | 25000 | 25000 | 25000 |
|  |  | # of Input Tokens / Eval Run | Modifiable Input | 200 | 200 | 200 | 200 | 200 | 200 | 200 | 200 | 200 | 200 | 200 | 200 |
|  |  | # of Output Tokens / Eval Run | Modifiable Input | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 |
|  | Agent Observability: Cloud Logging | # of Tokens for User Queries / Month | Calculated Input |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | # of Tokens for API Calls / Month | Modifiable Input |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | % Sampling Rate | Modifiable Input | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 |
|  | Agent Observability: Cloud Trace | # of API Calls / Month | Calculated Input |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | % Sampling Rate | Modifiable Input | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 |
|  | Agent Observability: Cloud Monitoring | SKU Pricing Coming Soon | N/A |  |  |  |  |  |  |  |  |  |  |  |  |

## B. Pre-Built Agentic Use Cases

| Phase | Product / SKU | Data Field | Category | Brand-Adherent Research & Desk Agent | On-Brand GenMedia Agent | Custom Data Insights Agent (YouTube Data API) | SDLC + Code Context Agent | Invoice Reconciliation Agent | Contract Analysis Agent (High-Volume Batch) | Contract Analysis Agent (Vendor Contracts) | Credit Lending Agent (Competitive Pricing) | KYC Research Agent (Businesses) | Nurse Handoff Agent |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Use Case | Use Case | # of Users | Use Case Input |  |  |  |  |  |  |  |  |  |  |
|  |  | # of Queries / User / Month | Modifiable Input | 40 | 25 | 40 | 80 | 40 | 100 | 20 | 100 | 100 | 20 |
|  |  | # of Turns / Query | Modifiable Input | 6 | 5 | 10 | 3 | 5 | 2 | 5 | 3 | 3 | 2 |
|  |  | % of Query Turns with Tools & API Calls | Modifiable Input | 0.4 |  | 0.6 | 0.2 | 1 |  |  | 0.75 | 0.75 |  |
|  |  | # of Tools & API Calls / Query Turn | Modifiable Input | 20 |  | 10 | 3 | 2 |  |  | 8 | 7 |  |
|  |  | % of Query Turns with Agent Calls | Modifiable Input |  |  |  |  |  |  |  |  |  |  |
|  |  | # of Agent Calls / Query Turn | Modifiable Input |  |  |  |  |  |  |  |  |  |  |
|  |  | # of Initial Prompt Input Tokens | Modifiable Input | 1000 | 500 | 2500 | 1500 | 500 | 500 | 2000 | 2500 | 500 | 300 |
|  |  | # of Follow-Up Input Tokens | Modifiable Input | 1200 | 250 | 250 | 500 | 150 | 250 | 750 | 500 | 250 | 150 |
|  |  | # of Average Output Tokens | Modifiable Input | 1500 | 750 | 600 | 3000 | 750 | 400 | 1500 | 500 | 1000 | 400 |
| Build | Google Gemini for User Query | # of Monthly Input Tokens | Calculated Input |  |  |  |  |  |  |  |  |  |  |
|  |  | # of Monthly Output Tokens | Calculated Input |  |  |  |  |  |  |  |  |  |  |
|  |  | Gemini Model | Modifiable Input | Gemini 3.0 Flash | Gemini 3.0 Flash | Gemini 3.0 Flash | Gemini 3.1 Pro (<= 200k) | Gemini 3.0 Flash | Gemini 3.0 Flash | Gemini 3.0 Flash | Gemini 3.0 Flash | Gemini 3.0 Flash | Gemini 3.1 Flash-Lite |
|  | Google Gemini for Tools & API Calls | # of Tools & API Calls / Month | Calculated Input |  |  |  |  |  |  |  |  |  |  |
|  |  | Gemini Model | Modifiable Input | Gemini 3.1 Flash-Lite |  | Gemini 3.0 Flash | Gemini 3.1 Flash-Lite | Gemini 3.1 Flash-Lite | Gemini 3.1 Flash-Lite | Gemini 3.1 Flash-Lite | Gemini 3.1 Flash-Lite | Gemini 3.1 Flash-Lite |  |
|  |  | # of Input Tokens / Tool & API Call | Modifiable Input | 250 |  | 3000 | 200 | 250 | 250 | 250 | 300 | 250 |  |
|  |  | # of Output Tokens / Tool & API Call | Modifiable Input | 350 |  | 800 | 300 | 350 | 350 | 350 | 400 | 350 |  |
|  | Google Gemini for Agent Calls | # of Agent Calls / Month | Calculated Input |  |  |  |  |  |  |  |  |  |  |
|  |  | Gemini Model | Modifiable Input |  |  |  |  |  |  |  |  |  |  |
|  |  | # of Input Tokens / Agent Call | Modifiable Input |  |  |  |  |  |  |  |  |  |  |
|  |  | # of Output Tokens / Agent Call | Modifiable Input |  |  |  |  |  |  |  |  |  |  |
|  | Apigee for Tools & API Calls | # of Tool, API, Agent Calls / Month | Calculated Input |  |  |  |  |  |  |  |  |  |  |
|  |  | % of Tools, API, Agent Calls that Require Apigee | Modifiable Input |  |  |  |  |  |  |  |  |  |  |
|  |  | # of Environments | Modifiable Input | 2 |  | 2 | 1 | 1 |  |  | 1 | 2 |  |
|  |  | Environment Type | Modifiable Input | Intermediate |  | Intermediate | Intermediate | Intermediate |  |  | Comprehensive | Intermediate |  |
|  | BigQuery API Calls | # of Query Turns / Month | Calculated Input |  |  |  |  |  |  |  |  |  |  |
|  |  | % of Query Turns with API Calls | Modifiable Input | 0 |  |  | 0.3 | 1 | 1 | 1 | 1 |  |  |
|  |  | # of BigQuery API Calls / Query Turn | Modifiable Input | 0 |  |  | 1 | 1 | 2 | 5 | 5 |  |  |
|  |  | # GB of Data / API Call | Modifiable Input | 0 |  |  | 0.15 | 0.2 | 0.25 | 0.25 | 0.3 |  |  |
|  | Imagen for Image Generation | # of Query Turns / Month | Calculated Input |  |  |  |  |  |  |  |  |  |  |
|  |  | Imagen Model | Modifiable Input |  |  |  |  |  |  |  |  |  |  |
|  |  | % of Turns Needing Image Generation | Modifiable Input |  |  |  |  |  |  |  |  |  |  |
|  |  | # of Images Generated per Turn | Modifiable Input |  |  |  |  |  |  |  |  |  |  |
|  | Veo for Video Generation | # of Query Turns / Month | Calculated Input |  |  |  |  |  |  |  |  |  |  |
|  |  | Veo Model | Modifiable Input |  |  |  |  |  |  |  |  |  |  |
|  |  | Video Output Type | Modifiable Input |  |  |  |  |  |  |  |  |  |  |
|  |  | Video Resolution | Modifiable Input |  |  |  |  |  |  |  |  |  |  |
|  |  | % of Turns Needing Video Generationn | Modifiable Input |  |  |  |  |  |  |  |  |  |  |
|  |  | # Seconds of Video Generated per Turn | Modifiable Input |  |  |  |  |  |  |  |  |  |  |
|  | Agent Search for RAG | # of Query Turns / Month | Calculated Input |  |  |  |  |  |  |  |  |  |  |
|  |  | % of Query Turns that Require Search | Modifiable Input | 0.2 |  | 0 | 0.1 | 0.75 | 0.5 | 0.75 | 0.3 | 0.25 | 0.1 |
|  |  | # GBs of Data Indexed | Modifiable Input | 100 |  | 0 | 100 | 250 | 100 | 250 | 350 | 250 | 50 |
|  | Grounding with Google Search | # of Query Turns / Month | Calculated Input |  |  |  |  |  |  |  |  |  |  |
|  |  | % of Query Turns that Require Google Search Grounding | Modifiable Input | 0.2 |  | 0.05 |  |  |  |  |  | 0.4 |  |
|  | Grounding with Google Maps | # of Query Turns / Month | Calculated Input |  |  |  |  |  |  |  |  |  |  |
|  |  | % of Query Turns that Require Google Maps Grounding | Modifiable Input | 0 |  |  |  |  |  |  |  |  |  |
| Scale | Agent Runtime | # of Query Turns / Month | Calculated Input |  |  |  |  |  |  |  |  |  |  |
|  |  | # Seconds / Query Turn | Modifiable Input | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 5 |
|  |  | # of vCPU | Modifiable Input | 1 | 2 | 3 | 1 | 2 | 1 | 2 | 1 | 2 | 1 |
|  |  | # of RAM | Modifiable Input | 1 | 2 | 3 | 1 | 2 | 1 | 2 | 1 | 2 | 1 |
|  | Agent Sessions | # of Query Turns / Month | Calculated Input |  |  |  |  |  |  |  |  |  |  |
|  |  | # of Events / Query Turn | Modifiable Input | 6 |  | 3 | 3 | 3 | 3 | 3 | 3 | 3 |  |
|  | Agent Sandbox: Code Execution | # of Runtime Hours / Month | Calculated Input |  |  |  |  |  |  |  |  |  |  |
|  |  | % of Usage for Code Execution | Modifiable Input | 0.1 |  | 0 | 0.3 |  |  |  | 0.3 |  |  |
|  |  | # of vCPU | Modifiable Input | 1 |  | 0 | 1 |  |  |  | 1 |  |  |
|  |  | # of RAM | Modifiable Input | 2 |  | 0 | 1 |  |  |  | 1 |  |  |
|  | Agent Sandbox: Computer Use | # of Runtime Hours / Month | Calculated Input |  |  |  |  |  |  |  |  |  |  |
|  |  | % of Usage for Computer Use | Modifiable Input | 0 |  | 0 | 0.3 |  |  |  | 0.3 |  |  |
|  |  | # of vCPU | Modifiable Input | 0 |  | 0 | 1 |  |  |  | 1 |  |  |
|  |  | # of RAM | Modifiable Input | 0 |  | 0 | 1 |  |  |  | 1 |  |  |
|  | Agent Memory Bank | # of Queries / Month | Calculated Input |  |  |  |  |  |  |  |  |  |  |
|  |  | # of Query Turns / Month | Calculated Input |  |  |  |  |  |  |  |  |  |  |
|  |  | # of Memories / Query | Modifiable Input | 15 |  | 0 | 3 | 2 | 3 | 3 | 1 | 2 |  |
|  |  | # of Retrieved Memories / Query Turn | Modifiable Input | 2 |  | 0 | 3 | 2 | 3 | 3 | 1 | 2 |  |
| Govern | Agent Gateway | # of Query Turns / Month | Calculated Input |  |  |  |  |  |  |  |  |  |  |
|  |  | # of RAG Searches / Month | Calculated Input |  |  |  |  |  |  |  |  |  |  |
|  |  | # of Groundings / Month | Calculated Input |  |  |  |  |  |  |  |  |  |  |
|  |  | # of API Calls / Month | Calculated Input |  |  |  |  |  |  |  |  |  |  |
|  |  | # of Agent Sandbox Calls / Month | Calculated Input |  |  |  |  |  |  |  |  |  |  |
|  | Agent Security: Model Armor | # of Tokens / Month | Calculated Input |  |  |  |  |  |  |  |  |  |  |
|  |  | % of Tokens Scanned | Modifiable Input | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
|  | Agent Security: Security Command Center | SKU Pricing Coming Soon | N/A |  |  |  |  |  |  |  |  |  |  |
|  | Agent Security: Anomaly Detection | SKU Not Yet Available | N/A |  |  |  |  |  |  |  |  |  |  |
|  | Agent Semantic Policies | SKU Not Yet Available | N/A |  |  |  |  |  |  |  |  |  |  |
|  | Agent Identity | SKU Is Included At No Cost | N/A |  |  |  |  |  |  |  |  |  |  |
|  | Agent Registry | SKU Is Included At No Cost | N/A |  |  |  |  |  |  |  |  |  |  |
| Optimize | Agent Evaluation | Gemini Model | Modifiable Input | Gemini 3.1 Flash-Lite | Gemini 3.1 Flash-Lite | Gemini 3.1 Flash-Lite | Gemini 3.1 Flash-Lite | Gemini 3.1 Flash-Lite | Gemini 3.1 Flash-Lite | Gemini 3.1 Flash-Lite | Gemini 3.1 Flash-Lite | Gemini 3.1 Flash-Lite | Gemini 3.1 Flash-Lite |
|  |  | # of Eval Runs / Month | Modifiable Input | 10000 | 10000 | 10000 | 10000 | 10000 | 10000 | 10000 | 10000 | 10000 | 10000 |
|  |  | # of Input Tokens / Eval Run | Modifiable Input | 200 | 200 | 200 | 200 | 200 | 200 | 200 | 200 | 200 | 200 |
|  |  | # of Output Tokens / Eval Run | Modifiable Input | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 |
|  | Agent Observability: Cloud Logging | # of Tokens for User Queries / Month | Calculated Input |  |  |  |  |  |  |  |  |  |  |
|  |  | # of Tokens for API Calls / Month | Modifiable Input |  |  |  |  |  |  |  |  |  |  |
|  |  | % Sampling Rate | Modifiable Input | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 |
|  | Agent Observability: Cloud Trace | # of API Calls / Month | Calculated Input |  |  |  |  |  |  |  |  |  |  |
|  |  | % Sampling Rate | Modifiable Input | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 |
|  | Agent Observability: Cloud Monitoring | SKU Pricing Coming Soon | N/A |  |  |  |  |  |  |  |  |  |  |
