// Calls to the Python servers. Vite forwards /api to the app server and /chat to the copilot chat API.

async function request(method, path, body) {
  const response = await fetch(path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body && JSON.stringify(body),
  });
  return readJson(response);
}

// A server that is down or crashed does not answer with JSON.
function readJson(response) {
  return response.json().catch(() => ({ detail: `Server error ${response.status}. Is the server running?` }));
}

export const listApplications = () => request("GET", "/api/applications");

export const createApplication = (applicant) => request("POST", "/api/applications", applicant);

// Uploads a PDF as a form, the way a browser sends files.
export async function submitPdf(applicationId, file) {
  const form = new FormData();
  form.append("file", file);
  return readJson(await fetch(`/api/applications/${applicationId}/documents/pdf`, { method: "POST", body: form }));
}

// Streams one chat turn. The server sends one JSON line per event: tool_started, tool_finished,
// then answer or error. onEvent is called for each line as soon as it arrives.
// host is "gemini" (cloud LLM) or "local" (small model in Ollama).
export async function chat(conversationId, host, message, onEvent) {
  const response = await fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ conversation_id: conversationId, host, message }),
  });
  if (!response.ok) {
    onEvent({ type: "error", message: `Server error ${response.status}. Is the copilot chat API running?` });
    return;
  }

  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += value;
    const lines = buffer.split("\n");
    buffer = lines.pop(); // an unfinished line waits for the next chunk
    lines.filter(Boolean).forEach((line) => onEvent(JSON.parse(line)));
  }
}
