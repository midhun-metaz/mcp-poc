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

// Apply one streamed event to the answer being built (the last message).
function applyEvent(message, event) {
  if (event.type === "context") return { ...message, resources: event.resources };
  if (event.type === "tool_started") return { ...message, steps: [...message.steps, { ...event, running: true }] };
  // Tools run one at a time, so the finished tool is the last one started.
  if (event.type === "tool_finished") return { ...message, steps: [...message.steps.slice(0, -1), event] };
  if (event.type === "answer") return { ...message, text: event.text };
  if (event.type === "suggestions") return { ...message, suggestions: event.questions };
  return { ...message, text: `Error: ${event.message}` };
}

// application is the one open in the UI. The copilot reads it as an MCP resource with every question.
export default function ChatPanel({ application, onReply, onClearApplication }) {
  const [messages, setMessages] = useState([]);
  const [prompts, setPrompts] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [conversationId, setConversationId] = useState(() => crypto.randomUUID());
  const bottom = useRef(null);

  // Keep the newest message in view. (Braces: an effect may only return a clean-up function.)
  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  // The MCP server's prompts become one-click actions for the open application.
  useEffect(() => {
    api.listPrompts().then((list) => Array.isArray(list) && setPrompts(list));
  }, []);

  async function send(text, prompt) {
    if (!text.trim() || busy) return;
    // Add the question and an empty answer that fills in as events stream in.
    setMessages((current) => [...current, { role: "user", text }, { role: "assistant", text: "", steps: [] }]);
    setInput("");
    setBusy(true);
    await api.chat(conversationId, text, { applicationId: application?.application_id, prompt }, (event) =>
      setMessages((current) => [...current.slice(0, -1), applyEvent(current.at(-1), event)]),
    );
    setBusy(false);
    onReply(); // the copilot may have created an application or added a document
  }

  function newChat() {
    setMessages([]);
    setConversationId(crypto.randomUUID());
  }

  // Follow-up questions the copilot suggested for its latest answer.
  const followUps = busy ? [] : (messages.at(-1)?.suggestions ?? []);

  const suggestions = SAMPLE_QUESTIONS.map((question) => (
    <button key={question} className="chip" disabled={busy} onClick={() => send(question)}>
      <span>{question}</span>
      <span className="chip-arrow" aria-hidden="true">
        →
      </span>
    </button>
  ));

  return (
    <section className="panel chat">
      <div className="chat-head">
        <span className="copilot-avatar">✦</span>
        <div className="chat-title">
          <h2>Copilot</h2>
          <p className="muted">
            <span className={busy ? "status-dot busy" : "status-dot"} />
            {busy ? "Working…" : "Online · MCP tools"}
          </p>
        </div>
        {messages.length > 0 && (
          <button className="ghost" disabled={busy} onClick={newChat}>
            + New chat
          </button>
        )}
      </div>

      <div className="messages">
        {messages.length === 0 && (
          <div className="welcome">
            <span className="copilot-avatar large">✦</span>
            <h3>How can I help with your loans?</h3>
            <p className="muted">
              {application ? "I can help with the selected application, look up others, create drafts and read documents you paste." : "Look up any application, create a draft or ask a question. No applicant selection needed."}
            </p>
            <p className="welcome-label">Try asking</p>
            <div className="chips">{suggestions}</div>
          </div>
        )}
        {messages.map((message, index) => (
          <Message key={index} message={message} />
        ))}
        {followUps.length > 0 && (
          <div className="follow-ups">
            {followUps.map((question) => (
              <button key={question} className="chip" onClick={() => send(question)}>
                {question}
              </button>
            ))}
          </div>
        )}
        <div ref={bottom} />
      </div>

      <form
        className="composer"
        onSubmit={(event) => {
          event.preventDefault();
          send(input);
        }}
      >
        {application && (
          <div className="context-bar">
            <span
              className="context-pill"
              title={`Shared with the copilot as MCP resource los://applications/${application.application_id}`}
            >
              {application.application_id} · {application.full_name}
            </span>
            <button type="button" className="context-clear" disabled={busy}
              title="Clear the selection and start a fresh chat without previous applicant context"
              onClick={() => { newChat(); onClearApplication(); }}>
              × Clear & start fresh
            </button>
            {prompts.map((prompt) => (
              <button
                key={prompt.name}
                type="button"
                className="prompt-action"
                title={`MCP prompt: ${prompt.description}`}
                disabled={busy}
                onClick={() => send(`${prompt.title} · ${application.application_id}`, prompt.name)}
              >
                {prompt.title}
              </button>
            ))}
          </div>
        )}
        {!application && <p className="general-chat-label"><span aria-hidden="true">✦</span> General chat <span>· No applicant attached</span></p>}
        <div className="composer-box">
          <textarea
            rows={1}
            placeholder={application ? "Ask about this application…" : "Ask Copilot anything about your loans…"}
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                send(input);
              }
            }}
          />
          <button className="send" aria-label="Send" disabled={busy || !input.trim()}>
            ↑
          </button>
        </div>
        <p className="composer-hint">
          <kbd>Enter</kbd> to send · <kbd>Shift</kbd>+<kbd>Enter</kbd> for a new line
        </p>
      </form>
    </section>
  );
}

function Message({ message }) {
  if (message.role === "user") {
    return (
      <div className="message user">
        <div className="bubble">{message.text}</div>
      </div>
    );
  }

  return (
    <div className="message assistant">
      <span className="copilot-avatar small">✦</span>
      <div className="message-body">
        {message.resources && (
          <p className="resources">
            Read resources{" "}
            {message.resources.map((uri) => (
              <code key={uri}>{uri}</code>
            ))}
          </p>
        )}
        {message.steps.map((step, index) => (
          <details key={index} className={step.running ? "step running" : step.error ? "step failed" : "step"}>
            <summary>
              <span className="step-icon">{step.running ? <span className="spinner" /> : step.error ? "!" : "✓"}</span>
              <span>{step.running ? `${TOOL_LABELS[step.tool] ?? "Running"}…` : step.error ? "Tool failed" : "Used tool"}</span>
              <code>{step.tool}</code>
            </summary>
            <pre>{JSON.stringify({ args: step.args, result: step.result, error: step.error }, null, 2)}</pre>
          </details>
        ))}
        {message.text ? (
          <div className="bubble">
            <Markdown>{message.text}</Markdown>
          </div>
        ) : (
          <div className="bubble typing" aria-label="Copilot is working on your request">
            <span />
            <span />
            <span />
          </div>
        )}
      </div>
    </div>
  );
}
