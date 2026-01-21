"""
Sentinel Agent
--------------
The core agent that ties everything together. It's essentially an AI SRE that can:
- Query Docker containers for logs (via MCP)
- Analyze those logs for root causes (via DSPy brain)
- Recommend actions like restart, escalate, or ignore

The interesting bit is how the agent decides what to do. It uses a DSPy-trained
"brain" that's been optimized on example incidents, so it doesn't just rely on
Gemini's base knowledge - it's been taught our specific patterns.
"""

import asyncio
from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.tools import McpToolset
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from mcp.client.stdio import StdioServerParameters
from google.genai import types
from modules.rca_brain import SREBrain

load_dotenv()

# Load the DSPy brain at module level so it's ready before any requests come in.
# The compiled weights contain few-shot examples that dramatically improve accuracy.
brain_instance = SREBrain()
if hasattr(brain_instance, "load_production_weights"):
    brain_instance.load_production_weights("modules/brain_compiled.json")


def consult_sre_expert(container_name: str, logs: str) -> dict:
    """
    The agent calls this when it spots errors in container logs.

    Instead of asking Gemini to freestyle an analysis, we route through our
    trained DSPy module. It returns structured output: root cause, severity,
    and what action to take. Much more reliable than raw prompting.
    """
    print(f"\n🧠 [Brain] Analyzing logs for {container_name}...")
    prediction = brain_instance(container_name=container_name, logs=logs)
    return {
        "analysis": prediction.reasoning,
        "root_cause": prediction.root_cause,
        "severity": prediction.severity,
        "recommended_action": prediction.suggested_action
    }


def create_sentinel():
    """
    Factory function that assembles the agent with all its tools.

    Two tool sources:
    1. MCP server (ops_server.py) - gives us Docker access
    2. consult_sre_expert - our DSPy brain for analysis
    """
    # MCP lets us run the Docker tools in a separate process.
    # The agent talks to it via stdin/stdout using the MCP protocol.
    ops_tools = McpToolset(
        connection_params=StdioServerParameters(
            command="python",
            args=["servers/ops_server.py"]
        )
    )

    agent = LlmAgent(
        model="gemini-2.5-flash",
        name="Sentinel_Prime",
        instruction="""
        You are an Autonomous Site Reliability Engineer (SRE).
        1. When asked to check a service, FIRST use 'list_active_containers' or 'get_container_logs'.
        2. If you see errors, pass them to 'consult_sre_expert'.
        3. Always report the final status.
        """,
        tools=[ops_tools, consult_sre_expert]
    )
    return agent


async def main():
    """
    Interactive REPL for testing the agent locally.
    For production, use api_server.py instead.
    """
    print("⏳ Initializing Sentinel...")
    agent = create_sentinel()

    # ADK needs a session service to track conversation state
    session_service = InMemorySessionService()
    session_id = "live-session-01"
    user_id = "admin_user"
    app_name = "Sentinel_App"

    await session_service.create_session(
        session_id=session_id,
        user_id=user_id,
        app_name=app_name
    )

    runner = Runner(
        agent=agent,
        app_name=app_name,
        session_service=session_service
    )

    print("✅ Sentinel is Online. (Type 'exit' to quit)")

    while True:
        try:
            user_input = await asyncio.to_thread(input, "\nUser: ")
            if user_input.lower() in ["exit", "quit"]:
                break

            user_msg = types.Content(
                role="user",
                parts=[types.Part(text=user_input)]
            )

            # Stream responses - the agent might call multiple tools before answering
            final_text = ""
            async for event in runner.run_async(
                session_id=session_id,
                user_id=user_id,
                new_message=user_msg
            ):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            final_text += part.text

            print(f"Sentinel: {final_text}")

        except KeyboardInterrupt:
            break
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())