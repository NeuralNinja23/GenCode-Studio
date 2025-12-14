# app/lib/monitoring.py
from fastapi import FastAPI
from prometheus_client.registry import CollectorRegistry as Registry
from prometheus_client import Gauge
from prometheus_fastapi_instrumentator import Instrumentator
from app.core.logging import log

# Create a separate registry
registry = Registry()

# Re-create the custom Gauge
active_preview_servers = Gauge(
    'gencode_active_preview_servers',
    'Number of active preview/dev servers',
    registry=registry
)

def set_active_preview_servers(n: int):
    """Sets the value of the active preview servers gauge."""
    active_preview_servers.set(n)

def register_monitoring(app: FastAPI):
    """
    Registers Prometheus monitoring on the FastAPI app.
    This replaces the Express middleware and /metrics endpoint.
    """
    
    # This single line replaces the Express middleware for request counting and duration.
    instrumentator = Instrumentator(
        excluded_handlers=["/metrics"], # Don't monitor the metrics endpoint itself
        registry=registry # Use our custom registry
    ).instrument(app)

    # This exposes the /metrics endpoint
    instrumentator.expose(app, include_in_schema=False, should_gzip=True)

    log("MONITORING", "Prometheus instrumentation registered at /metrics.")
