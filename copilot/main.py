"""Copilot chat API: the React UI sends chat messages here. The chosen host (Gemini in the cloud, or a small model
running locally in Ollama) answers them using the same MCP tools.

Run: .venv/bin/python -m copilot.main   (start the app server and MCP server first)
"""

import asyncio
import json
from typing import Literal

import uvicorn
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from copilot import agent, local_agent

PORT = 8002

app = FastAPI(title="LOS Copilot")
CONVERSATIONS = {}  # (host, conversation id) -> history, kept in memory (single-user POC)

# Two MCP hosts that share the same MCP server and tools: a cloud LLM and a local SLM.
HOSTS = {
    "gemini": (agent, agent.GEMINI_MODEL),
    "local": (local_agent, local_agent.LOCAL_MODEL),
}


class ChatRequest(BaseModel):
    conversation_id: str
    message: str
    host: Literal["gemini", "local"] = "gemini"


@app.post("/chat")
async def chat(request: ChatRequest):
    """Stream one copilot turn as JSON lines: tool steps as they happen, then the answer or an error."""
    events = asyncio.Queue()

    host, model = HOSTS[request.host]
    key = (request.host, request.conversation_id)  # each host keeps its own history format

    async def run_agent():
        try:
            answer, CONVERSATIONS[key] = await host.answer_question(
                CONVERSATIONS.get(key, []), request.message, on_step=events.put_nowait
            )
            events.put_nowait({"type": "answer", "text": answer, "model": model})
        except Exception as error:
            while isinstance(error, ExceptionGroup):  # MCP connection errors arrive wrapped
                error = error.exceptions[0]
            events.put_nowait({"type": "error", "message": str(error)})
        events.put_nowait(None)  # end of this turn

    async def stream():
        task = asyncio.create_task(run_agent())
        while (event := await events.get()) is not None:
            yield json.dumps(event) + "\n"
        await task

    return StreamingResponse(stream(), media_type="application/x-ndjson")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=PORT)
