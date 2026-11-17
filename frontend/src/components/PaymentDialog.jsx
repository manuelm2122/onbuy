import { useEffect, useState, useCallback } from "react";
import { PayPalScriptProvider, PayPalButtons } from "@paypal/react-paypal-js";
import { toast } from "sonner";
import { Scale, Landmark, CreditCard, MessageCircle, Clock } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { api, formatApiErrorDetail } from "@/lib/api";

const money = (currency, v) => `${currency === "PEN" ? "S/" : "US$"} ${Number(v).toFixed(2)}`;

const CasePaymentDialog = ({ item, open, onOpenChange, onPaid }) => {
  const [offer, setOffer] = useState(null);
  const [error, setError] = useState(null);
  const [method, setMethod] = useState("paypal");
  const [currency, setCurrency] = useState("PEN");
  const [requesting, setRequesting] = useState(false);

  const load = useCallback(() => {
    setError(null);
    api
      .get(`/payments/case-offer/${item.id}`)
      .then(({ data }) => {
        setOffer(data);
        if (!data.paypal_client_id || data.pending_manual) setMethod("manual");
      })
      .catch((err) => setError(formatApiErrorDetail(err.response?.data?.detail) || "Pagos no disponibles"));
  }, [item.id]);

  useEffect(() => {
    if (open) load();
  }, [open, load]);

  const createOrder = useCallback(async () => {
    const { data } = await api.post("/payments/create-order", { item_type: "case", item_id: item.id });
    return data.order_id;
  }, [item.id]);

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

  const requestManual = async () => {
    setRequesting(true);
    try {
      const { data } = await api.post("/payments/manual", { item_id: item.id, currency });
      toast.success(data.message);
      load();
      onPaid?.();
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail));
    } finally {
      setRequesting(false);
    }
  };

  const extra = offer?.plan === "extra";
  const pending = offer?.pending_manual;
  const manualAmount = offer ? (currency === "PEN" ? offer.amount_pen : offer.amount_usd) : 0;
  const waText = pending
    ? `Hola, realicé el pago de ${money(pending.currency, pending.amount)} para mi chat de asesoría. Referencia: ${pending.reference}`
    : "Hola, quiero pagar mi chat de asesoría legal y contable por depósito o transferencia.";
  const methodBtn = (key, Icon, text) => (
    <button
      type="button"
      onClick={() => setMethod(key)}
      data-testid={`pay-method-${key}`}
      className={`flex items-center justify-center gap-2 p-3 border text-xs font-semibold transition-colors ${method === key ? "border-[#0284C7] bg-sky-50 text-[#0284C7]" : "border-slate-200 text-slate-600 hover:border-slate-300"}`}
    >
      <Icon size={15} /> {text}
    </button>
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md max-h-[90vh] overflow-y-auto" data-testid="payment-dialog">
        <DialogHeader>
          <DialogTitle className="font-heading">{extra ? "Agrega más mensajes" : "Habilita tu chat"}</DialogTitle>
          <DialogDescription>
            {extra ? `Continúa en el mismo caso "${item.title}" con todo tu historial.` : `Activa el chat "${item.title}" con el agente legal y contable.`}
          </DialogDescription>
        </DialogHeader>

        {error ? (
          <p className="text-sm text-red-600 bg-red-50 border border-red-200 p-4" data-testid="payment-error">{error}</p>
        ) : !offer ? (
          <p className="text-slate-400 text-xs">Calculando…</p>
        ) : (
          <div className="space-y-5">
            <div className="flex items-start gap-3 bg-sky-50 border border-sky-200 p-4" data-testid="payment-quote">
              <Scale size={18} className="text-[#0284C7] shrink-0 mt-0.5" strokeWidth={1.5} />
              <div className="flex-1">
                <p className="text-sm font-semibold text-[#0F172A]" data-testid="payment-messages">
                  {extra ? `${offer.messages} mensajes adicionales` : `Chat con ${offer.messages} mensajes`}
                </p>
                <p className="text-xs text-slate-600 mt-1">Incluye análisis de documentos, redacción de escritos e informe final en PDF.</p>
                <p className="mt-2 font-heading font-black text-xl text-[#0284C7]" data-testid="payment-total-usd">
                  US$ {offer.amount_usd.toFixed(2)}
                  <span className="text-xs font-normal text-slate-500 ml-2">≈ S/ {offer.amount_pen.toFixed(2)} (T.C. {offer.rate_pen_per_usd.toFixed(3)})</span>
                </p>
              </div>
            </div>

            {pending ? (
              <div className="bg-amber-50 border border-amber-200 p-4" data-testid="payment-pending-manual">
                <p className="flex items-center gap-2 text-sm font-semibold text-amber-800"><Clock size={15} /> Pago en verificación</p>
                <p className="text-xs text-amber-800 mt-2 leading-relaxed">
                  Registramos tu solicitud por {money(pending.currency, pending.amount)} (referencia <b>{pending.reference}</b>).
                  Tu chat se habilitará cuando confirmemos el abono. Envíanos el comprobante por WhatsApp para agilizarlo.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-3">
                {offer.paypal_client_id && methodBtn("paypal", CreditCard, "PayPal o tarjeta")}
                {methodBtn("manual", Landmark, "Depósito o transferencia")}
              </div>
            )}

            {!pending && method === "paypal" && offer.paypal_client_id && (
              <div data-testid="paypal-buttons-container">
                <PayPalScriptProvider options={{ clientId: offer.paypal_client_id, currency: "USD", intent: "capture", locale: "es_ES" }}>
                  <PayPalButtons
                    forceReRender={[offer.amount_usd]}
                    style={{ layout: "vertical", shape: "pill", label: "pay" }}
                    createOrder={createOrder}
                    onApprove={onApprove}
                    onError={() => toast.error("PayPal reportó un error. Intenta nuevamente.")}
                  />
                </PayPalScriptProvider>
                <p className="text-[11px] text-slate-400 mt-2">
                  Se cobra en dólares y tu chat se habilita al instante.{" "}
                  {offer.paypal_mode === "sandbox" && <b className="text-amber-600">Modo de prueba (sandbox) activo.</b>}
                </p>
              </div>
            )}

            {!pending && method === "manual" && (
              <div className="space-y-4" data-testid="manual-payment-panel">
                <div className="grid grid-cols-2 gap-3">
                  {["PEN", "USD"].map((c) => (
                    <button
                      key={c}
                      type="button"
                      onClick={() => setCurrency(c)}
                      data-testid={`manual-currency-${c}`}
                      className={`p-3 border text-left transition-colors ${currency === c ? "border-[#0284C7] bg-sky-50" : "border-slate-200 hover:border-slate-300"}`}
                    >
                      <p className="text-[10px] uppercase tracking-wide text-slate-500">{c === "PEN" ? "Soles" : "Dólares"}</p>
                      <p className="font-heading font-bold text-[#0F172A]">{money(c, c === "PEN" ? offer.amount_pen : offer.amount_usd)}</p>
                    </button>
                  ))}
                </div>
                <div className="bg-slate-50 border border-slate-200 p-4 text-xs text-slate-700 leading-relaxed whitespace-pre-wrap" data-testid="manual-bank-account">
                  <p className="font-semibold text-[#0F172A] mb-1">Abona {money(currency, manualAmount)} a:</p>
                  {currency === "PEN" ? offer.bank_account_pen : offer.bank_account_usd}
                </div>
                <button
                  type="button"
                  onClick={requestManual}
                  disabled={requesting}
                  data-testid="manual-request-btn"
                  className="w-full bg-[#0F172A] hover:bg-slate-800 disabled:opacity-60 text-white font-semibold py-3 rounded-full text-sm transition-colors"
                >
                  {requesting ? "Registrando…" : "Ya hice el pago — solicitar habilitación"}
                </button>
                <p className="text-[11px] text-slate-400">El equipo verifica el abono y habilita tu chat manualmente.</p>
              </div>
            )}

            {(pending || method === "manual") && offer.whatsapp_number && (
              <a
                href={`https://wa.me/${offer.whatsapp_number}?text=${encodeURIComponent(waText)}`}
                target="_blank"
                rel="noopener noreferrer"
                data-testid="manual-whatsapp-link"
                className="w-full inline-flex items-center justify-center gap-2 bg-[#25D366] hover:bg-[#1EBE5A] text-white font-semibold py-3 rounded-full text-sm transition-colors"
              >
                <MessageCircle size={16} /> Coordinar o enviar comprobante por WhatsApp
              </a>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};

export const PaymentDialog = ({ itemType = "case", item, ...rest }) =>
  itemType === "case" && item ? <CasePaymentDialog item={item} {...rest} /> : null;
