import { useState } from "react";
import { AlertCircle, CheckCircle2, HelpCircle, Loader2, MailWarning, RotateCcw, ShieldCheck, XCircle } from "lucide-react";
import { toast } from "sonner";
import { api, formatApiErrorDetail } from "@/lib/api";

export const DeliveryStatus = ({ m, onRetry, onReport }) => {
  const d = m.delivery;
  if (!d) return null;
  if (d.state === "retrying")
    return (
      <p className="mt-1.5 text-[11px] text-amber-600 flex items-center gap-1.5" data-testid={`delivery-retrying-${m.id}`}>
        <Loader2 className="animate-spin" size={11} /> No se pudo enviar. Reintentando ({d.attempt}/{d.max})…
      </p>
    );
  return (
    <div className="mt-1.5 flex flex-col items-end gap-1.5" data-testid={`delivery-failed-${m.id}`}>
      <p className="text-[11px] text-red-600 flex items-center gap-1.5 text-right">
        <AlertCircle size={11} className="shrink-0" /> {d.canRetry ? "No se pudo enviar el mensaje." : d.error}
      </p>
      {d.canRetry && (
        <div className="flex flex-wrap justify-end gap-2">
          <button onClick={() => onRetry(m)} data-testid={`delivery-retry-btn-${m.id}`} className="inline-flex items-center gap-1.5 border border-red-300 hover:bg-red-50 text-red-700 font-semibold px-3 py-1 rounded-full text-[11px] transition-colors">
            <RotateCcw size={11} /> Reintentar
          </button>
          {d.canReport && (
            <button onClick={() => onReport(m)} disabled={d.reported} data-testid={`delivery-report-btn-${m.id}`} className="inline-flex items-center gap-1.5 bg-[#0F172A] hover:bg-slate-800 disabled:opacity-50 text-white font-semibold px-3 py-1 rounded-full text-[11px] transition-colors">
              <MailWarning size={11} /> {d.reported ? "Falla reportada" : "Reportar la falla"}
            </button>
          )}
        </div>
      )}
    </div>
  );
};

const STATE = {
  verificada: { label: "Verificada", icon: CheckCircle2, cls: "text-emerald-700 bg-emerald-50 border-emerald-200" },
  dudosa: { label: "Revisar", icon: HelpCircle, cls: "text-amber-700 bg-amber-50 border-amber-200" },
  no_encontrada: { label: "No encontrada", icon: XCircle, cls: "text-red-700 bg-red-50 border-red-200" },
};

export const CitationCheck = ({ caseId, message }) => {
  const [result, setResult] = useState(message.citations || null);
  const [loading, setLoading] = useState(false);

  const verify = async () => {
    setLoading(true);
    try {
      const { data } = await api.post(`/cases/${caseId}/messages/${message.id}/verify-citations`);
      setResult(data);
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail));
    } finally {
      setLoading(false);
    }
  };

  if (!result)
    return (
      <button onClick={verify} disabled={loading} data-testid={`verify-citations-btn-${message.id}`} title="Busca en fuentes públicas las normas citadas. No descuenta mensajes." className="inline-flex items-center gap-1.5 border border-slate-300 hover:border-emerald-600 hover:text-emerald-700 disabled:opacity-60 text-slate-500 font-semibold px-3 py-1.5 rounded-full text-[11px] transition-colors">
        {loading ? <Loader2 className="animate-spin" size={11} /> : <ShieldCheck size={11} />}
        {loading ? "Verificando citas…" : "Verificar citas"}
      </button>
    );

  return (
    <div className="w-full mt-2 border border-slate-200 rounded-lg p-3 bg-slate-50" data-testid={`citations-result-${message.id}`}>
      <p className="text-[11px] font-semibold text-slate-700 flex items-center gap-1.5">
        <ShieldCheck size={12} className="text-emerald-600" /> Verificación de citas legales
      </p>
      {result.items.length === 0 ? (
        <p className="text-[11px] text-slate-500 mt-2">Esta respuesta no contiene citas legales concretas.</p>
      ) : (
        <ul className="mt-2 space-y-2">
          {result.items.map((c, i) => {
            const meta = STATE[c.estado] || STATE.dudosa;
            return (
              <li key={i} className="text-[11px] leading-relaxed" data-testid={`citation-item-${message.id}-${i}`}>
                <span className={`inline-flex items-center gap-1 border rounded-full px-2 py-0.5 font-semibold mr-2 ${meta.cls}`}>
                  <meta.icon size={10} /> {meta.label}
                </span>
                <b className="text-slate-800">{c.cita}</b>
                {c.detalle && <span className="text-slate-600"> — {c.detalle}</span>}
                {c.fuente && (
                  <a href={c.fuente} target="_blank" rel="noopener noreferrer" className="ml-1 text-[#0284C7] underline">ver fuente</a>
                )}
              </li>
            );
          })}
        </ul>
      )}
      <p className="text-[10px] text-slate-400 mt-2">Comprobación automática con búsqueda en fuentes públicas. Confirma siempre en la fuente oficial antes de presentar un escrito.</p>
    </div>
  );
};
