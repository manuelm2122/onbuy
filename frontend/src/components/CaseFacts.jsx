import { useCallback, useEffect, useState } from "react";
import { FilePlus2, Loader2, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { api, formatApiErrorDetail } from "@/lib/api";
import { toFormData } from "@/lib/download";
import { EvidencePicker, FileChip, fmtDay, inputCls } from "@/components/EvidencePicker";

const EMPTY = { date: "", text: "" };

export const CaseFacts = ({ caseId, open, onOpenChange, onChanged }) => {
  const [facts, setFacts] = useState(null);
  const [form, setForm] = useState(EMPTY);
  const [evidence, setEvidence] = useState(null);
  const [busy, setBusy] = useState(false);

  const fail = (err) => toast.error(formatApiErrorDetail(err.response?.data?.detail));
  const load = useCallback(() => api.get(`/cases/${caseId}/facts`).then(({ data }) => setFacts(data)).catch(fail), [caseId]);

  useEffect(() => {
    if (open) {
      setFacts(null);
      load();
    }
  }, [open, load]);

  const run = async (fn) => {
    setBusy(true);
    try {
      await fn();
    } catch (err) {
      fail(err);
    } finally {
      setBusy(false);
    }
  };

  const submit = (e) => {
    e.preventDefault();
    run(async () => {
      const { data } = await api.post(`/cases/${caseId}/facts`, toFormData(form, evidence));
      setFacts(data);
      setForm(EMPTY);
      setEvidence(null);
    });
  };

  const remove = (id) => run(async () => { await api.delete(`/cases/${caseId}/facts/${id}`); await load(); });
  const exportToCase = () => run(async () => {
    await api.post(`/cases/${caseId}/facts/export`);
    toast.success("Relación de hechos añadida al expediente");
    onOpenChange(false);
    onChanged();
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-heading text-xl">Cuaderno de hechos</DialogTitle>
          <DialogDescription>Anota lo ocurrido con su fecha y la prueba que lo respalda. Se ordena solo y se convierte en la "relación de hechos" de tu demanda, denuncia o reclamo.</DialogDescription>
        </DialogHeader>
        {!facts ? (
          <div className="py-8 flex justify-center"><Loader2 className="animate-spin text-[#0284C7]" size={20} /></div>
        ) : facts.length === 0 ? (
          <p className="text-xs text-slate-500 py-4 text-center" data-testid="facts-empty">Aún no hay hechos. Empieza por el más antiguo: cuándo y cómo comenzó todo.</p>
        ) : (
          <ol className="relative border-l-2 border-slate-200 ml-2 space-y-4 py-2" data-testid="facts-list">
            {facts.map((f, i) => (
              <li key={f.id} className="pl-5 relative" data-testid={`fact-item-${f.id}`}>
                <span className="absolute -left-[11px] top-0 w-5 h-5 rounded-full bg-[#0284C7] text-white text-[10px] font-bold flex items-center justify-center">{i + 1}</span>
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-[11px] font-semibold text-slate-500">{fmtDay(f.date)}</p>
                    <p className="text-sm text-[#0F172A] leading-relaxed whitespace-pre-wrap break-words">{f.text}</p>
                    <FileChip caseId={caseId} file={f.file} />
                  </div>
                  <button onClick={() => remove(f.id)} title="Eliminar" data-testid={`fact-delete-${f.id}`} className="text-slate-300 hover:text-red-600 transition-colors shrink-0"><Trash2 size={14} /></button>
                </div>
              </li>
            ))}
          </ol>
        )}
        <form onSubmit={submit} className="border-t border-slate-200 pt-4 space-y-3" data-testid="facts-form">
          <div className="grid sm:grid-cols-[160px_1fr] gap-3">
            <input required type="date" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} data-testid="fact-date-input" className={inputCls} />
            <textarea required minLength={3} maxLength={2000} rows={2} placeholder="¿Qué ocurrió? Ej.: El inquilino dejó de pagar la renta y no respondió mis mensajes." value={form.text} onChange={(e) => setForm({ ...form, text: e.target.value })} data-testid="fact-text-input" className={`${inputCls} resize-y`} />
          </div>
          <EvidencePicker caseId={caseId} value={evidence} onChange={setEvidence} label="Prueba vinculada (opcional)" />
          <div className="flex flex-wrap gap-2">
            <button type="submit" disabled={busy} data-testid="fact-add-btn" className="inline-flex items-center gap-1.5 bg-[#0F172A] hover:bg-slate-800 disabled:opacity-60 text-white font-semibold px-5 py-2.5 rounded-full text-xs transition-colors"><Plus size={13} /> Agregar hecho</button>
            <button type="button" onClick={exportToCase} disabled={busy || !facts?.length} data-testid="facts-export-btn" className="inline-flex items-center gap-1.5 border border-[#0284C7] text-[#0284C7] hover:bg-sky-50 disabled:opacity-50 font-semibold px-5 py-2.5 rounded-full text-xs transition-colors"><FilePlus2 size={13} /> Añadir relación de hechos al expediente</button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};
