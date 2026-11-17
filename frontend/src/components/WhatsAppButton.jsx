import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { MessageCircle, X, Send } from "lucide-react";
import { api } from "@/lib/api";
import { SERVICES } from "@/constants/services";

export const WhatsAppButton = ({ defaultService = "auditorias" }) => {
  const [cfg, setCfg] = useState(null);
  const [open, setOpen] = useState(false);
  const [service, setService] = useState(defaultService);

  useEffect(() => {
    api.get("/public/settings").then(({ data }) => setCfg(data)).catch(() => {});
  }, []);

  if (!cfg?.whatsapp_enabled || !cfg.whatsapp_number) return null;

  const title = SERVICES.find((s) => s.key === service)?.title || "";
  const text = (cfg.whatsapp_message || "Hola, estoy interesado en: {servicio}").replace("{servicio}", title);
  const href = `https://wa.me/${cfg.whatsapp_number}?text=${encodeURIComponent(text)}`;

  return (
    <div className="fixed bottom-24 right-6 z-50 flex flex-col items-end gap-3" data-testid="whatsapp-widget">
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 12, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 12, scale: 0.96 }}
            transition={{ duration: 0.18 }}
            className="w-72 bg-white text-[#0F172A] rounded-xl shadow-2xl shadow-black/40 overflow-hidden border border-slate-200"
            data-testid="whatsapp-panel"
          >
            <div className="bg-[#128C7E] text-white px-4 py-3">
              <p className="font-heading font-bold text-sm">Escríbenos por WhatsApp</p>
              <p className="text-[11px] text-emerald-100 mt-0.5">Te respondemos lo antes posible</p>
            </div>
            <div className="p-4">
              <label className="text-[10px] tracking-[0.15em] uppercase text-slate-500 font-semibold">
                ¿Qué servicio te interesa?
              </label>
              <select
                value={service}
                onChange={(e) => setService(e.target.value)}
                data-testid="whatsapp-service-select"
                className="mt-1.5 w-full border border-slate-300 focus:border-[#128C7E] outline-none px-3 py-2.5 text-sm bg-white text-[#0F172A] rounded"
              >
                {SERVICES.map((s) => (
                  <option key={s.key} value={s.key}>{s.title}</option>
                ))}
              </select>
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                data-testid="whatsapp-send-link"
                className="mt-4 w-full inline-flex items-center justify-center gap-2 bg-[#25D366] hover:bg-[#1EBE5A] text-white font-semibold py-2.5 rounded-full text-sm transition-colors"
              >
                <Send size={15} /> Abrir chat
              </a>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
      <button
        onClick={() => setOpen((v) => !v)}
        aria-label="WhatsApp"
        data-testid="whatsapp-toggle-btn"
        className="w-14 h-14 rounded-full bg-[#25D366] hover:bg-[#1EBE5A] text-white flex items-center justify-center shadow-xl shadow-black/40 transition-[background-color,transform] hover:scale-105"
      >
        {open ? <X size={24} /> : <MessageCircle size={26} />}
      </button>
    </div>
  );
};
