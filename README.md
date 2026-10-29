# LOS Copilot

A demo loan application app with AI chat and document uploads. Uses React, Python, SQLite, Gemini for chat, and Ollama for document checks. All sample data is fake.

## Setup

Install Python, Node.js 22, and Ollama, then run:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
ollama pull gemma4:e2b
cd frontend && npm install
```

Add your `GEMINI_API_KEY` to `.env`.

## Run

Run each command in a separate terminal from the project folder. Skip `ollama serve` if Ollama is already running.

```bash
ollama serve
.venv/bin/python -m app_server.main
.venv/bin/python -m mcp_server.server
.venv/bin/python -m copilot.main
cd frontend && npm run dev
```

Open [the app](http://127.0.0.1:5173). Select an application, ask questions in chat, or upload a PDF from `samples/`. Uploads check the applicant name, salary income, document type, and duplicates.

## Test

```bash
.venv/bin/python -m unittest discover -s tests -v
```
