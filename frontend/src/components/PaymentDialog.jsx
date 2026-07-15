import { useEffect, useState, useCallback } from "react";
import { PayPalScriptProvider, PayPalButtons } from "@paypal/react-paypal-js";
import { toast } from "sonner";
import { Building2, Building } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { api, formatApiErrorDetail } from "@/lib/api";

const fmtPen = (v) => `S/ ${Number(v).toLocaleString("es-PE", { minimumFractionDigits: 2 })}`;
const fmtUsd = (v) => `USD ${Number(v).toLocaleString("en-US", { minimumFractionDigits: 2 })}`;

export const PaymentDialog = ({ audit, open, onOpenChange, onPaid }) => {
  const [config, setConfig] = useState(null);
  const [plan, setPlan] = useState("small");
  const [quote, setQuote] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!open) return;
    setError(null);
    api
      .get("/payments/config")
      .then(({ data }) => setConfig(data))
      .catch((err) => setError(formatApiErrorDetail(err.response?.data?.detail) || "Pagos no disponibles"));
  }, [open]);

  useEffect(() => {
    if (!open) return;
    setQuote(null);
    api
      .get(`/payments/quote?plan=${plan}`)
      .then(({ data }) => setQuote(data))
      .catch((err) => setError(formatApiErrorDetail(err.response?.data?.detail) || "No se pudo calcular el monto"));
  }, [open, plan]);

  const createOrder = useCallback(async () => {
    const { data } = await api.post("/payments/create-order", { audit_id: audit.id, plan });
    return data.order_id;
  }, [audit?.id, plan]);

  const onApprove = useCallback(
    async (data) => {
      try {
        const res = await api.post(`/payments/capture/${data.orderID}`);
        toast.success(res.data.message);
        onOpenChange(false);
        onPaid?.();
      } catch (err) {
        toast.error(formatApiErrorDetail(err.response?.data?.detail) || "No se pudo confirmar el pago");
      }
    },
    [onOpenChange, onPaid]
  );

  const plans = [
    { key: "small", icon: Building, title: "Pequeño", desc: "Menos de 50 dptos." },
    { key: "medium", icon: Building2, title: "Mediano-grande", desc: "De 50 a 150 dptos." },
  ];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md" data-testid="payment-dialog">
        <DialogHeader>
          <DialogTitle className="font-heading">Activa tu auditoría</DialogTitle>
          <DialogDescription>
            Paga con PayPal y tu auditoría de <b>{audit?.condominium_name}</b> se activará automáticamente.
          </DialogDescription>
        </DialogHeader>

        {error ? (
          <p className="text-sm text-red-600 bg-red-50 border border-red-200 p-4" data-testid="payment-error">{error}</p>
        ) : (
          <div className="space-y-5">
            <div className="grid grid-cols-2 gap-3">
              {plans.map((p) => {
                const Icon = p.icon;
                const active = plan === p.key;
                return (
                  <button
                    key={p.key}
                    type="button"
                    onClick={() => setPlan(p.key)}
                    data-testid={`plan-${p.key}-option`}
                    className={`text-left p-4 border transition-colors ${
                      active ? "border-[#0284C7] bg-sky-50" : "border-slate-200 hover:border-slate-300"
                    }`}
                  >
                    <Icon size={20} className={active ? "text-[#0284C7]" : "text-slate-400"} strokeWidth={1.5} />
                    <p className="font-heading font-bold text-sm text-[#0F172A] mt-2">{p.title}</p>
                    <p className="text-[11px] text-slate-500">{p.desc}</p>
                  </button>
                );
              })}
            </div>

            <div className="bg-slate-50 border border-slate-200 p-4 text-sm" data-testid="payment-quote">
              {quote ? (
                <>
                  <div className="flex justify-between text-slate-600">
                    <span>Precio del plan</span>
                    <span className="font-semibold text-[#0F172A]">{fmtPen(quote.amount_pen)}</span>
                  </div>
                  <div className="flex justify-between text-slate-600 mt-1.5">
                    <span>T.C. del día (ref.)</span>
                    <span>S/ {quote.rate_pen_per_usd?.toFixed(3)} por USD</span>
                  </div>
                  <div className="flex justify-between mt-2.5 pt-2.5 border-t border-slate-200">
                    <span className="font-semibold text-[#0F172A]">Total a cobrar</span>
                    <span className="font-heading font-black text-[#0284C7]" data-testid="payment-total-usd">{fmtUsd(quote.amount_usd)}</span>
                  </div>
                </>
              ) : (
                <p className="text-slate-400 text-xs">Calculando monto con el tipo de cambio del día…</p>
              )}
            </div>

            {config && quote && (
              <div data-testid="paypal-buttons-container">
                <PayPalScriptProvider
                  options={{ clientId: config.client_id, currency: "USD", intent: "capture", locale: "es_ES" }}
                >
                  <PayPalButtons
                    forceReRender={[plan, quote.amount_usd]}
                    style={{ layout: "vertical", shape: "pill", label: "pay" }}
                    createOrder={createOrder}
                    onApprove={onApprove}
                    onError={() => toast.error("PayPal reportó un error. Intenta nuevamente.")}
                  />
                </PayPalScriptProvider>
              </div>
            )}

            <p className="text-[11px] text-slate-400 leading-relaxed">
              El cobro se procesa en dólares americanos (USD) con el tipo de cambio del día. Al completarse el
              pago, la auditoría se activa de inmediato (1 auditoría por pago) y recibirás la confirmación por
              correo. {config?.mode === "sandbox" && <b className="text-amber-600">Modo de prueba (sandbox) activo.</b>}
            </p>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};
