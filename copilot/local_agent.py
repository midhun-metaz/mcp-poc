"""Local SLM agent: a second MCP host. A small model in Ollama chooses the MCP tools, we run them and send back
the results. It uses the same MCP server, tools and prompt as the Gemini agent; only the model is different.
"""

import json
import os

import httpx
from mcp import Client

from copilot.agent import MAX_STEPS, MCP_URL, SYSTEM_PROMPT, run_tool

OLLAMA_URL = "http://127.0.0.1:11434"
LOCAL_MODEL = os.environ.get("LOCAL_AGENT_MODEL", "gemma4:e2b")  # any Ollama model that supports tools

# Small models need more guidance than Gemini. Measured with qwen3:1.7b on 4 test questions: the shared prompt
# without thinking called the right tool 1/4 times (and invented a status for an unknown ID); this stricter
# prompt with thinking on got 4/4, at about 40 s per question on this CPU.
LOCAL_PROMPT = SYSTEM_PROMPT + """
Always call a tool before answering any question about applications, and answer only from the tool results.
Never write a tool call as text; use the tool calling format."""
THINK = True


def ollama_tools(mcp_tools):
    """Describe the MCP tools to Ollama, in the function format its tool calling expects."""
    return [
        {"type": "function", "function": {"name": tool.name, "description": tool.description, "parameters": tool.input_schema}}
        for tool in mcp_tools
    ]


async def ask(ollama, mcp_client, tools, history, question, on_step):
    """Answer one question. Returns the answer and the updated conversation history (a list of chat messages)."""
    messages = history + [{"role": "user", "content": question}]
    for _ in range(MAX_STEPS):
        response = await ollama.post("/api/chat", json={
            "model": LOCAL_MODEL,
            "messages": [{"role": "system", "content": LOCAL_PROMPT}] + messages,
            "tools": tools,
            "think": THINK,
            "stream": False,
            "options": {"temperature": 0},
        })
        if response.is_error:
            raise RuntimeError(f"Ollama: {response.text}")  # for example: model "gemma4:e2b" not found
        message = response.json()["message"]
        messages.append(message)
        if not message.get("tool_calls"):
            return message["content"], messages

        for call in message["tool_calls"]:
            name, args = call["function"]["name"], call["function"]["arguments"]
            on_step({"type": "tool_started", "tool": name, "args": args})
            result = await run_tool(mcp_client, name, args)
            on_step({"type": "tool_finished", "tool": name, "args": args, **result})
            messages.append({"role": "tool", "tool_name": name, "content": json.dumps(result)})

    return "Sorry, that took too many steps. Please try a simpler request.", history


async def answer_question(history, question, on_step):
    """Connect to the MCP server, discover its tools and answer one question with the local model."""
    async with httpx.AsyncClient(base_url=OLLAMA_URL, timeout=300) as ollama, Client(MCP_URL) as mcp_client:
        tools = ollama_tools((await mcp_client.list_tools()).tools)
        return await ask(ollama, mcp_client, tools, history, question, on_step)
