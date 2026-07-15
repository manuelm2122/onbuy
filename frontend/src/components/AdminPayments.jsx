import { useEffect, useState } from "react";
import { CreditCard, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";

const fmtDate = (iso) =>
  iso ? new Date(iso).toLocaleString("es-PE", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }) : "—";

const STATUS_META = {
  completed: { label: "Pagado", cls: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  created: { label: "Sin completar", cls: "bg-amber-50 text-amber-700 border-amber-200" },
};

const PLAN_LABELS = { small: "Pequeño", medium: "Mediano-grande" };

export const AdminPayments = () => {
  const [payments, setPayments] = useState(null);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/admin/payments");
      setPayments(data);
    } catch {
      toast.error("No se pudo cargar el historial de pagos");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  if (payments === null)
    return <p className="text-sm text-slate-400 py-10 text-center">Cargando historial de pagos…</p>;

  const completed = payments.filter((p) => p.status === "completed");
  const totalUsd = completed.reduce((s, p) => s + (p.amount_usd || 0), 0);
  const totalPen = completed.reduce((s, p) => s + (p.amount_pen || 0), 0);

  return (
    <div data-testid="admin-payments">
      <div className="grid sm:grid-cols-3 gap-4 mb-6">
        <div className="bg-white border border-slate-200 p-5" data-testid="payments-stat-count">
          <p className="text-[10px] tracking-[0.2em] uppercase text-slate-500 font-semibold">Pagos completados</p>
          <p className="font-heading font-black text-3xl text-[#0F172A] mt-1">{completed.length}</p>
        </div>
        <div className="bg-white border border-slate-200 p-5" data-testid="payments-stat-usd">
          <p className="text-[10px] tracking-[0.2em] uppercase text-slate-500 font-semibold">Total cobrado (USD)</p>
          <p className="font-heading font-black text-3xl text-[#0284C7] mt-1">
            $ {totalUsd.toLocaleString("en-US", { minimumFractionDigits: 2 })}
          </p>
        </div>
        <div className="bg-white border border-slate-200 p-5" data-testid="payments-stat-pen">
          <p className="text-[10px] tracking-[0.2em] uppercase text-slate-500 font-semibold">Equivalente (S/)</p>
          <p className="font-heading font-black text-3xl text-[#0F172A] mt-1">
            S/ {totalPen.toLocaleString("es-PE", { minimumFractionDigits: 2 })}
          </p>
        </div>
      </div>

      <div className="bg-white border border-slate-200">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <CreditCard className="text-[#0284C7]" size={20} strokeWidth={1.5} />
            <h3 className="font-heading font-bold text-[#0F172A]">Historial de transacciones PayPal</h3>
          </div>
          <button
            onClick={load}
            disabled={loading}
            data-testid="payments-refresh-btn"
            className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-[#0284C7] transition-colors disabled:opacity-50"
          >
            <RefreshCw size={13} className={loading ? "animate-spin" : ""} /> Actualizar
          </button>
        </div>

        {payments.length === 0 ? (
          <p className="text-sm text-slate-400 py-12 text-center" data-testid="payments-empty">
            Aún no hay transacciones registradas. Cuando un cliente pague con PayPal aparecerá aquí.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-[#0F172A] text-white text-left">
                  <th className="px-4 py-3 font-semibold text-xs tracking-wider uppercase">Fecha</th>
                  <th className="px-4 py-3 font-semibold text-xs tracking-wider uppercase">Cliente</th>
                  <th className="px-4 py-3 font-semibold text-xs tracking-wider uppercase hidden md:table-cell">Auditoría</th>
                  <th className="px-4 py-3 font-semibold text-xs tracking-wider uppercase hidden sm:table-cell">Plan</th>
                  <th className="px-4 py-3 font-semibold text-xs tracking-wider uppercase">Monto</th>
                  <th className="px-4 py-3 font-semibold text-xs tracking-wider uppercase">Estado</th>
                  <th className="px-4 py-3 font-semibold text-xs tracking-wider uppercase hidden lg:table-cell">ID transacción</th>
                </tr>
              </thead>
              <tbody>
                {payments.map((p) => {
                  const meta = STATUS_META[p.status] || STATUS_META.created;
                  return (
                    <tr key={p.id} className="border-t border-slate-100" data-testid={`payment-row-${p.id}`}>
                      <td className="px-4 py-3.5 text-slate-600 whitespace-nowrap text-xs">
                        {fmtDate(p.captured_at || p.created_at)}
                      </td>
                      <td className="px-4 py-3.5">
                        <p className="text-[#0F172A] font-medium text-xs">{p.user_email}</p>
                        {p.payer_email && p.payer_email !== p.user_email && (
                          <p className="text-[10px] text-slate-400">PayPal: {p.payer_email}</p>
                        )}
                      </td>
                      <td className="px-4 py-3.5 text-slate-600 hidden md:table-cell text-xs">{p.condominium_name}</td>
                      <td className="px-4 py-3.5 text-slate-600 hidden sm:table-cell text-xs">{PLAN_LABELS[p.plan] || p.plan}</td>
                      <td className="px-4 py-3.5 whitespace-nowrap">
                        <p className="font-semibold text-[#0F172A] text-xs">USD {Number(p.amount_usd).toFixed(2)}</p>
                        <p className="text-[10px] text-slate-400">
                          S/ {Number(p.amount_pen).toLocaleString("es-PE", { minimumFractionDigits: 2 })}
                          {p.exchange_rate ? ` · T.C. ${(1 / p.exchange_rate).toFixed(3)}` : ""}
                        </p>
                      </td>
                      <td className="px-4 py-3.5">
                        <span className={`inline-flex items-center gap-1.5 border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide ${meta.cls}`}>
                          {meta.label}
                        </span>
                        {p.paypal_mode === "sandbox" && (
                          <span className="block text-[9px] text-amber-600 mt-1">sandbox</span>
                        )}
                      </td>
                      <td className="px-4 py-3.5 hidden lg:table-cell">
                        <p className="font-mono text-[10px] text-slate-500">{p.capture_id || "—"}</p>
                        <p className="font-mono text-[9px] text-slate-400">Orden: {p.order_id}</p>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
