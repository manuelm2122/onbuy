import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { MessagesSquare, X } from "lucide-react";
import { api } from "@/lib/api";
import { useAssistantChat } from "@/hooks/useAssistantChat";
import { ChatPanel } from "@/components/ChatPanel";

const TEASER_KEY = "obs-assistant-teaser-seen";

export const ChatWidget = () => {
  const { pathname } = useLocation();
  const chat = useAssistantChat();
  const [enabled, setEnabled] = useState(false);
  const [open, setOpen] = useState(false);
  const [teaser, setTeaser] = useState(false);

  useEffect(() => {
    api.get("/public/settings").then(({ data }) => setEnabled(!!data.assistant_enabled)).catch(() => {});
  }, []);

  useEffect(() => {
    if (!enabled || localStorage.getItem(TEASER_KEY)) return undefined;
    const timer = setTimeout(() => setTeaser(true), 3500);
    return () => clearTimeout(timer);
  }, [enabled]);

  const dismissTeaser = () => {
    setTeaser(false);
    localStorage.setItem(TEASER_KEY, "1");
  };

  const openChat = () => {
    dismissTeaser();
    setOpen(true);
  };

  if (!enabled || pathname.startsWith("/panel") || pathname === "/acceso") return null;

  return (
    <>
      <AnimatePresence>{open && <ChatPanel chat={chat} onClose={() => setOpen(false)} />}</AnimatePresence>
      {!open && (
        <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-3" data-testid="chat-widget">
          <AnimatePresence>
            {teaser && (
              <motion.div
                initial={{ opacity: 0, y: 10, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 10, scale: 0.95 }}
                transition={{ duration: 0.25 }}
                data-testid="chat-teaser"
                className="relative max-w-[240px] bg-white text-[#0F172A] rounded-2xl rounded-br-md shadow-xl shadow-black/30 border border-slate-200 pl-4 pr-9 py-3"
              >
                <button onClick={openChat} className="text-left text-sm leading-snug" data-testid="chat-teaser-open">
                  <b className="font-heading">¿Tienes alguna duda?</b>
                  <span className="block text-slate-600 text-xs mt-0.5">Pregúntame sobre nuestros servicios, respondo al instante.</span>
                </button>
                <button onClick={dismissTeaser} aria-label="Cerrar aviso" data-testid="chat-teaser-close" className="absolute top-2 right-2 text-slate-400 hover:text-slate-700 transition-colors">
                  <X size={14} />
                </button>
              </motion.div>
            )}
          </AnimatePresence>
          <motion.button
            onClick={openChat}
            initial={{ opacity: 0, scale: 0.6 }}
            animate={{ opacity: 1, scale: 1 }}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            aria-label="Abrir chat"
            data-testid="chat-launcher-btn"
            className="relative h-14 pl-4 pr-5 rounded-full bg-[#0284C7] hover:bg-[#0EA5E9] text-white font-semibold text-sm flex items-center gap-2.5 shadow-xl shadow-sky-900/50 ring-1 ring-white/20 transition-colors"
          >
            <span className="absolute inset-0 rounded-full bg-[#0EA5E9] opacity-40 animate-ping [animation-duration:2.4s] pointer-events-none" />
            <span className="relative w-8 h-8 rounded-full bg-white/15 flex items-center justify-center">
              <MessagesSquare size={18} />
            </span>
            <span className="relative">Chatea con nosotros</span>
          </motion.button>
        </div>
      )}
    </>
  );
};
