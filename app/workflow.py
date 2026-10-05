from datetime import datetime, timezone
from agents.orchestrator import Orchestrator

def run_opportunity_pipeline(product: dict):
    return Orchestrator().run(product, datetime.now(timezone.utc).isoformat())
