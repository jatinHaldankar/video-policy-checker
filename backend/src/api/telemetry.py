import os
import logging
from azure.monitor.opentelemetry import configure_azure_monitor

# Azure opentelementry integtation tracks the app performance, errors, requests

logger = logging.getLogger("compliance-project-telementry")


def setup_telemetry():
    """
    Intitializes azure monitor opentelementry.

    what is opentelementry?
    -> Industry standard observability framework
    -> Tracks the https requests, database queires, errors, performance metrics
    -> sends this data to azure monitor

    What does "hooks into FastAPI automatically" mean?
    -> Once configured, it auto-captures every API Requests/response
    -> No Need to manually log each endpoint
    -> Tracks the response time, error rates, dependencies
    """
    connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")

    if not connection_string:
        logger.warning("No Instrumention key found.")
        return

    try:
        configure_azure_monitor(
            connection_string=connection_string,
            logger_name="compliance-project-telementry",
        )
        logger.info("Azure Monitor Tracking is enabled and connected")
    except Exception as e:
        logger.error(f"Failed to initialize the azure monitor: {e}")
