import { useCallback, useEffect, useState } from "react";
import { FilePlus2, Loader2, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { api, formatApiErrorDetail } from "@/lib/api";
import { toFormData } from "@/lib/download";
import { EvidencePicker, FileChip, fmtDay, inputCls } from "@/components/EvidencePicker";

const EMPTY = { type: "pago", date: "", amount: "", concept: "", repeat_until: "" };

export const CaseLedger = ({ caseId, open, onOpenChange, onChanged }) => {
  const [ledger, setLedger] = useState(null);
  const [form, setForm] = useState(EMPTY);
  const [evidence, setEvidence] = useState(null);
  const [busy, setBusy] = useState(false);

  const fail = (err) => toast.error(formatApiErrorDetail(err.response?.data?.detail));
  const load = useCallback(() => api.get(`/cases/${caseId}/ledger`).then(({ data }) => setLedger(data)).catch(fail), [caseId]);

  useEffect(() => {
    if (open) {
      setLedger(null);
      load();
    }
  }, [open, load]);

  const symbol = ledger?.currency === "USD" ? "US$" : "S/";
  const money = (v) => `${symbol} ${Number(v).toLocaleString("es-PE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

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
      const fields = { ...form, repeat_until: form.type === "cargo" ? form.repeat_until : "" };
      const { data } = await api.post(`/cases/${caseId}/ledger`, toFormData(fields, evidence));
      setLedger(data);
      setForm({ ...EMPTY, type: form.type });
      setEvidence(null);
    });
  };

  const remove = (id) => run(async () => { await api.delete(`/cases/${caseId}/ledger/${id}`); await load(); });
  const setCurrency = (currency) => run(async () => setLedger((await api.put(`/cases/${caseId}/ledger/currency`, { currency })).data));
  const exportToCase = () => run(async () => {
    await api.post(`/cases/${caseId}/ledger/export`);
    toast.success("Estado de cuenta añadido al expediente");
    onOpenChange(false);
    onChanged();
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-heading text-xl">Registro de pagos y deudas</DialogTitle>
          <DialogDescription>Anota lo que te deben (cargos) y cada pago recibido con su comprobante. El saldo se actualiza solo y no descuenta mensajes.</DialogDescription>
        </DialogHeader>
        {!ledger ? (
          <div className="py-8 flex justify-center"><Loader2 className="animate-spin text-[#0284C7]" size={20} /></div>
        ) : (
          <>
            <div className="grid grid-cols-3 gap-3" data-testid="ledger-summary">
              {[["Total adeudado", ledger.total_cargos, "text-[#0F172A]"], ["Total pagado", ledger.total_pagos, "text-emerald-700"], ["Saldo pendiente", ledger.saldo, "text-red-600"]].map(([label, value, cls], i) => (
                <div key={label} className="border border-slate-200 p-3">
                  <p className="text-[10px] tracking-[0.12em] uppercase text-slate-500 font-semibold">{label}</p>
                  <p className={`font-heading font-bold text-base sm:text-lg mt-1 ${cls}`} data-testid={`ledger-total-${i}`}>{money(value)}</p>
                </div>
              ))}
            </div>
            {ledger.entries.length === 0 ? (
              <p className="text-xs text-slate-500 py-4 text-center" data-testid="ledger-empty">Aún no hay movimientos. Empieza registrando la deuda (cargo) y luego los pagos.</p>
            ) : (
              <div className="overflow-x-auto border border-slate-200" data-testid="ledger-list">
                <table className="w-full text-xs">
                  <thead className="bg-slate-50 text-slate-500 text-left">
                    <tr>{["Fecha", "Concepto", "Cargo", "Pago", "Saldo", ""].map((h) => <th key={h} className="px-3 py-2 font-semibold">{h}</th>)}</tr>
                  </thead>
                  <tbody>
                    {ledger.entries.map((e) => (
                      <tr key={e.id} className="border-t border-slate-100" data-testid={`ledger-entry-${e.id}`}>
                        <td className="px-3 py-2 whitespace-nowrap">{fmtDay(e.date)}</td>
                        <td className="px-3 py-2 max-w-[220px]"><p className="text-[#0F172A]">{e.concept}</p><FileChip caseId={caseId} file={e.file} /></td>
                        <td className="px-3 py-2 whitespace-nowrap">{e.type === "cargo" ? money(e.amount) : ""}</td>
                        <td className="px-3 py-2 whitespace-nowrap text-emerald-700">{e.type === "pago" ? money(e.amount) : ""}</td>
                        <td className="px-3 py-2 whitespace-nowrap font-semibold">{money(e.balance)}</td>
                        <td className="px-3 py-2"><button onClick={() => remove(e.id)} title="Eliminar" data-testid={`ledger-delete-${e.id}`} className="text-slate-300 hover:text-red-600 transition-colors"><Trash2 size={13} /></button></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <form onSubmit={submit} className="border-t border-slate-200 pt-4 grid sm:grid-cols-4 gap-3" data-testid="ledger-form">
              <select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })} data-testid="ledger-type-select" className={inputCls}>
                <option value="pago">Pago recibido</option>
                <option value="cargo">Cargo (lo que me deben)</option>
              </select>
              <input required type="date" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} data-testid="ledger-date-input" className={inputCls} />
              <input required type="number" step="0.01" min="0.01" placeholder={`Monto (${symbol})`} value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} data-testid="ledger-amount-input" className={inputCls} />
              <select value={ledger.currency} onChange={(e) => setCurrency(e.target.value)} data-testid="ledger-currency-select" className={inputCls} title="Moneda de todo el registro">
                <option value="PEN">Soles (S/)</option>
                <option value="USD">Dólares (US$)</option>
              </select>
              <input required minLength={2} placeholder="Concepto. Ej.: Renta de marzo" value={form.concept} onChange={(e) => setForm({ ...form, concept: e.target.value })} data-testid="ledger-concept-input" className={`${inputCls} ${form.type === "cargo" ? "sm:col-span-2" : "sm:col-span-4"}`} />
              {form.type === "cargo" && (
                <div className="sm:col-span-2">
                  <input type="month" value={form.repeat_until} onChange={(e) => setForm({ ...form, repeat_until: e.target.value })} data-testid="ledger-repeat-input" className={inputCls} />
                  <p className="text-[10px] text-slate-400 mt-1">Opcional: repetir este cargo cada mes hasta el mes indicado.</p>
                </div>
              )}
              <div className="sm:col-span-4"><EvidencePicker caseId={caseId} value={evidence} onChange={setEvidence} label="Comprobante (opcional)" /></div>
              <div className="sm:col-span-4 flex flex-wrap gap-2">
                <button type="submit" disabled={busy} data-testid="ledger-add-btn" className="inline-flex items-center gap-1.5 bg-[#0F172A] hover:bg-slate-800 disabled:opacity-60 text-white font-semibold px-5 py-2.5 rounded-full text-xs transition-colors"><Plus size={13} /> Registrar</button>
                <button type="button" onClick={exportToCase} disabled={busy || ledger.entries.length === 0} data-testid="ledger-export-btn" className="inline-flex items-center gap-1.5 border border-[#0284C7] text-[#0284C7] hover:bg-sky-50 disabled:opacity-50 font-semibold px-5 py-2.5 rounded-full text-xs transition-colors"><FilePlus2 size={13} /> Añadir estado de cuenta al expediente</button>
              </div>
            </form>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
};
