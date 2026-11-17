import { useCallback, useEffect, useState } from "react";
import { BellRing, CalendarClock, CheckCircle2, Circle, Flag, Loader2, Plus, Sparkles, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { api, formatApiErrorDetail } from "@/lib/api";

const inputCls = "w-full border border-slate-300 focus:border-[#0284C7] outline-none px-3 py-2 text-sm transition-colors bg-white";
const EMPTY = { title: "", date: "", kind: "plazo", note: "" };
const fmt = (iso) => new Date(`${iso}T12:00:00`).toLocaleDateString("es-PE", { day: "2-digit", month: "short", year: "numeric" });
const today = () => new Date().toLocaleDateString("en-CA");

const daysLabel = (e) => {
  if (e.done) return { text: "Cumplido", cls: "text-emerald-700" };
  const diff = Math.round((new Date(`${e.date}T12:00:00`) - new Date(`${today()}T12:00:00`)) / 86400000);
  if (diff < 0) return { text: `Venció hace ${-diff} día${diff === -1 ? "" : "s"}`, cls: "text-red-600" };
  if (diff === 0) return { text: "Vence hoy", cls: "text-red-600" };
  return { text: `Faltan ${diff} día${diff === 1 ? "" : "s"}`, cls: diff <= 3 ? "text-amber-600" : "text-slate-500" };
};

export const CaseTimeline = ({ caseId, open, onOpenChange }) => {
  const [events, setEvents] = useState(null);
  const [form, setForm] = useState(EMPTY);
  const [saving, setSaving] = useState(false);
  const [suggesting, setSuggesting] = useState(false);
  const [suggestions, setSuggestions] = useState([]);

  const load = useCallback(async () => {
    try {
      const { data } = await api.get(`/cases/${caseId}/events`);
      setEvents(data);
    } catch {
      toast.error("No se pudo cargar la línea de tiempo");
      setEvents([]);
    }
  }, [caseId]);

  useEffect(() => {
    if (open) {
      setEvents(null);
      setSuggestions([]);
      load();
    }
  }, [open, load]);

  const fail = (err) => toast.error(formatApiErrorDetail(err.response?.data?.detail));

  const add = async (payload, source = "cliente") => {
    setSaving(true);
    try {
      await api.post(`/cases/${caseId}/events`, { ...payload, source });
      await load();
      return true;
    } catch (err) {
      fail(err);
      return false;
    } finally {
      setSaving(false);
    }
  };

  const submit = async (e) => {
    e.preventDefault();
    if (await add(form)) setForm(EMPTY);
  };

  const toggle = (ev) => api.put(`/cases/${caseId}/events/${ev.id}`, { done: !ev.done }).then(load).catch(fail);
  const remove = (ev) => api.delete(`/cases/${caseId}/events/${ev.id}`).then(load).catch(fail);

  const suggest = async () => {
    setSuggesting(true);
    try {
      const { data } = await api.post(`/cases/${caseId}/events/suggest`);
      setSuggestions(data);
      if (data.length === 0) toast.info("El agente no encontró plazos nuevos que sugerir");
    } catch (err) {
      fail(err);
    } finally {
      setSuggesting(false);
    }
  };

  const accept = async (s, i) => {
    if (await add(s, "agente")) setSuggestions((prev) => prev.filter((_, j) => j !== i));
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-heading text-xl">Línea de tiempo y plazos</DialogTitle>
          <DialogDescription className="flex items-start gap-1.5">
            <BellRing size={14} className="shrink-0 mt-0.5 text-[#0284C7]" />
            Te avisamos por correo 3 días antes, 1 día antes y el mismo día de cada plazo pendiente.
          </DialogDescription>
        </DialogHeader>

        <div data-testid="timeline-list">
          {!events ? (
            <div className="py-8 flex justify-center"><Loader2 className="animate-spin text-[#0284C7]" size={20} /></div>
          ) : events.length === 0 ? (
            <p className="text-xs text-slate-500 py-6 text-center" data-testid="timeline-empty">Aún no hay etapas ni plazos. Agrega el primero o pide una sugerencia al agente.</p>
          ) : (
            <ol className="relative border-l-2 border-slate-200 ml-2 space-y-4 py-2">
              {events.map((ev) => {
                const d = daysLabel(ev);
                return (
                  <li key={ev.id} className="pl-5 relative" data-testid={`timeline-event-${ev.id}`}>
                    <button onClick={() => toggle(ev)} title={ev.done ? "Marcar como pendiente" : "Marcar como cumplido"} data-testid={`timeline-toggle-${ev.id}`} className="absolute -left-[11px] top-0.5 bg-white rounded-full">
                      {ev.done ? <CheckCircle2 size={20} className="text-emerald-600" /> : <Circle size={20} className="text-slate-400 hover:text-[#0284C7] transition-colors" />}
                    </button>
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className={`text-sm font-semibold ${ev.done ? "text-slate-400 line-through" : "text-[#0F172A]"}`}>{ev.title}</p>
                        <p className="text-[11px] text-slate-500 mt-0.5 flex items-center gap-1.5 flex-wrap">
                          {ev.kind === "plazo" ? <CalendarClock size={11} /> : <Flag size={11} />}
                          {ev.kind === "plazo" ? "Plazo" : "Etapa"} · {fmt(ev.date)} · <span className={`font-semibold ${d.cls}`}>{d.text}</span>
                          {ev.source === "agente" && <span className="text-[#0284C7]">· sugerido por el agente</span>}
                        </p>
                        {ev.note && <p className="text-[11px] text-slate-500 mt-1 leading-relaxed">{ev.note}</p>}
                      </div>
                      <button onClick={() => remove(ev)} title="Eliminar" data-testid={`timeline-delete-${ev.id}`} className="text-slate-300 hover:text-red-600 transition-colors shrink-0"><Trash2 size={14} /></button>
                    </div>
                  </li>
                );
              })}
            </ol>
          )}
        </div>

        {suggestions.length > 0 && (
          <div className="border border-sky-200 bg-sky-50 rounded-lg p-4 space-y-3" data-testid="timeline-suggestions">
            <p className="text-xs font-semibold text-sky-900">Sugerencias del agente. Revisa la fecha antes de agregarlas.</p>
            {suggestions.map((s, i) => (
              <div key={`${s.title}-${i}`} className="flex items-start gap-3" data-testid={`timeline-suggestion-${i}`}>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-[#0F172A]">{s.title}</p>
                  <p className="text-[11px] text-slate-600 leading-relaxed">{s.kind === "plazo" ? "Plazo" : "Etapa"} · {s.note}</p>
                  <input type="date" value={s.date} onChange={(e) => setSuggestions((prev) => prev.map((x, j) => (j === i ? { ...x, date: e.target.value } : x)))} data-testid={`timeline-suggestion-date-${i}`} className="mt-1.5 border border-slate-300 px-2 py-1 text-xs bg-white outline-none" />
                </div>
                <button onClick={() => accept(s, i)} disabled={saving} data-testid={`timeline-suggestion-accept-${i}`} className="shrink-0 inline-flex items-center gap-1 bg-[#0284C7] hover:bg-[#0EA5E9] disabled:opacity-60 text-white font-semibold px-3 py-1.5 rounded-full text-[11px] transition-colors">
                  <Plus size={11} /> Agregar
                </button>
              </div>
            ))}
          </div>
        )}

        <form onSubmit={submit} className="border-t border-slate-200 pt-4 grid sm:grid-cols-[1fr_150px_120px] gap-3" data-testid="timeline-form">
          <input required minLength={2} value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="Ej.: Responder la carta notarial" data-testid="timeline-title-input" className={inputCls} />
          <input required type="date" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} data-testid="timeline-date-input" className={inputCls} />
          <select value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value })} data-testid="timeline-kind-select" className={inputCls}>
            <option value="plazo">Plazo</option>
            <option value="etapa">Etapa</option>
          </select>
          <input value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} placeholder="Nota (opcional)" data-testid="timeline-note-input" className={`${inputCls} sm:col-span-3`} />
          <div className="sm:col-span-3 flex flex-wrap gap-2">
            <button type="submit" disabled={saving} data-testid="timeline-add-btn" className="inline-flex items-center gap-1.5 bg-[#0F172A] hover:bg-slate-800 disabled:opacity-60 text-white font-semibold px-5 py-2.5 rounded-full text-xs transition-colors">
              <Plus size={13} /> Agregar
            </button>
            <button type="button" onClick={suggest} disabled={suggesting} data-testid="timeline-suggest-btn" className="inline-flex items-center gap-1.5 border border-[#0284C7] text-[#0284C7] hover:bg-sky-50 disabled:opacity-60 font-semibold px-5 py-2.5 rounded-full text-xs transition-colors">
              {suggesting ? <Loader2 className="animate-spin" size={13} /> : <Sparkles size={13} />} {suggesting ? "Analizando el caso…" : "Sugerir plazos con el agente"}
            </button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};
