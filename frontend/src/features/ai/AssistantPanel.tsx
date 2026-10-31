import { useState, type FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { apiRequest } from "../../api/client";

type ChatMessage = { role: "user" | "assistant"; content: string };
type ChatReply = { answer: string; thread_id?: string; proposals?: { id: string; title: string; description: string }[] };

function AssistantChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([{ role: "assistant", content: "Hi, I’m Revo’s assistant. Ask about billing, invoices, subscriptions, or revenue." }]);
  const [message, setMessage] = useState(""); const [threadId, setThreadId] = useState<string>();
  const chat = useMutation({ mutationFn: (text: string) => apiRequest<ChatReply>("/ai/chat", { method: "POST", body: JSON.stringify({ message: text, ...(threadId ? { thread_id: threadId } : {}) }) }), onSuccess: (reply) => { setThreadId(reply.thread_id); setMessages((current) => [...current, { role: "assistant", content: reply.answer }]); } });
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const text = message.trim(); if (!text || chat.isPending) return;
    setMessages((current) => [...current, { role: "user", content: text }]); setMessage(""); chat.mutate(text);
  }
  return <div className="flex min-h-0 flex-1 flex-col">
    <div className="flex-1 space-y-3 overflow-y-auto p-4" aria-live="polite">{messages.map((item, index) => <div key={`${item.role}-${index}`} className={`max-w-[90%] rounded-2xl px-3.5 py-2.5 text-sm ${item.role === "user" ? "ml-auto bg-indigo-600 text-white" : "bg-slate-100 text-slate-700"}`}><p className="mb-1 text-[10px] font-semibold uppercase tracking-wide opacity-70">{item.role === "user" ? "You" : "Revo assistant"}</p>{item.content}</div>)}{chat.isPending && <p className="text-xs text-slate-500" role="status">Thinking…</p>}{chat.error && <p role="alert" className="rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{chat.error instanceof Error ? chat.error.message : "The assistant is unavailable."}</p>}</div>
    {import.meta.env.VITE_USE_MOCKS === "true" && <p className="mx-4 mb-2 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">Demo response mode. No action is taken from a chat message.</p>}
    <form onSubmit={submit} className="border-t border-slate-200 p-3"><label className="sr-only" htmlFor="assistant-message">Message the assistant</label><div className="flex items-end gap-2"><textarea id="assistant-message" value={message} onChange={(event) => setMessage(event.target.value)} maxLength={2000} rows={2} placeholder="Ask a question…" className="min-h-12 flex-1 resize-none rounded-xl border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none" /><button disabled={!message.trim() || chat.isPending} className="rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50">Send</button></div></form>
  </div>;
}

export function AssistantPanel({ open, onClose }: { open: boolean; onClose: () => void }) {
  if (!open) return null;
  return <div className="fixed inset-0 z-50 bg-slate-950/25" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <aside role="dialog" aria-modal="true" aria-labelledby="assistant-title" className="absolute inset-y-0 right-0 flex w-full max-w-md flex-col bg-white shadow-2xl">
      <header className="flex items-center justify-between border-b border-slate-200 px-5 py-4"><div><h2 id="assistant-title" className="font-semibold text-slate-900">Revo assistant</h2><p className="mt-0.5 text-xs text-slate-500">Ask a question about your Revo workspace</p></div><button onClick={onClose} aria-label="Close assistant" className="rounded-lg px-3 py-2 text-slate-500 hover:bg-slate-100">×</button></header>
      <AssistantChat />
    </aside>
  </div>;
}

export function AssistantPage() {
  return <section className="mx-auto flex h-[calc(100vh-11rem)] max-w-4xl flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm"><header className="border-b border-slate-200 px-5 py-4"><h1 className="font-semibold">Revo assistant</h1><p className="mt-1 text-sm text-slate-500">Answers depend on the signed-in user’s permissions and available tools.</p></header><AssistantChat /></section>;
}
