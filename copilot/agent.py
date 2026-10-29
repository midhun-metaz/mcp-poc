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
A message may include the application the officer has open; "this application" means that one.
To create applications, call create_application once per person with only the facts the user gave.
If the outcome is needs_information, ask the user for the missing fields.
A draft is not submitted or approved. Document presence does not prove validity.
Amounts are in INR. Keep answers short."""

FOLLOW_UP_PROMPT = """Suggest 3 short questions the loan officer could ask the copilot next, based on this exchange.
The copilot can only list or look up applications, create draft applications and read documents.
Reuse the application IDs and names from the exchange. If the copilot asked for details,
one suggestion may give example values (all data is synthetic). At most 12 words each."""


def make_config(mcp_tools, rules):
    """Describe the MCP tools and the loan rules to Gemini. Automatic calling is off, so we run the tools ourselves."""
    declarations = [
        types.FunctionDeclaration(
            name=tool.name, description=tool.description, parameters_json_schema=tool.input_schema
        )
        for tool in mcp_tools
    ]
    return types.GenerateContentConfig(
        system_instruction=f"{SYSTEM_PROMPT}\n\nLoan rules (MCP resource los://rules): {rules}",
        tools=[types.Tool(function_declarations=declarations)],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )


async def run_tool(mcp_client, name, args):
    """Run one MCP tool and return its result to Gemini."""
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


async def read_resource(mcp_client, uri):
    """Read one MCP resource as text."""
    return (await mcp_client.read_resource(uri)).contents[0].text


async def answer_question(history, question, on_step, application_id=None, prompt=None):
    """Connect to the MCP server, gather context from its resources and prompts, and answer one question.

    application_id is the application open in the UI. prompt is the name of an MCP prompt the user picked;
    its text replaces the question."""
    gemini = genai.Client()
    async with Client(MCP_URL) as mcp_client:
        # Prompt: a ready-made instruction the user picked replaces the typed question.
        if prompt:
            result = await mcp_client.get_prompt(prompt, {"application_id": application_id})
            question = result.messages[0].content.text

        # Resources: context the host attaches itself, before the model asks for anything.
        resources = ["los://rules"]
        rules = await read_resource(mcp_client, "los://rules")
        if application_id:
            uri = f"los://applications/{application_id}"
            resources.append(uri)
            open_application = await read_resource(mcp_client, uri)
            question += f"\n\nApplication the officer has open (MCP resource {uri}): {open_application}"
        on_step({"type": "context", "resources": resources})

        gemini_config = make_config((await mcp_client.list_tools()).tools, rules)
        return await ask(gemini, mcp_client, gemini_config, history, question, on_step)


async def list_prompts():
    """The MCP server's prompts, for the UI to offer as buttons. Each one takes an application_id."""
    async with Client(MCP_URL) as mcp_client:
        return [
            {"name": prompt.name, "title": prompt.title, "description": prompt.description}
            for prompt in (await mcp_client.list_prompts()).prompts
        ]


async def suggest_follow_ups(question, answer):
    """Ask Gemini for three follow-up questions that fit the last question and answer."""
    response = await genai.Client().aio.models.generate_content(
        model=GEMINI_MODEL,
        contents=f"Loan officer: {question}\nCopilot: {answer}\n\n{FOLLOW_UP_PROMPT}",
        config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=list[str]),
    )
    return response.parsed[:3]
