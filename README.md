# LOS Copilot POC

A small loan copilot for learning MCP. All data is fake.

```text
React UI ─┬─ list, form, upload ──────────────────────────────▶ App server (REST API) ─▶ SQLite
          └─ chat ─▶ Copilot API ─▶ Gemini ─MCP─▶ MCP server ─▶ App server            ─▶ local model (Ollama)
```

- `app_server/` – the loan system: REST API, database, local document model
- `mcp_server/` – MCP tools that call the REST API
- `copilot/` – two MCP hosts (Gemini in the cloud, a small model in Ollama) and the chat API used by the UI
- `frontend/` – React UI
- `samples/` – realistic sample PDFs (salary slip, bank statement, ID card, electricity bill) and the script that makes them

## Setup (once)

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env          # then add your GEMINI_API_KEY
ollama pull gemma4:e2b
cd frontend && npm install
```

The frontend needs Node 22 (`frontend/.nvmrc`); with nvm, run `nvm use` in `frontend/` first.

Document extraction uses **Gemma** (`gemma4:e2b`) locally. **Gemini** remains the default chat agent; the optional **Local SLM** chat mode uses the same Gemma model. Qwen is no longer required. Gemma needs an up-to-date Ollama:

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull gemma4:e2b
```

Override the document model with `OLLAMA_MODEL` in `.env`. Set `LOCAL_AGENT_MODEL` separately to override the optional local chat model, which must support tools.

## Evaluate document extraction

With Ollama running, run `.venv/bin/python -m app_server.evaluate_slm` to check classification, name extraction, and net monthly income on nine synthetic documents. To compare another installed model, prefix the command with `OLLAMA_MODEL=<model-name>`. This small sample is a smoke test, not a production accuracy guarantee.

Local comparison on 2026-10-29 (one sequential run per model, including initial model loading):

| Model | Document type | Person name | Monthly income | Average latency |
| --- | --- | --- | --- | --- |
| Gemma `gemma4:e2b` | 9/9 | 9/9 | 9/9 | 8.6 s |
| Qwen `qwen3:1.7b` | 9/9 | 9/9 | 9/9 | 5.3 s |

Gemma consolidates local tasks onto the model already used by optional local chat, but was slower in this test and has a larger installed model (4.6 GB versus 1.4 GB). This change removes the app's Qwen requirement; it does not uninstall existing Ollama models. Restart the app server after changing the document model.

## Start

Run each command in its own terminal, from this folder, in this order:

```bash
ollama serve
.venv/bin/python -m app_server.main
.venv/bin/python -m mcp_server.server
.venv/bin/python -m copilot.main
cd frontend && npm run dev
```

Open http://127.0.0.1:5173

## Try

- Click a sample question in the chat, or type your own. Switch between **Gemini** and **Local SLM** to compare the two hosts.
- Pick an application, upload one of the sample PDFs and submit it.
- Try the REST API at http://127.0.0.1:8001/docs.
