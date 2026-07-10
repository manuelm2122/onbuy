import { useEffect, useState, useCallback } from "react";
import { BookOpenCheck, Eye, Download, CheckCircle2, RotateCcw, Loader2 } from "lucide-react";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { api, BACKEND_URL, formatApiErrorDetail } from "@/lib/api";

const fmtDate = (iso) =>
  new Date(iso).toLocaleString("es-PE", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });

const daysLeft = (dueIso) => Math.ceil((new Date(dueIso) - new Date()) / (1000 * 60 * 60 * 24));

const DeadlineBadge = ({ c }) => {
  if (c.status === "respondido")
    return <span className="text-[10px] font-bold px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">Respondido</span>;
  const d = daysLeft(c.due_date);
  const cls = d < 0 ? "bg-red-100 text-red-700 border-red-300" : d <= 5 ? "bg-amber-50 text-amber-700 border-amber-200" : "bg-sky-50 text-[#0284C7] border-sky-200";
  const label = d < 0 ? `Vencido hace ${Math.abs(d)} d` : `${d} días restantes`;
  return <span className={`text-[10px] font-bold px-2.5 py-1 rounded-full border ${cls}`}>{label}</span>;
};

const Row = ({ label, value }) => (
  <div className="grid grid-cols-[140px_1fr] gap-2 py-1.5 border-b border-slate-50 text-xs">
    <span className="font-semibold text-slate-500">{label}</span>
    <span className="text-slate-700 whitespace-pre-wrap">{value || "—"}</span>
  </div>
);

export const AdminComplaints = () => {
  const [complaints, setComplaints] = useState(null);
  const [selected, setSelected] = useState(null);
  const [acting, setActing] = useState(null);
  const [responseNote, setResponseNote] = useState("");

  const load = useCallback(async () => {
    try {
      const { data } = await api.get("/admin/complaints");
      setComplaints(data);
    } catch {
      toast.error("No se pudieron cargar los reclamos");
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const setStatus = async (c, status) => {
    setActing(c.id);
    try {
      const { data } = await api.put(`/admin/complaints/${c.id}/status`, {
        status,
        response_note: status === "respondido" ? responseNote || null : null,
      });
      toast.success(data.message);
      setSelected(null);
      setResponseNote("");
      load();
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail));
    } finally {
      setActing(null);
    }
  };

  const pending = complaints?.filter((c) => c.status !== "respondido").length || 0;

  return (
    <div className="bg-white border border-slate-200" data-testid="admin-complaints">
      <div className="p-6 border-b border-slate-100 flex items-center justify-between">
        <div>
          <h3 className="font-heading font-bold text-[#0F172A] flex items-center gap-2">
            <BookOpenCheck size={18} className="text-[#0284C7]" /> Libro de Reclamaciones
          </h3>
          <p className="text-xs text-slate-500 mt-1">
            Plazo legal de respuesta: 15 días hábiles improrrogables (Ley N° 31435). Custodia mínima: 2 años.
          </p>
        </div>
        {complaints && (
          <span
            className={`text-xs font-bold px-3 py-1.5 rounded-full ${pending > 0 ? "bg-red-50 text-red-600 border border-red-200" : "bg-slate-100 text-slate-500"}`}
            data-testid="complaints-pending-badge"
          >
            {pending > 0 ? `${pending} por responder` : "Todo respondido"}
          </span>
        )}
      </div>

      {!complaints ? (
        <div className="p-10 flex justify-center">
          <Loader2 className="animate-spin text-[#0284C7]" size={22} />
        </div>
      ) : complaints.length === 0 ? (
        <div className="p-12 text-center" data-testid="complaints-empty">
          <BookOpenCheck className="mx-auto text-slate-300" size={36} strokeWidth={1.2} />
          <p className="text-sm text-slate-500 mt-3">Aún no hay reclamos ni quejas registrados.</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left" data-testid="complaints-table">
            <thead>
              <tr className="border-b border-slate-100 text-[10px] tracking-[0.15em] uppercase text-slate-400">
                <th className="px-5 py-3 font-semibold">N° Reclamo</th>
                <th className="px-5 py-3 font-semibold">Consumidor</th>
                <th className="px-5 py-3 font-semibold">Tipo</th>
                <th className="px-5 py-3 font-semibold">Monto</th>
                <th className="px-5 py-3 font-semibold">Recibido</th>
                <th className="px-5 py-3 font-semibold">Plazo</th>
                <th className="px-5 py-3 font-semibold text-right">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {complaints.map((c) => (
                <tr key={c.id} className="border-b border-slate-50 hover:bg-slate-50/60 transition-colors" data-testid={`complaint-row-${c.id}`}>
                  <td className="px-5 py-4 font-mono text-xs font-bold text-[#0284C7]">{c.code}</td>
                  <td className="px-5 py-4">
                    <p className="text-sm font-semibold text-[#0F172A]">{c.consumer_name}</p>
                    <p className="text-[11px] text-slate-400">{c.email}</p>
                  </td>
                  <td className="px-5 py-4">
                    <span className={`text-[10px] font-bold px-2.5 py-1 rounded-full border ${c.request_type === "Reclamo" ? "bg-red-50 text-red-600 border-red-200" : "bg-amber-50 text-amber-700 border-amber-200"}`}>
                      {c.request_type}
                    </span>
                  </td>
                  <td className="px-5 py-4 text-xs text-slate-600">{c.amount ? `S/ ${Number(c.amount).toLocaleString("es-PE")}` : "—"}</td>
                  <td className="px-5 py-4 text-xs text-slate-500">{fmtDate(c.created_at)}</td>
                  <td className="px-5 py-4"><DeadlineBadge c={c} /></td>
                  <td className="px-5 py-4 text-right">
                    <div className="inline-flex items-center gap-1.5">
                      <button
                        onClick={() => { setSelected(c); setResponseNote(c.response_note || ""); }}
                        data-testid={`complaint-view-${c.id}`}
                        title="Ver detalle"
                        className="text-slate-400 hover:text-[#0284C7] transition-colors p-1.5"
                      >
                        <Eye size={16} />
                      </button>
                      <a
                        href={`${BACKEND_URL}/api/complaints/${c.id}/receipt`}
                        data-testid={`complaint-pdf-${c.id}`}
                        title="Descargar hoja PDF"
                        className="text-slate-400 hover:text-[#0284C7] transition-colors p-1.5"
                      >
                        <Download size={16} />
                      </a>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Dialog open={!!selected} onOpenChange={(o) => !o && setSelected(null)}>
        <DialogContent className="sm:max-w-2xl max-h-[85vh] overflow-y-auto">
          {selected && (
            <>
              <DialogHeader>
                <DialogTitle className="font-heading text-xl flex items-center gap-3">
                  {selected.code}
                  <DeadlineBadge c={selected} />
                </DialogTitle>
                <DialogDescription>
                  {selected.request_type} recibido el {fmtDate(selected.created_at)} — {selected.website}
                </DialogDescription>
              </DialogHeader>
              <div className="mt-2" data-testid="complaint-detail-dialog">
                <Row label="Consumidor" value={selected.consumer_name} />
                <Row label="Documento" value={`${selected.doc_type} ${selected.doc_number}`} />
                <Row label="Domicilio" value={selected.address} />
                <Row label="Contacto" value={`${selected.email} · ${selected.phone}`} />
                <Row label="Bien contratado" value={`${selected.item_type} — ${selected.service_description}`} />
                <Row label="Monto reclamado" value={selected.amount ? `S/ ${Number(selected.amount).toLocaleString("es-PE")}` : "No precisado"} />
                <Row label="Detalle" value={selected.detail} />
                <Row label="Pedido" value={selected.consumer_request} />
                <Row label="Plazo de respuesta" value={selected.due_date_display} />
                <Row label="Email al consumidor" value={selected.consumer_email_status ? (selected.consumer_email_status.status === "sent" ? "Enviado ✓" : `No enviado (${selected.consumer_email_status.reason || selected.consumer_email_status.status})`) : "En proceso…"} />
                {selected.responded_at && <Row label="Respondido el" value={fmtDate(selected.responded_at)} />}
                {selected.status !== "respondido" ? (
                  <div className="mt-4">
                    <label className="text-[10px] tracking-[0.15em] uppercase text-slate-500 font-semibold">Nota de respuesta (opcional)</label>
                    <textarea
                      rows={3}
                      value={responseNote}
                      onChange={(e) => setResponseNote(e.target.value)}
                      placeholder="Resumen de la respuesta dada al consumidor…"
                      data-testid="complaint-response-note"
                      className="mt-1 w-full border border-slate-300 focus:border-[#0284C7] outline-none px-3 py-2.5 text-sm transition-colors resize-none"
                    />
                    <button
                      onClick={() => setStatus(selected, "respondido")}
                      disabled={acting === selected.id}
                      data-testid="complaint-mark-responded"
                      className="mt-3 w-full inline-flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-60 text-white font-semibold py-3 rounded-full text-sm transition-colors"
                    >
                      <CheckCircle2 size={15} />
                      {acting === selected.id ? "Guardando…" : "Marcar como respondido"}
                    </button>
                  </div>
                ) : (
                  <>
                    {selected.response_note && <Row label="Nota de respuesta" value={selected.response_note} />}
                    <button
                      onClick={() => setStatus(selected, "pendiente")}
                      disabled={acting === selected.id}
                      data-testid="complaint-mark-pending"
                      className="mt-4 w-full inline-flex items-center justify-center gap-2 border border-slate-300 hover:border-amber-400 hover:text-amber-600 disabled:opacity-60 text-slate-500 font-semibold py-3 rounded-full text-sm transition-colors"
                    >
                      <RotateCcw size={14} />
                      {acting === selected.id ? "Guardando…" : "Volver a pendiente"}
                    </button>
                  </>
                )}
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};
