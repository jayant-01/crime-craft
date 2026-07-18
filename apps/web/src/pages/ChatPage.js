import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useRef, useState } from "react";
import { chatApi, conversationsApi, pdfApi, voiceApi } from "../api/endpoints";
import { useMicRecorder } from "../voice/useMicRecorder";
import { speak } from "../voice/speak";
const LANG_LABEL = { en: "EN", hi: "हि", kn: "ಕ" };
export default function ChatPage() {
    const [conversations, setConversations] = useState([]);
    const [conversationId, setConversationId] = useState(null);
    const [messages, setMessages] = useState([]);
    const [draft, setDraft] = useState("");
    const [sending, setSending] = useState(false);
    const [transcribing, setTranscribing] = useState(false);
    const mic = useMicRecorder();
    const bottomRef = useRef(null);
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
    async function openConversation(id) {
        const conv = await conversationsApi.get(id);
        setConversationId(conv.id);
        setMessages(conv.turns);
    }
    async function send() {
        const query = draft.trim();
        if (!query || sending)
            return;
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
        }
        catch (err) {
            setMessages((prev) => [
                ...prev,
                { role: "assistant", content: `Error: ${err instanceof Error ? err.message : "unknown"}` },
            ]);
        }
        finally {
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
            }
            catch (err) {
                // surface error in draft so the user can see it
                setDraft(err instanceof Error ? `[mic error: ${err.message}]` : "[mic error]");
            }
            finally {
                setTranscribing(false);
            }
        }
        else {
            void mic.start();
        }
    }
    return (_jsxs("div", { className: "grid grid-cols-1 md:grid-cols-[16rem_1fr] gap-4", children: [_jsxs("aside", { className: "bg-card shadow rounded p-3", children: [_jsx("button", { onClick: newConversation, className: "w-full text-sm bg-brand-600 text-white rounded px-3 py-1.5 hover:bg-brand-700", children: "New conversation" }), _jsxs("ul", { className: "mt-3 space-y-1 text-sm", children: [conversations.map((c) => (_jsxs("li", { className: "flex items-center gap-1", children: [_jsx("button", { onClick: () => openConversation(c.id), className: `flex-1 text-left rounded px-2 py-1 truncate ${conversationId === c.id ? "bg-brand-100 text-brand-700" : "hover:bg-surface-2"}`, children: c.title || "Untitled" }), _jsx("a", { href: pdfApi.exportConversation(c.id), target: "_blank", rel: "noreferrer", title: "Export as PDF", className: "text-subtle hover:text-brand-600 px-1", children: "\u21E3" })] }, c.id))), conversations.length === 0 && (_jsx("li", { className: "text-xs text-subtle px-1", children: "No conversations yet." }))] })] }), _jsxs("section", { className: "bg-card shadow rounded flex flex-col h-[70vh]", children: [_jsxs("div", { className: "flex-1 overflow-y-auto p-4 space-y-3", children: [messages.length === 0 && (_jsx("p", { className: "text-sm text-subtle", children: "Ask about cases, locality trends, or specific FIRs. English, \u0939\u093F\u0928\u094D\u0926\u0940, or \u0C95\u0CA8\u0CCD\u0CA8\u0CA1." })), messages.map((m, i) => (_jsx(Bubble, { message: m }, i))), _jsx("div", { ref: bottomRef })] }), _jsxs("form", { onSubmit: (e) => {
                            e.preventDefault();
                            void send();
                        }, className: "border-t p-3 flex gap-2 items-center", children: [_jsx("button", { type: "button", onClick: toggleMic, disabled: transcribing, className: `rounded px-2 py-1.5 text-sm border ${mic.recording ? "bg-rose-600 text-white border-rose-600" : "border-line hover:bg-surface-2"}`, title: mic.recording ? "Stop recording" : "Start voice input", children: transcribing ? "…" : mic.recording ? "■" : "🎤" }), _jsx("input", { value: draft, onChange: (e) => setDraft(e.target.value), placeholder: "Any thefts in HSR Layout? / \u090F\u091A\u090F\u0938\u0906\u0930 \u0932\u0947\u0906\u0909\u091F \u092E\u0947\u0902 \u091A\u094B\u0930\u0940?", className: "flex-1 rounded border-line border px-3 py-1.5 text-sm" }), _jsx("button", { disabled: sending || !draft.trim(), className: "bg-brand-600 text-white rounded px-3 py-1.5 text-sm hover:bg-brand-700 disabled:opacity-50", children: sending ? "…" : "Send" })] })] })] }));
}
function Bubble({ message }) {
    const isUser = message.role === "user";
    return (_jsx("div", { className: isUser ? "flex justify-end" : "", children: _jsxs("div", { className: `max-w-[80%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap ${isUser ? "bg-brand-600 text-white" : "bg-surface-2 text-ink"}`, children: [message.content, _jsxs("div", { className: "mt-2 flex flex-wrap items-center gap-1", children: [message.detectedLanguage && message.detectedLanguage !== "en" && (_jsx("span", { className: "text-xs rounded bg-card/70 text-brand-700 px-1.5 py-0.5", children: LANG_LABEL[message.detectedLanguage] })), !isUser && (_jsx("button", { onClick: () => void speak(message.content, message.detectedLanguage || "en"), className: "text-xs rounded bg-card/70 text-brand-700 px-1.5 py-0.5 hover:underline", title: "Read aloud", children: "\uD83D\uDD0A" })), message.citations?.map((c) => (_jsx("a", { href: `/cases/${c.case_id}`, className: "text-xs rounded bg-card/80 text-brand-700 px-1.5 py-0.5 hover:underline", children: c.case_id }, c.case_id)))] })] }) }));
}
