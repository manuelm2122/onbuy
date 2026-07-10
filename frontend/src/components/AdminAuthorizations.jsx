import { useEffect, useState, useCallback } from "react";
import { BadgeCheck, Ban, ShieldCheck, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { api, formatApiErrorDetail } from "@/lib/api";

const STATUS = {
  pendiente: { label: "Pendiente", cls: "bg-amber-50 text-amber-700 border-amber-200" },
  analizando: { label: "Analizando", cls: "bg-sky-50 text-sky-700 border-sky-200" },
  completada: { label: "Completada", cls: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  error: { label: "Error", cls: "bg-red-50 text-red-700 border-red-200" },
};

const PAYMENT = {
  pendiente_pago: { label: "Pago pendiente", cls: "bg-orange-50 text-orange-700 border-orange-200" },
  autorizada: { label: "Autorizada", cls: "bg-emerald-50 text-emerald-700 border-emerald-200" },
};

const Pill = ({ meta }) => (
  <span className={`inline-flex items-center text-[11px] font-semibold px-2.5 py-0.5 rounded-full border whitespace-nowrap ${meta.cls}`}>
    {meta.label}
  </span>
);

export const AdminAuthorizations = () => {
  const [audits, setAudits] = useState(null);
  const [acting, setActing] = useState(null);

  const load = useCallback(async () => {
    try {
      const { data } = await api.get("/admin/audits");
      setAudits(data);
    } catch {
      toast.error("No se pudieron cargar las auditorías");
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const act = async (id, action) => {
    setActing(id);
    try {
      const { data } = await api.post(`/admin/audits/${id}/${action}`);
      toast.success(data.message);
      load();
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail));
    } finally {
      setActing(null);
    }
  };

  const removeAudit = async (id, name) => {
    if (!window.confirm(`¿Eliminar por completo la auditoría "${name}" y todos sus documentos? Esta acción es irreversible.`)) return;
    setActing(id);
    try {
      const { data } = await api.delete(`/audits/${id}`);
      toast.success(data.message);
      load();
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail));
    } finally {
      setActing(null);
    }
  };

  const pendingCount = (audits || []).filter((a) => a.payment_status === "pendiente_pago").length;

  return (
    <div>
      <div className="bg-sky-50 border border-sky-200 p-5 flex items-start gap-4 mb-6" data-testid="authorizations-info-banner">
        <ShieldCheck className="text-[#0284C7] shrink-0 mt-0.5" size={22} strokeWidth={1.5} />
        <div>
          <h3 className="font-heading font-bold text-[#0F172A] text-sm">Control de autorizaciones</h3>
          <p className="text-xs text-slate-600 leading-relaxed mt-1.5">
            Las auditorías de los clientes quedan bloqueadas al crearse. Cuando confirmes el pago
            (S/ 1,100 · &lt;50 dptos. / S/ 2,100 · 50–150 dptos.), autorízalas aquí para habilitar el
            análisis con IA.{" "}
            {pendingCount > 0 && (
              <b data-testid="pending-authorizations-count">
                {pendingCount} auditoría(s) pendiente(s) de autorización.
              </b>
            )}
          </p>
        </div>
      </div>

      {!audits ? (
        <div className="bg-white border border-slate-200 p-12 flex justify-center">
          <div className="w-6 h-6 border-2 border-[#0284C7] border-t-transparent rounded-full animate-spin" />
        </div>
      ) : audits.length === 0 ? (
        <div className="bg-white border border-dashed border-slate-300 p-12 text-center" data-testid="empty-authorizations">
          <p className="text-slate-500 text-sm">Aún no hay auditorías de clientes.</p>
        </div>
      ) : (
        <div className="bg-white border border-slate-200 overflow-x-auto">
          <table className="w-full text-sm" data-testid="authorizations-table">
            <thead>
              <tr className="bg-[#0F172A] text-white text-left">
                <th className="px-5 py-3.5 font-semibold text-xs tracking-wider uppercase">Cliente</th>
                <th className="px-5 py-3.5 font-semibold text-xs tracking-wider uppercase">Condominio</th>
                <th className="px-5 py-3.5 font-semibold text-xs tracking-wider uppercase hidden md:table-cell">Período</th>
                <th className="px-5 py-3.5 font-semibold text-xs tracking-wider uppercase hidden sm:table-cell">Docs</th>
                <th className="px-5 py-3.5 font-semibold text-xs tracking-wider uppercase">Estado</th>
                <th className="px-5 py-3.5 font-semibold text-xs tracking-wider uppercase">Pago</th>
                <th className="px-5 py-3.5 font-semibold text-xs tracking-wider uppercase text-right">Acción</th>
              </tr>
            </thead>
            <tbody>
              {audits.map((a) => (
                <tr key={a.id} className="border-t border-slate-100" data-testid={`auth-row-${a.id}`}>
                  <td className="px-5 py-4">
                    <p className="font-semibold text-[#0F172A]">{a.owner_name}</p>
                    <p className="text-xs text-slate-400">{a.owner_email}</p>
                  </td>
                  <td className="px-5 py-4">
                    <p className="text-[#0F172A]">{a.condominium_name}</p>
                    <p className="text-xs text-slate-400">{a.district || ""}</p>
                  </td>
                  <td className="px-5 py-4 text-slate-600 hidden md:table-cell">{a.period}</td>
                  <td className="px-5 py-4 text-slate-600 hidden sm:table-cell">{a.document_count}</td>
                  <td className="px-5 py-4">
                    <Pill meta={STATUS[a.status] || STATUS.pendiente} />
                  </td>
                  <td className="px-5 py-4">
                    <Pill meta={PAYMENT[a.payment_status] || PAYMENT.pendiente_pago} />
                  </td>
                  <td className="px-5 py-4 text-right">
                    <div className="inline-flex items-center gap-2">
                      {a.payment_status === "pendiente_pago" ? (
                        <button
                          onClick={() => act(a.id, "authorize")}
                          disabled={acting === a.id}
                          data-testid={`authorize-audit-btn-${a.id}`}
                          className="inline-flex items-center gap-1.5 bg-[#0284C7] hover:bg-[#0EA5E9] disabled:opacity-60 text-white font-semibold px-4 py-2 rounded-full text-xs transition-colors"
                        >
                          <BadgeCheck size={14} />
                          {acting === a.id ? "Autorizando…" : "Autorizar"}
                        </button>
                      ) : (
                        <button
                          onClick={() => act(a.id, "revoke")}
                          disabled={acting === a.id}
                          data-testid={`revoke-audit-btn-${a.id}`}
                          className="inline-flex items-center gap-1.5 border border-slate-300 hover:border-red-400 hover:text-red-600 disabled:opacity-60 text-slate-500 font-semibold px-4 py-2 rounded-full text-xs transition-colors"
                        >
                          <Ban size={14} />
                          {acting === a.id ? "Revocando…" : "Revocar"}
                        </button>
                      )}
                      <button
                        onClick={() => removeAudit(a.id, a.condominium_name)}
                        disabled={acting === a.id}
                        data-testid={`admin-delete-audit-btn-${a.id}`}
                        title="Eliminar auditoría por completo"
                        className="text-slate-400 hover:text-red-600 disabled:opacity-40 transition-colors p-1.5"
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
