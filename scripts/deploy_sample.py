"""Deploy an external ADK-sample agent to Vertex AI Agent Engine.

adk-samples live at ../adk-samples/python/agents/<sample>/<package>/agent.py with
a `root_agent`. This imports that root_agent and deploys it, shipping the sample's
package via extra_packages and its runtime deps via requirements (dev tools filtered).

Usage:
  python scripts/deploy_sample.py --sample financial-advisor --package financial_advisor [--check]
"""

import argparse
import importlib
import json
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SAMPLES = Path("/home/jasmeetbhatia/github/adk-samples/python/agents")
DATA = REPO / "data"

PROJECT, LOCATION = "jsb-genai-sa", "us-central1"
STAGING = "gs://jsb-genai-sa-staging"

# Dev/test deps to exclude from the deployed container requirements.
_DEV = ("pytest", "ruff", "mypy", "codespell", "types-", "agent-starter-pack",
        "black", "isort", "pre-commit", "ipykernel", "jupyter")


def runtime_requirements(sample_dir: Path) -> list[str]:
    pyproj = sample_dir / "pyproject.toml"
    reqs = []
    if pyproj.exists():
        txt = pyproj.read_text()
        m = re.search(r"dependencies\s*=\s*\[(.*?)\]", txt, re.S)
        if m:
            for q in re.findall(r'"([^"]+)"', m.group(1)):
                low = q.lower()
                if not any(d in low for d in _DEV):
                    reqs.append(q)
    # Ensure the agent-engines extra is present.
    if not any("agent" in r and "aiplatform" in r for r in reqs):
        reqs.append("google-cloud-aiplatform[adk,agent-engines]>=1.93.0")
    return reqs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", required=True)
    ap.add_argument("--package", required=True)
    ap.add_argument("--check", action="store_true", help="import root_agent only, no deploy")
    args = ap.parse_args()

    sample_dir = SAMPLES / args.sample
    assert sample_dir.exists(), f"missing {sample_dir}"

    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "1")
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", PROJECT)
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", LOCATION)
    os.environ.setdefault("GOOGLE_CLOUD_STORAGE_BUCKET", STAGING.replace("gs://", ""))

    os.chdir(sample_dir)
    sys.path.insert(0, str(sample_dir))
    root_agent = importlib.import_module(f"{args.package}.agent").root_agent
    print(f"Imported root_agent: name={getattr(root_agent,'name','?')} "
          f"sub_agents={len(getattr(root_agent,'sub_agents',[]) or [])} "
          f"tools={len(getattr(root_agent,'tools',[]) or [])}")
    if args.check:
        print("CHECK OK")
        return

    import vertexai
    from vertexai import agent_engines
    reqs = runtime_requirements(sample_dir)
    print("requirements:", reqs)
    vertexai.init(project=PROJECT, location=LOCATION, staging_bucket=STAGING)
    print(f"Deploying '{args.sample}' (~5-10 min)...")
    remote = agent_engines.create(
        agent_engines.AdkApp(agent=root_agent, enable_tracing=True),
        display_name=f"sample_{args.package}",
        requirements=reqs,
        extra_packages=[args.package],
    )
    name = remote.resource_name
    print("DEPLOYED:", name)
    out = DATA / f"deployment_{args.package}.json"
    out.write_text(json.dumps({"sample": args.sample, "package": args.package,
                               "resource_name": name}, indent=2))
    print("Saved", out)


if __name__ == "__main__":
    main()
