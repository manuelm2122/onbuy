import { useEffect, useState } from "react";
import { BACKEND_URL } from "@/lib/api";

const KEY = "obs-assistant-chat";
const FALLBACK = "No pude responder en este momento. Inténtalo de nuevo o escríbenos por el formulario de contacto.";
const WELCOME = {
  role: "assistant",
  content:
    "¡Hola! Soy el asistente de OnBuySolutions. Puedo contarte sobre nuestras auditorías para condominios, la asesoría legal y contable, y nuestros menús y catálogos QR. ¿En qué te ayudo?",
};

const newId = () => `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}${Math.random().toString(36).slice(2, 12)}`;
const fresh = () => ({ sessionId: newId(), messages: [WELCOME] });

const load = () => {
  try {
    const saved = JSON.parse(localStorage.getItem(KEY));
    if (saved?.sessionId && Array.isArray(saved.messages) && saved.messages.length) return saved;
  } catch {
    localStorage.removeItem(KEY);
  }
  return fresh();
};

export const useAssistantChat = () => {
  const [state, setState] = useState(load);
  const [sending, setSending] = useState(false);

  useEffect(() => {
    localStorage.setItem(KEY, JSON.stringify(state));
  }, [state]);

  const setLast = (content, error = false) =>
    setState((s) => ({ ...s, messages: [...s.messages.slice(0, -1), { role: "assistant", content, error }] }));

  const send = async (text) => {
    const message = text.trim();
    if (!message || sending) return;
    setSending(true);
    setState((s) => ({ ...s, messages: [...s.messages, { role: "user", content: message }, { role: "assistant", content: "" }] }));
    try {
      const res = await fetch(`${BACKEND_URL}/api/assistant/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: state.sessionId, message }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        setLast(typeof body.detail === "string" ? body.detail : FALLBACK, true);
        return;
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let raw = "";
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        raw += decoder.decode(value, { stream: true });
        setLast(raw.split("[ERROR_IA]")[0]);
      }
      const answer = raw.split("[ERROR_IA]")[0].trim();
      if (raw.includes("[ERROR_IA]") || !answer) setLast(answer || FALLBACK, !answer);
    } catch {
      setLast(FALLBACK, true);
    } finally {
      setSending(false);
    }
  };

  const reset = () => setState(fresh());

  return { messages: state.messages, sending, send, reset };
};
