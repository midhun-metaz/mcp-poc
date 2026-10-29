import { useEffect, useRef, useState } from "react";
import Markdown from "react-markdown";
import * as api from "../api.js";
import { SAMPLE_QUESTIONS } from "../samples.js";

// What each MCP tool is doing, shown while it runs.
const TOOL_LABELS = {
  list_applications: "Listing applications",
  get_application: "Looking up the application",
  create_application: "Creating a draft application",
  submit_document: "Reading the document with the local model",
};

// The two MCP hosts. Both call the same MCP tools; only the model that chooses them differs.
const HOSTS = {
  gemini: { label: "Gemini", about: "Gemini (cloud LLM) answers by calling MCP tools", waiting: "Gemini is choosing MCP tools…" },
  local: {
    label: "Local SLM",
    about: "A small model on this computer answers with the same MCP tools",
    waiting: "The local model is thinking and choosing MCP tools… (slow on a CPU)",
  },
};

// Apply one streamed event to the answer being built (the last message).
function applyEvent(message, event) {
  if (event.type === "tool_started") return { ...message, steps: [...message.steps, { ...event, running: true }] };
  // Tools run one at a time, so the finished tool is the last one started.
  if (event.type === "tool_finished") return { ...message, steps: [...message.steps.slice(0, -1), event] };
  if (event.type === "answer") return { ...message, text: event.text, model: event.model };
  return { ...message, text: `Error: ${event.message}` };
}

export default function ChatPanel({ onReply }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [conversationId, setConversationId] = useState(() => crypto.randomUUID());
  const [host, setHost] = useState("gemini");
  const bottom = useRef(null);

  // Keep the newest message in view. (Braces: an effect may only return a clean-up function.)
  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  async function send(text) {
    if (!text.trim() || busy) return;
    // Add the question and an empty answer that fills in as events stream in.
    setMessages((current) => [...current, { role: "user", text }, { role: "assistant", text: "", steps: [], host }]);
    setInput("");
    setBusy(true);
    await api.chat(conversationId, host, text, (event) =>
      setMessages((current) => [...current.slice(0, -1), applyEvent(current.at(-1), event)]),
    );
    setBusy(false);
    onReply(); // the copilot may have created an application or added a document
  }

  function newChat() {
    setMessages([]);
    setConversationId(crypto.randomUUID());
  }

  // Each host keeps its own conversation, so switching starts a new chat.
  function switchHost(newHost) {
    setHost(newHost);
    newChat();
  }

  const suggestions = SAMPLE_QUESTIONS.map((question) => (
    <button key={question} className="chip" disabled={busy} onClick={() => send(question)}>
      {question}
    </button>
  ));

  return (
    <section className="panel chat">
      <div className="chat-head">
        <div>
          <h2>Copilot</h2>
          <p className="muted">{HOSTS[host].about}</p>
        </div>
        <div className="chat-actions">
          <div className="switch">
            {Object.entries(HOSTS).map(([key, { label }]) => (
              <button key={key} className={host === key ? "active" : ""} disabled={busy} onClick={() => switchHost(key)}>
                {label}
              </button>
            ))}
          </div>
          {messages.length > 0 && <button onClick={newChat}>New chat</button>}
        </div>
      </div>

      <div className="messages">
        {messages.length === 0 && (
          <div className="welcome">
            <p>
              <strong>Ask about loan applications.</strong>
            </p>
            <p className="muted">I can look up applications, create drafts and read documents you paste.</p>
            <div className="chips">{suggestions}</div>
          </div>
        )}
        {messages.map((message, index) => (
          <Message key={index} message={message} />
        ))}
        <div ref={bottom} />
      </div>

      {messages.length > 0 && <div className="chips scroll">{suggestions}</div>}

      <form
        className="composer"
        onSubmit={(event) => {
          event.preventDefault();
          send(input);
        }}
      >
        <textarea
          rows={2}
          placeholder="Ask the copilot… (Enter to send, Shift+Enter for a new line)"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              send(input);
            }
          }}
        />
        <button className="primary" disabled={busy || !input.trim()}>
          Send
        </button>
      </form>
    </section>
  );
}

function Message({ message }) {
  return (
    <div className={`message ${message.role}`}>
      {message.steps?.map((step, index) => (
        <details key={index} className={step.running ? "step running" : step.error ? "step failed" : "step"}>
          <summary>
            {step.running ? `⏳ ${TOOL_LABELS[step.tool] ?? "Running"}…` : step.error ? "⚠️ MCP tool failed" : "✓ MCP tool"}{" "}
            · <code>{step.tool}</code>
          </summary>
          <pre>{JSON.stringify({ args: step.args, result: step.result, error: step.error }, null, 2)}</pre>
        </details>
      ))}
      {message.text ? (
        <div className="bubble">{message.role === "assistant" ? <Markdown>{message.text}</Markdown> : message.text}</div>
      ) : (
        <p className="thinking">{HOSTS[message.host].waiting}</p>
      )}
      {message.model && <p className="answered-by">Answered by {message.model}</p>}
    </div>
  );
}
