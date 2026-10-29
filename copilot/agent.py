"""Gemini agent (the MCP host): Gemini chooses MCP tools, we run them through the MCP server and send back the results."""

import os

from dotenv import load_dotenv
from google import genai
from google.genai import types
from mcp import Client

load_dotenv()  # reads GEMINI_API_KEY from .env; variables already set are kept

MCP_URL = "http://127.0.0.1:8000/mcp"
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
MAX_STEPS = 6  # model requests per question, so the model cannot loop forever

SYSTEM_PROMPT = """You are a loan origination copilot. All data is synthetic.
Use the tools for every application fact. Never invent IDs, statuses or applicant details.
To create applications, call create_application once per person with only the facts the user gave.
If the outcome is needs_information, ask the user for the missing fields.
A draft is not submitted or approved. Document presence does not prove validity.
Amounts are in INR. Keep answers short."""


def make_config(mcp_tools):
    """Describe the MCP tools to Gemini. Automatic calling is off, so we run the tools ourselves."""
    declarations = [
        types.FunctionDeclaration(
            name=tool.name, description=tool.description, parameters_json_schema=tool.input_schema
        )
        for tool in mcp_tools
    ]
    return types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=[types.Tool(function_declarations=declarations)],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )


async def run_tool(mcp_client, name, args):
    """Run one MCP tool. Shared by both hosts: the Gemini agent here and the local SLM agent."""
    result = await mcp_client.call_tool(name, args)
    if result.is_error:
        # MCP explains unknown tools, bad arguments and app server errors, so the model can react.
        return {"error": result.content[0].text}
    return {"result": result.structured_content}


async def ask(gemini, mcp_client, gemini_config, history, question, on_step):
    """Answer one question. Returns the answer and the updated conversation history.

    on_step is called before and after every tool call, so the UI can show tool steps live."""
    contents = history + [types.Content(role="user", parts=[types.Part.from_text(text=question)])]
    for _ in range(MAX_STEPS):
        response = await gemini.aio.models.generate_content(
            model=GEMINI_MODEL, contents=contents, config=gemini_config
        )
        # Keep the model's reply unchanged: Gemini needs its thought signatures in the next request.
        contents.append(response.candidates[0].content)
        if not response.function_calls:
            return response.text, contents

        replies = []
        for call in response.function_calls:
            step = {"tool": call.name, "args": call.args or {}}
            on_step({"type": "tool_started", **step})
            result = await run_tool(mcp_client, call.name, call.args or {})
            on_step({"type": "tool_finished", **step, **result})
            replies.append(types.Part(
                function_response=types.FunctionResponse(id=call.id, name=call.name, response=result)
            ))
        contents.append(types.Content(role="user", parts=replies))

    return "Sorry, that took too many steps. Please try a simpler request.", history


async def answer_question(history, question, on_step):
    """Connect to the MCP server, discover its tools and answer one question."""
    gemini = genai.Client()
    async with Client(MCP_URL) as mcp_client:
        gemini_config = make_config((await mcp_client.list_tools()).tools)
        return await ask(gemini, mcp_client, gemini_config, history, question, on_step)
