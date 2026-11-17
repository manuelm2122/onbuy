import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import { ChevronDown, RotateCcw, SendHorizontal, Sparkles } from "lucide-react";

const SUGGESTIONS = [
  "¿Qué servicios ofrecen?",
  "¿Qué incluye la asesoría legal de pago?",
  "Quiero un menú QR para mi restaurante",
  "¿Cómo contrato una auditoría?",
];

const linkClass = "text-[#0284C7] underline underline-offset-2 hover:text-[#0369A1]";

const MarkdownLink = ({ href = "", children }) => {
  const path = href.replace(/^https?:\/\/(www\.)?onbuysolutions\.com(?=\/|$)/i, "") || "/";
  return path.startsWith("/") ? (
    <Link to={path} className={linkClass}>{children}</Link>
  ) : (
    <a href={href} target="_blank" rel="noopener noreferrer" className={linkClass}>{children}</a>
  );
};

const Typing = () => (
  <span className="inline-flex gap-1 py-1.5" data-testid="chat-typing">
    {[0, 1, 2].map((i) => (
      <span key={i} className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: `${i * 0.15}s` }} />
    ))}
  </span>
);

const Bubble = ({ message, index }) => {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        data-testid={`chat-message-${index}`}
        data-role={message.role}
        className={`max-w-[85%] px-4 py-2.5 text-sm leading-relaxed break-words ${
          isUser
            ? "bg-[#0284C7] text-white rounded-2xl rounded-br-md"
            : `bg-white border rounded-2xl rounded-bl-md ${message.error ? "border-red-200 text-red-700" : "border-slate-200 text-[#0F172A]"}`
        }`}
      >
        {isUser ? message.content : message.content ? (
          <ReactMarkdown
            components={{
              a: MarkdownLink,
              p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
              ul: ({ children }) => <ul className="list-disc pl-5 mb-2 last:mb-0 space-y-1">{children}</ul>,
              ol: ({ children }) => <ol className="list-decimal pl-5 mb-2 last:mb-0 space-y-1">{children}</ol>,
            }}
          >
            {message.content}
          </ReactMarkdown>
        ) : (
          <Typing />
        )}
      </div>
    </div>
  );
};

export const ChatPanel = ({ chat, onClose }) => {
  const { messages, sending, send, reset } = chat;
  const [text, setText] = useState("");
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [messages]);

  const submit = (e) => {
    e.preventDefault();
    send(text);
    setText("");
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 24, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 24, scale: 0.96 }}
      transition={{ duration: 0.22, ease: "easeOut" }}
      style={{ transformOrigin: "bottom right" }}
      data-testid="chat-panel"
      className="fixed z-[60] inset-x-3 bottom-3 top-20 sm:inset-auto sm:bottom-6 sm:right-6 sm:w-[390px] sm:h-[600px] sm:max-h-[calc(100vh-6rem)] flex flex-col rounded-2xl overflow-hidden bg-[#F8FAFC] border border-slate-700/60 shadow-2xl shadow-black/50"
    >
      <header className="relative bg-[#020617] text-white px-5 py-4 flex items-center gap-3 border-b-2 border-[#0EA5E9]">
        <span className="relative w-10 h-10 rounded-full bg-[#0284C7] flex items-center justify-center shrink-0">
          <Sparkles size={18} />
          <span className="absolute bottom-0 right-0 w-3 h-3 rounded-full bg-emerald-400 border-2 border-[#020617]" />
        </span>
        <div className="flex-1 min-w-0">
          <p className="font-heading font-bold text-sm tracking-tight">Asistente OnBuySolutions</p>
          <p className="text-[11px] text-slate-400">En línea · responde al instante</p>
        </div>
        <button onClick={reset} disabled={sending} aria-label="Nueva conversación" title="Nueva conversación" data-testid="chat-reset-btn" className="p-2 rounded-full text-slate-400 hover:text-white hover:bg-white/10 disabled:opacity-40 transition-colors">
          <RotateCcw size={16} />
        </button>
        <button onClick={onClose} aria-label="Ocultar chat" title="Ocultar chat" data-testid="chat-close-btn" className="p-2 rounded-full text-slate-400 hover:text-white hover:bg-white/10 transition-colors">
          <ChevronDown size={20} />
        </button>
      </header>

      <div className="flex-1 overflow-y-auto px-4 py-5 space-y-3" data-testid="chat-messages">
        {messages.map((m, i) => <Bubble key={i} message={m} index={i} />)}
        {messages.length === 1 && (
          <div className="flex flex-wrap gap-2 pt-2">
            {SUGGESTIONS.map((s, i) => (
              <button key={s} onClick={() => send(s)} data-testid={`chat-suggestion-${i}`} className="text-xs text-[#0284C7] border border-[#0284C7]/40 hover:bg-[#0284C7] hover:text-white rounded-full px-3 py-1.5 transition-colors">
                {s}
              </button>
            ))}
          </div>
        )}
        <div ref={endRef} />
      </div>

      <form onSubmit={submit} className="bg-white border-t border-slate-200 p-3 flex items-center gap-2">
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          maxLength={500}
          placeholder="Escribe tu consulta…"
          aria-label="Escribe tu consulta"
          data-testid="chat-input"
          className="flex-1 bg-slate-100 text-[#0F172A] placeholder:text-slate-400 rounded-full px-4 py-2.5 text-sm outline-none focus:ring-2 focus:ring-[#0EA5E9]/50"
        />
        <button type="submit" disabled={sending || !text.trim()} aria-label="Enviar" data-testid="chat-send-btn" className="w-10 h-10 shrink-0 rounded-full bg-[#0284C7] hover:bg-[#0EA5E9] disabled:opacity-40 text-white flex items-center justify-center transition-colors">
          <SendHorizontal size={17} />
        </button>
      </form>
      <p className="bg-white text-[10px] text-slate-400 text-center pb-2 px-3">
        Asistente con IA: solo informa sobre nuestros servicios, no brinda asesoría legal.
      </p>
    </motion.div>
  );
};
