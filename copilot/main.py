import asyncio
import json

import uvicorn
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from copilot import agent

PORT = 8002

app = FastAPI(title="LOS Copilot")
CONVERSATIONS = {}  # conversation id -> history, kept in memory (single-user POC)

class ChatRequest(BaseModel):
    conversation_id: str
    message: str
    application_id: str | None = None  # the application open in the UI, attached as an MCP resource
    prompt: str | None = None  # an MCP prompt the user picked; its text replaces the message


@app.post("/chat")
async def chat(request: ChatRequest):
    """Stream one copilot turn as JSON lines: the MCP resources attached as context, tool steps as they happen,
    then the answer or an error, then follow-up questions for the UI to offer."""
    events = asyncio.Queue()

    key = request.conversation_id

    async def run_agent():
        try:
            answer, CONVERSATIONS[key] = await agent.answer_question(
                CONVERSATIONS.get(key, []),
                request.message,
                on_step=events.put_nowait,
                application_id=request.application_id,
                prompt=request.prompt,
            )
            events.put_nowait({"type": "answer", "text": answer, "model": agent.GEMINI_MODEL})
        except Exception as error:
            while isinstance(error, ExceptionGroup):  # MCP connection errors arrive wrapped
                error = error.exceptions[0]
            events.put_nowait({"type": "error", "message": str(error)})
        else:
            try:
                questions = await agent.suggest_follow_ups(request.message, answer)
                events.put_nowait({"type": "suggestions", "questions": questions})
            except Exception as error:  # the answer is already shown, so just skip the suggestions
                print("Could not suggest follow-ups:", error)
        events.put_nowait(None)  # end of this turn

    async def stream():
        task = asyncio.create_task(run_agent())
        while (event := await events.get()) is not None:
            yield json.dumps(event) + "\n"
        await task

    return StreamingResponse(stream(), media_type="application/x-ndjson")


@app.get("/chat/prompts")
async def prompts():
    """The MCP prompts the UI offers as buttons."""
    return await agent.list_prompts()


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=PORT)
