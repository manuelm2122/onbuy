import { useState } from "react";
import { Calculator, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { api, formatApiErrorDetail } from "@/lib/api";

const PAGOS_HINT = "Un pago por línea: AAAA-MM monto. Ej.: 2025-03 500";

const CALCS = {
  beneficios: {
    label: "Beneficios sociales (liquidación al cese)",
    fields: [
      { k: "fecha_ingreso", label: "Fecha de ingreso", type: "date", required: true },
      { k: "fecha_cese", label: "Fecha de cese", type: "date", required: true },
      { k: "sueldo", label: "Remuneración mensual (S/)", type: "number", required: true },
      { k: "vacaciones_pendientes_dias", label: "Días de vacaciones no gozadas", type: "number" },
      { k: "asignacion_familiar", label: "Percibe asignación familiar", type: "checkbox" },
      { k: "despido_arbitrario", label: "Incluir indemnización por despido arbitrario", type: "checkbox" },
    ],
  },
  intereses: {
    label: "Intereses legales de una deuda",
    fields: [
      { k: "capital", label: "Capital adeudado (S/)", type: "number", required: true },
      { k: "tipo", label: "Tipo de interés", type: "select", options: [["efectiva", "Legal efectiva (deudas civiles)"], ["laboral", "Legal laboral (deudas laborales)"]] },
      { k: "fecha_inicio", label: "Desde", type: "date", required: true },
      { k: "fecha_fin", label: "Hasta", type: "date", required: true },
      { k: "factor_inicio", label: "Factor acumulado SBS inicial", type: "number", hint: "Opcional. Resultado exacto: sbs.gob.pe → Tasa de interés legal" },
      { k: "factor_fin", label: "Factor acumulado SBS final", type: "number" },
      { k: "tasa_anual", label: "Tasa legal anual (%)", type: "number", hint: "Solo si no ingresas los factores (resultado aproximado)" },
    ],
  },
  alimentos: {
    label: "Pensiones de alimentos devengadas",
    fields: [
      { k: "monto_mensual", label: "Pensión mensual (S/)", type: "number", required: true },
      { k: "mes_inicio", label: "Primer mes adeudado", type: "month", required: true },
      { k: "mes_fin", label: "Último mes a liquidar", type: "month", required: true },
      { k: "pagos", label: "Pagos realizados", type: "textarea", hint: PAGOS_HINT },
    ],
  },
  alquileres: {
    label: "Alquileres impagos",
    fields: [
      { k: "renta_mensual", label: "Renta mensual", type: "number", required: true },
      { k: "moneda", label: "Moneda", type: "select", options: [["PEN", "Soles (S/)"], ["USD", "Dólares (US$)"]] },
      { k: "mes_inicio", label: "Primer mes adeudado", type: "month", required: true },
      { k: "mes_fin", label: "Último mes a liquidar", type: "month", required: true },
      { k: "penalidad_mensual", label: "Penalidad pactada por mes impago", type: "number" },
      { k: "garantia", label: "Garantía a descontar", type: "number" },
      { k: "pagos", label: "Pagos realizados", type: "textarea", hint: PAGOS_HINT },
    ],
  },
};

const inputCls = "mt-1 w-full border border-slate-300 focus:border-[#0284C7] outline-none px-3 py-2 text-sm transition-colors bg-white";

const Field = ({ f, value, onChange }) => {
  const testId = `calc-field-${f.k}`;
  if (f.type === "checkbox")
    return (
      <label className="sm:col-span-2 flex items-center gap-2 text-sm text-slate-700">
        <input type="checkbox" checked={!!value} onChange={(e) => onChange(e.target.checked)} data-testid={testId} /> {f.label}
      </label>
    );
  return (
    <div className={f.type === "textarea" ? "sm:col-span-2" : ""}>
      <label className="text-[10px] tracking-[0.15em] uppercase text-slate-500 font-semibold">{f.label}{f.required ? " *" : ""}</label>
      {f.type === "select" ? (
        <select value={value ?? f.options[0][0]} onChange={(e) => onChange(e.target.value)} data-testid={testId} className={inputCls}>
          {f.options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
      ) : f.type === "textarea" ? (
        <textarea rows={3} value={value ?? ""} onChange={(e) => onChange(e.target.value)} data-testid={testId} className={`${inputCls} resize-y font-mono`} />
      ) : (
        <input type={f.type} step="any" min={f.type === "number" ? 0 : undefined} required={f.required} value={value ?? ""} onChange={(e) => onChange(e.target.value)} data-testid={testId} className={inputCls} />
      )}
      {f.hint && <p className="text-[10px] text-slate-400 mt-1">{f.hint}</p>}
    </div>
  );
};

export const CaseCalculators = ({ caseId, open, onOpenChange, onDone }) => {
  const [type, setType] = useState("beneficios");
  const [inputs, setInputs] = useState({});
  const [busy, setBusy] = useState(false);

  const usePayments = async () => {
    try {
      const { data } = await api.get(`/cases/${caseId}/ledger`);
      const byMonth = {};
      data.entries.filter((e) => e.type === "pago").forEach((e) => {
        byMonth[e.date.slice(0, 7)] = (byMonth[e.date.slice(0, 7)] || 0) + e.amount;
      });
      const lines = Object.entries(byMonth).map(([m, v]) => `${m} ${v.toFixed(2)}`);
      if (!lines.length) return toast.info("No hay pagos en el registro de pagos y deudas");
      setInputs((p) => ({ ...p, pagos: lines.join("\n") }));
      toast.success(`${lines.length} mes(es) con pagos cargados desde tu registro`);
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail));
    }
  };

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const { data } = await api.post(`/cases/${caseId}/calculations`, { type, inputs });
      toast.success(`${data.title}: resultado añadido al expediente`);
      setInputs({});
      onOpenChange(false);
      onDone();
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-heading text-xl">Calculadoras del expediente</DialogTitle>
          <DialogDescription>
            Cálculo exacto por fórmula, no por IA. El resultado se añade a la conversación del caso, puedes exportarlo a PDF y el agente lo tendrá en cuenta. No descuenta mensajes.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="mt-2 space-y-4" data-testid="calc-form">
          <select value={type} onChange={(e) => { setType(e.target.value); setInputs({}); }} data-testid="calc-type-select" className={inputCls}>
            {Object.entries(CALCS).map(([k, c]) => <option key={k} value={k}>{c.label}</option>)}
          </select>
          <div className="grid sm:grid-cols-2 gap-4">
            {CALCS[type].fields.map((f) => (
              <Field key={`${type}-${f.k}`} f={f} value={inputs[f.k]} onChange={(v) => setInputs((p) => ({ ...p, [f.k]: v }))} />
            ))}
          </div>
          {CALCS[type].fields.some((f) => f.k === "pagos") && (
            <button type="button" onClick={usePayments} data-testid="calc-use-payments-btn" className="text-xs font-semibold text-[#0284C7] hover:underline">
              Usar los pagos de mi registro de pagos y deudas
            </button>
          )}
          <button type="submit" disabled={busy} data-testid="calc-submit-btn" className="w-full inline-flex items-center justify-center gap-2 bg-[#0284C7] hover:bg-[#0EA5E9] disabled:opacity-60 text-white font-semibold py-3 rounded-full text-sm transition-colors">
            {busy ? <Loader2 className="animate-spin" size={15} /> : <Calculator size={15} />} Calcular y añadir al expediente
          </button>
        </form>
      </DialogContent>
    </Dialog>
  );
};
