"""
Sentinel API Server
-------------------
This is the REST interface for Sentinel. Instead of running the agent in a terminal,
you can POST incidents here and get back structured JSON responses.

I went with FastAPI because the automatic Swagger docs are genuinely useful for testing,
and the async support plays nicely with Google ADK's streaming responses.
"""

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from agents.sentinel_agent import create_sentinel

app = FastAPI(
    title="Sentinel SRE Agent API",
    description="Autonomous AI Agent for Root Cause Analysis",
)

# Globals to hold the agent and session state between requests.
# Not ideal for horizontal scaling, but works fine for single-instance deployments.
agent_instance = None
session_service = None


class QueryRequest(BaseModel):
    user_id: str = "api_user_01"
    session_id: str = "session_001"
    query: str

    class Config:
        # Swagger UI will show this as an example - saves time when testing
        json_schema_extra = {
            "example": {
                "user_id": "kunj369",
                "session_id": "incident_123",
                "query": "Check logs for chaos-monkey and fix any critical errors."
            }
        }


@app.on_event("startup")
async def startup_event():
    """
    Spin up the agent once when the server starts, not on every request.
    Loading the DSPy brain and MCP toolset takes a few seconds, so we do it here.
    """
    global agent_instance, session_service
    print("\n🚀 Booting up Sentinel Agent...")

    agent_instance = create_sentinel()
    session_service = InMemorySessionService()

    print("✅ Sentinel is online and ready.\n")


@app.post("/analyze")
async def analyze_incident(request: QueryRequest):
    """
    Main endpoint - send an incident description, get back an RCA.

    The agent will:
    1. Check container logs via MCP tools
    2. Run the logs through the DSPy-trained brain
    3. Return root cause + recommended action
    """
    global agent_instance, session_service

    try:
        # Sessions let us maintain conversation context across multiple requests.
        # If the session already exists, that's fine - just reuse it.
        try:
            await session_service.create_session(
                session_id=request.session_id,
                user_id=request.user_id,
                app_name="Sentinel_API"
            )
        except Exception:
            pass  # Session exists, no problem

        # The Runner wires everything together: agent + session + tools
        runner = Runner(
            agent=agent_instance,
            app_name="Sentinel_API",
            session_service=session_service
        )

        # Package the user's query in the format ADK expects
        user_msg = types.Content(
            role="user",
            parts=[types.Part(text=request.query)]
        )

        # Stream the response - the agent might make multiple tool calls,
        # so we accumulate all the text parts into one final answer
        final_response = ""
        async for event in runner.run_async(
            session_id=request.session_id,
            user_id=request.user_id,
            new_message=user_msg
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        final_response += part.text

        return {
            "status": "success",
            "session_id": request.session_id,
            "response": final_response
        }

    except Exception as e:
        # Full traceback to console helps with debugging
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)