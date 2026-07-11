import { useEffect, useRef, useState } from "react";
import { chatApi, conversationsApi, pdfApi, voiceApi } from "../api/endpoints";
import type { ChatTurn, Citation, ConversationSummary } from "../api/types";
import { useMicRecorder } from "../voice/useMicRecorder";
import { speak } from "../voice/speak";

interface Message extends ChatTurn {
  citations?: Citation[];
  detectedLanguage?: "en" | "hi" | "kn";
}

const LANG_LABEL: Record<string, string> = { en: "EN", hi: "हि", kn: "ಕ" };

export default function ChatPage() {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const mic = useMicRecorder();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    conversationsApi.list().then(setConversations).catch(() => undefined);
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function newConversation() {
    const conv = await conversationsApi.create();
    setConversationId(conv.id);
    setMessages([]);
    setConversations((prev) => [
      { id: conv.id, title: null, created_at: conv.created_at, updated_at: conv.updated_at, turn_count: 0 },
      ...prev,
    ]);
  }

  async function openConversation(id: string) {
    const conv = await conversationsApi.get(id);
    setConversationId(conv.id);
    setMessages(conv.turns);
  }

  async function send() {
    const query = draft.trim();
    if (!query || sending) return;
    setSending(true);
    setDraft("");
    setMessages((prev) => [...prev, { role: "user", content: query }]);
    try {
      const res = await chatApi.send({
        query,
        conversation_id: conversationId ?? undefined,
        history: conversationId ? undefined : messages,
      });
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: res.answer,
          citations: res.citations,
          detectedLanguage: res.detected_language,
        },
      ]);
      if (res.conversation_id && !conversationId) {
        setConversationId(res.conversation_id);
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Error: ${err instanceof Error ? err.message : "unknown"}` },
      ]);
    } finally {
      setSending(false);
    }
  }

  async function toggleMic() {
    if (mic.recording) {
      setTranscribing(true);
      try {
        const blob = await mic.stop();
        const result = await voiceApi.transcribe(blob);
        setDraft((prev) => (prev ? `${prev} ${result.text}` : result.text));
      } catch (err) {
        // surface error in draft so the user can see it
        setDraft(err instanceof Error ? `[mic error: ${err.message}]` : "[mic error]");
      } finally {
        setTranscribing(false);
      }
    } else {
      void mic.start();
    }
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-[16rem_1fr] gap-4">
      <aside className="bg-card shadow rounded p-3">
        <button
          onClick={newConversation}
          className="w-full text-sm bg-brand-600 text-white rounded px-3 py-1.5 hover:bg-brand-700"
        >
          New conversation
        </button>
        <ul className="mt-3 space-y-1 text-sm">
          {conversations.map((c) => (
            <li key={c.id} className="flex items-center gap-1">
              <button
                onClick={() => openConversation(c.id)}
                className={`flex-1 text-left rounded px-2 py-1 truncate ${
                  conversationId === c.id ? "bg-brand-100 text-brand-700" : "hover:bg-surface-2"
                }`}
              >
                {c.title || "Untitled"}
              </button>
              <a
                href={pdfApi.exportConversation(c.id)}
                target="_blank"
                rel="noreferrer"
                title="Export as PDF"
                className="text-subtle hover:text-brand-600 px-1"
              >
                ⇣
              </a>
            </li>
          ))}
          {conversations.length === 0 && (
            <li className="text-xs text-subtle px-1">No conversations yet.</li>
          )}
        </ul>
      </aside>

      <section className="bg-card shadow rounded flex flex-col h-[70vh]">
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {messages.length === 0 && (
            <p className="text-sm text-subtle">
              Ask about cases, locality trends, or specific FIRs. English, हिन्दी, or ಕನ್ನಡ.
            </p>
          )}
          {messages.map((m, i) => (
            <Bubble key={i} message={m} />
          ))}
          <div ref={bottomRef} />
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void send();
          }}
          className="border-t p-3 flex gap-2 items-center"
        >
          <button
            type="button"
            onClick={toggleMic}
            disabled={transcribing}
            className={`rounded px-2 py-1.5 text-sm border ${
              mic.recording ? "bg-rose-600 text-white border-rose-600" : "border-line hover:bg-surface-2"
            }`}
            title={mic.recording ? "Stop recording" : "Start voice input"}
          >
            {transcribing ? "…" : mic.recording ? "■" : "🎤"}
          </button>
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Any thefts in HSR Layout? / एचएसआर लेआउट में चोरी?"
            className="flex-1 rounded border-line border px-3 py-1.5 text-sm"
          />
          <button
            disabled={sending || !draft.trim()}
            className="bg-brand-600 text-white rounded px-3 py-1.5 text-sm hover:bg-brand-700 disabled:opacity-50"
          >
            {sending ? "…" : "Send"}
          </button>
        </form>
      </section>
    </div>
  );
}

function Bubble({ message }: { message: Message }) {
  const isUser = message.role === "user";
  return (
    <div className={isUser ? "flex justify-end" : ""}>
      <div
        className={`max-w-[80%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap ${
          isUser ? "bg-brand-600 text-white" : "bg-surface-2 text-ink"
        }`}
      >
        {message.content}
        <div className="mt-2 flex flex-wrap items-center gap-1">
          {message.detectedLanguage && message.detectedLanguage !== "en" && (
            <span className="text-xs rounded bg-card/70 text-brand-700 px-1.5 py-0.5">
              {LANG_LABEL[message.detectedLanguage]}
            </span>
          )}
          {!isUser && (
            <button
              onClick={() => void speak(message.content, message.detectedLanguage || "en")}
              className="text-xs rounded bg-card/70 text-brand-700 px-1.5 py-0.5 hover:underline"
              title="Read aloud"
            >
              🔊
            </button>
          )}
          {message.citations?.map((c) => (
            <a
              key={c.case_id}
              href={`/cases/${c.case_id}`}
              className="text-xs rounded bg-card/80 text-brand-700 px-1.5 py-0.5 hover:underline"
            >
              {c.case_id}
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}
