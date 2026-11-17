import { useEffect, useState } from "react";
import { Loader2, Plus, X } from "lucide-react";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { api, formatApiErrorDetail } from "@/lib/api";
import { inputCls } from "@/components/EvidencePicker";

export const CaseChecklist = ({ caseId, open, onOpenChange }) => {
  const [data, setData] = useState(null);
  const [newItem, setNewItem] = useState("");

  useEffect(() => {
    if (!open) return;
    setData(null);
    api.get(`/cases/${caseId}/checklist`).then((res) => setData(res.data)).catch(() => toast.error("No se pudo cargar el checklist"));
  }, [open, caseId]);

  const save = async (tramite, items) => {
    if (items) setData((d) => ({ ...d, tramite, items }));
    try {
      const res = await api.put(`/cases/${caseId}/checklist`, { tramite, items });
      setData(res.data);
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail));
    }
  };

  const changeTramite = (tramite) => {
    if (data.items.length && !window.confirm("Se reemplazará la lista actual por la del nuevo trámite. ¿Continuar?")) return;
    save(tramite, null);
  };

  const addItem = (e) => {
    e.preventDefault();
    save(data.tramite, [...data.items, { text: newItem.trim(), done: false }]);
    setNewItem("");
  };

  const done = data?.items.filter((i) => i.done).length || 0;
  const pct = data?.items.length ? Math.round((done / data.items.length) * 100) : 0;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-heading text-xl">Checklist de requisitos</DialogTitle>
          <DialogDescription>Elige tu trámite y marca lo que ya reuniste. Es una guía general: confirma con el agente lo que aplica a tu caso.</DialogDescription>
        </DialogHeader>
        {!data ? (
          <div className="py-8 flex justify-center"><Loader2 className="animate-spin text-[#0284C7]" size={20} /></div>
        ) : (
          <>
            <select value={data.tramite} onChange={(e) => changeTramite(e.target.value)} data-testid="checklist-tramite-select" className={inputCls}>
              <option value="" disabled>Selecciona el trámite…</option>
              {data.templates.map((t) => <option key={t.key} value={t.key}>{t.label}</option>)}
            </select>
            {data.tramite && (
              <>
                <div data-testid="checklist-progress">
                  <div className="flex justify-between text-xs text-slate-600 mb-1.5">
                    <span>{done} de {data.items.length} requisitos listos</span>
                    <span className="font-semibold text-[#0284C7]" data-testid="checklist-percent">{pct}%</span>
                  </div>
                  <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                    <div className="h-full bg-[#0284C7] transition-[width] duration-300" style={{ width: `${pct}%` }} />
                  </div>
                </div>
                <ul className="space-y-1" data-testid="checklist-items">
                  {data.items.map((item, i) => (
                    <li key={`${item.text}-${i}`} className="flex items-start gap-3 py-1.5 group">
                      <input type="checkbox" checked={item.done} onChange={() => save(data.tramite, data.items.map((x, j) => (j === i ? { ...x, done: !x.done } : x)))} data-testid={`checklist-item-${i}`} className="mt-1 w-4 h-4 accent-[#0284C7] shrink-0" />
                      <span className={`flex-1 text-sm leading-relaxed ${item.done ? "text-slate-400 line-through" : "text-[#0F172A]"}`}>{item.text}</span>
                      <button onClick={() => save(data.tramite, data.items.filter((_, j) => j !== i))} title="Quitar" data-testid={`checklist-remove-${i}`} className="text-slate-300 hover:text-red-600 transition-colors shrink-0 mt-1"><X size={13} /></button>
                    </li>
                  ))}
                </ul>
                <form onSubmit={addItem} className="flex gap-2 border-t border-slate-200 pt-4">
                  <input required minLength={2} maxLength={300} value={newItem} onChange={(e) => setNewItem(e.target.value)} placeholder="Agregar un requisito propio" data-testid="checklist-new-input" className={inputCls} />
                  <button type="submit" data-testid="checklist-add-btn" className="shrink-0 inline-flex items-center gap-1.5 bg-[#0F172A] hover:bg-slate-800 text-white font-semibold px-4 py-2 rounded-full text-xs transition-colors"><Plus size={13} /> Agregar</button>
                </form>
              </>
            )}
          </>
        )}
      </DialogContent>
    </Dialog>
  );
};
