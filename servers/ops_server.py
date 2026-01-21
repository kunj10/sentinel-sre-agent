"""
Ops Server (MCP Tools)
----------------------
This is a FastMCP server that exposes Docker operations as tools the agent can call.
MCP (Model Context Protocol) is how we give the agent "hands" - instead of just
analyzing text, it can actually interact with the infrastructure.

The agent connects to this via stdin/stdout when it starts up. Each @mcp.tool()
decorator turns a function into something the agent can invoke by name.

Think of it as a microservice, except the client is an AI agent.
"""

import docker
from mcp.server.fastmcp import FastMCP
from docker.errors import NotFound

mcp = FastMCP("Sentinel_Ops")

# Try to connect to Docker. If it's not running, we'll fail gracefully
# instead of crashing on import.
try:
    client = docker.from_env()
except Exception as e:
    print(f"⚠️  Docker daemon not running: {e}")
    client = None


@mcp.tool()
def list_active_containers() -> str:
    """
    Returns a quick summary of what's running.
    The agent usually calls this first to see what containers exist.
    """
    if not client:
        return "Error: Docker unavailable."

    try:
        containers = client.containers.list()
        if not containers:
            return "No active containers found."

        report = "ACTIVE CONTAINERS:\n"
        for c in containers:
            report += f"- {c.name} (ID: {c.short_id}): {c.status}\n"
        return report
    except Exception as e:
        return f"Docker Error: {str(e)}"


@mcp.tool()
def get_container_logs(container_name: str, tail: int = 50) -> str:
    """
    Grab the last N lines of logs from a container.
    This is what the agent uses to diagnose problems.
    """
    if not client:
        return "Error: Docker unavailable."

    try:
        container = client.containers.get(container_name)
        logs = container.logs(tail=tail).decode('utf-8')
        return logs or "Logs are empty."

    except NotFound:
        return f"Error: Container '{container_name}' not found."
    except Exception as e:
        return f"System Error: {str(e)}"


@mcp.tool()
def restart_service(container_name: str) -> str:
    """
    Restart a container that's crashed or stuck.

    The agent only calls this when the DSPy brain recommends it -
    we don't want random restarts for every minor error.
    """
    if not client:
        return "Error: Docker unavailable."

    try:
        container = client.containers.get(container_name)
        container.restart()
        return f"✅ Service '{container_name}' restarted successfully."
    except Exception as e:
        return f"Restart Failed: {str(e)}"


if __name__ == "__main__":
    mcp.run()
