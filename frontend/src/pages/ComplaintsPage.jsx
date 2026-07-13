import { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, BookOpenCheck, Download, CheckCircle2, Loader2 } from "lucide-react";
import { toast } from "sonner";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { api, BACKEND_URL, formatApiErrorDetail } from "@/lib/api";
import { ThemeToggle } from "@/components/ThemeToggle";

const initial = {
  consumer_name: "",
  doc_type: "DNI",
  doc_number: "",
  address: "",
  phone: "",
  email: "",
  item_type: "Servicio",
  amount: "",
  service_description: "",
  request_type: "Reclamo",
  detail: "",
  consumer_request: "",
  accepted_declaration: false,
};

const Field = ({ label, children, required = true }) => (
  <div>
    <label className="text-[10px] tracking-[0.15em] uppercase text-slate-500 font-semibold">
      {label} {required && <span className="text-red-500">*</span>}
    </label>
    <div className="mt-1">{children}</div>
  </div>
);

const inputCls =
  "w-full border border-slate-300 focus:border-[#0284C7] outline-none px-3 py-2.5 text-sm transition-colors bg-white";

const Section = ({ number, title, children }) => (
  <div className="border border-slate-200 bg-white">
    <div className="bg-[#0F172A] px-5 py-3">
      <h2 className="text-white font-heading font-bold text-sm">
        {number}. {title}
      </h2>
    </div>
    <div className="p-5 grid sm:grid-cols-2 gap-4">{children}</div>
  </div>
);

export default function ComplaintsPage() {
  const [f, setF] = useState(initial);
  const [sending, setSending] = useState(false);
  const [result, setResult] = useState(null);

  const set = (field, value) => setF((prev) => ({ ...prev, [field]: value }));

  const submit = async (e) => {
    e.preventDefault();
    if (!f.accepted_declaration) {
      toast.error("Debes aceptar la declaración para registrar tu solicitud");
      return;
    }
    setSending(true);
    try {
      const payload = { ...f, amount: f.amount ? parseFloat(f.amount) : null };
      const { data } = await api.post("/complaints", payload);
      setResult(data);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail));
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="themeable min-h-screen bg-[#F8FAFC]">
      <header className="bg-[#020617] py-4">
        <div className="max-w-4xl mx-auto px-6 flex items-center justify-between">
          <Link to="/" className="font-heading font-black text-white text-lg" data-testid="complaints-logo-link">
            OnBuy<span className="text-[#0EA5E9]">Solutions</span>
          </Link>
          <div className="flex items-center gap-4">
            <ThemeToggle onDark />
            <Link
              to="/"
              className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors"
              data-testid="complaints-back-link"
            >
              <ArrowLeft size={14} /> Volver al inicio
            </Link>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-10">
        {result ? (
          <div className="bg-white border border-slate-200 p-8 sm:p-12 text-center" data-testid="complaint-success">
            <CheckCircle2 className="mx-auto text-emerald-500" size={52} strokeWidth={1.2} />
            <h1 className="font-heading font-black text-2xl text-[#0F172A] mt-5">Solicitud registrada</h1>
            <p className="text-sm text-slate-500 mt-3 max-w-lg mx-auto leading-relaxed">
              Tu hoja de reclamación fue registrada correctamente. Enviamos una copia con la constancia de
              fecha y hora de recepción a tu correo electrónico.
            </p>
            <div className="mt-6 inline-block bg-[#F8FAFC] border border-slate-200 px-8 py-5 text-left">
              <p className="text-[10px] tracking-[0.15em] uppercase text-slate-400 font-semibold">Número de reclamo</p>
              <p className="font-heading font-black text-2xl text-[#0284C7]" data-testid="complaint-code">{result.code}</p>
              <p className="text-xs text-slate-500 mt-2">
                Fecha de recepción: {new Date(result.created_at).toLocaleString("es-PE")}
                <br />
                Plazo máximo de respuesta: <b>{result.due_date_display}</b> (15 días hábiles)
              </p>
            </div>
            <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3">
              <a
                href={`${BACKEND_URL}/api/complaints/${result.id}/receipt`}
                data-testid="complaint-download-receipt"
                className="inline-flex items-center gap-2 bg-[#0284C7] hover:bg-[#0EA5E9] text-white font-semibold px-7 py-3 rounded-full text-sm transition-colors"
              >
                <Download size={15} /> Descargar constancia (PDF)
              </a>
              <Link
                to="/"
                className="inline-flex items-center gap-2 border border-slate-300 hover:border-[#0284C7] hover:text-[#0284C7] text-slate-500 font-semibold px-7 py-3 rounded-full text-sm transition-colors"
              >
                Volver al inicio
              </Link>
            </div>
          </div>
        ) : (
          <>
            <div className="flex items-start gap-4">
              <img src="/libro-reclamaciones.png" alt="Libro de Reclamaciones" className="w-14 h-14 object-contain bg-[#0F172A] rounded p-1.5" />
              <div>
                <h1 className="font-heading font-black text-2xl sm:text-3xl text-[#0F172A]">Libro de Reclamaciones</h1>
                <p className="text-xs text-slate-500 mt-1">Hoja de Reclamación Virtual — D.S. N° 011-2011-PCM y modificatorias</p>
              </div>
            </div>

            <div className="mt-6 bg-white border border-slate-200 p-5 text-xs text-slate-600 leading-relaxed" data-testid="complaint-provider-info">
              <p><b>Razón Social:</b> ONBUYSOLUTIONS S.A.C. &nbsp;·&nbsp; <b>RUC:</b> 20606439327</p>
              <p className="mt-1"><b>Dirección:</b> Parque Rospigliosi 153, Pueblo Libre, Lima, Perú</p>
              <p className="mt-1"><b>Plataforma / Marca Comercial:</b> OnBuySolutions — www.onbuysolutions.com</p>
              <p className="mt-3 text-slate-500 italic">
                La formulación del reclamo no impide acudir a otras vías de solución de controversias ni es
                requisito previo para interponer una denuncia ante el INDECOPI. Responderemos tu solicitud en un
                plazo máximo de 15 días hábiles improrrogables (Ley N° 31435).
              </p>
            </div>

            <form onSubmit={submit} className="mt-6 space-y-6">
              <Section number="1" title="IDENTIFICACIÓN DEL CONSUMIDOR RECLAMANTE">
                <div className="sm:col-span-2">
                  <Field label="Nombres y Apellidos / Razón Social">
                    <input required minLength={3} value={f.consumer_name} onChange={(e) => set("consumer_name", e.target.value)} className={inputCls} data-testid="complaint-name-input" />
                  </Field>
                </div>
                <Field label="Tipo de Documento">
                  <Select value={f.doc_type} onValueChange={(v) => set("doc_type", v)}>
                    <SelectTrigger className="w-full" data-testid="complaint-doctype-select"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="DNI">DNI</SelectItem>
                      <SelectItem value="CE">Carné de Extranjería (CE)</SelectItem>
                      <SelectItem value="RUC">RUC</SelectItem>
                      <SelectItem value="Pasaporte">Pasaporte</SelectItem>
                    </SelectContent>
                  </Select>
                </Field>
                <Field label="Número de Documento">
                  <input required minLength={6} maxLength={15} value={f.doc_number} onChange={(e) => set("doc_number", e.target.value.replace(/[^\dA-Za-z]/g, ""))} className={inputCls} data-testid="complaint-docnumber-input" />
                </Field>
                <div className="sm:col-span-2">
                  <Field label="Domicilio (Dirección completa)">
                    <input required minLength={5} value={f.address} onChange={(e) => set("address", e.target.value)} className={inputCls} data-testid="complaint-address-input" />
                  </Field>
                </div>
                <Field label="Teléfono / Celular">
                  <input required minLength={6} maxLength={15} value={f.phone} onChange={(e) => set("phone", e.target.value.replace(/[^\d+ ]/g, ""))} className={inputCls} data-testid="complaint-phone-input" />
                </Field>
                <Field label="Correo Electrónico">
                  <input required type="email" value={f.email} onChange={(e) => set("email", e.target.value)} className={inputCls} data-testid="complaint-email-input" />
                </Field>
              </Section>

              <Section number="2" title="IDENTIFICACIÓN DEL BIEN CONTRATADO">
                <Field label="Tipo">
                  <Select value={f.item_type} onValueChange={(v) => set("item_type", v)}>
                    <SelectTrigger className="w-full" data-testid="complaint-itemtype-select"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Producto">Producto</SelectItem>
                      <SelectItem value="Servicio">Servicio</SelectItem>
                    </SelectContent>
                  </Select>
                </Field>
                <Field label="Monto Reclamado (S/)" required={false}>
                  <input type="number" min="0" step="0.01" value={f.amount} onChange={(e) => set("amount", e.target.value)} className={inputCls} placeholder="Opcional" data-testid="complaint-amount-input" />
                </Field>
                <div className="sm:col-span-2">
                  <Field label="Descripción del producto o servicio contratado">
                    <input required minLength={5} value={f.service_description} onChange={(e) => set("service_description", e.target.value)} className={inputCls} placeholder="Ej.: Auditoría financiera de condominio — Plan Pequeño" data-testid="complaint-description-input" />
                  </Field>
                </div>
              </Section>

              <Section number="3" title="DETALLE DE LA RECLAMACIÓN Y PEDIDO DEL CONSUMIDOR">
                <div className="sm:col-span-2">
                  <Field label="Tipo de Solicitud">
                    <Select value={f.request_type} onValueChange={(v) => set("request_type", v)}>
                      <SelectTrigger className="w-full" data-testid="complaint-requesttype-select"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Reclamo">Reclamo — Disconformidad relacionada a los productos o servicios</SelectItem>
                        <SelectItem value="Queja">Queja — Disconformidad no relacionada a los productos o servicios; malestar respecto a la atención al público</SelectItem>
                      </SelectContent>
                    </Select>
                  </Field>
                </div>
                <div className="sm:col-span-2">
                  <Field label="Detalle del Reclamo o Queja">
                    <textarea required minLength={10} rows={4} value={f.detail} onChange={(e) => set("detail", e.target.value)} className={`${inputCls} resize-none`} data-testid="complaint-detail-input" />
                  </Field>
                </div>
                <div className="sm:col-span-2">
                  <Field label="Pedido del Consumidor (¿Qué solicita?)">
                    <textarea required minLength={5} rows={3} value={f.consumer_request} onChange={(e) => set("consumer_request", e.target.value)} className={`${inputCls} resize-none`} data-testid="complaint-request-input" />
                  </Field>
                </div>
              </Section>

              <Section number="4" title="DECLARACIÓN DEL CONSUMIDOR">
                <div className="sm:col-span-2">
                  <label className="flex items-start gap-3 cursor-pointer" data-testid="complaint-declaration-label">
                    <input
                      type="checkbox"
                      checked={f.accepted_declaration}
                      onChange={(e) => set("accepted_declaration", e.target.checked)}
                      className="mt-0.5 w-4 h-4 accent-[#0284C7]"
                      data-testid="complaint-declaration-checkbox"
                    />
                    <span className="text-xs text-slate-600 leading-relaxed">
                      Declaro que los datos consignados son correctos y se ajustan a la verdad. Acepto la{" "}
                      <Link to="/privacidad" target="_blank" className="text-[#0284C7] hover:underline">
                        Política de Privacidad
                      </Link>{" "}
                      para el tratamiento de mis datos personales en la gestión de esta solicitud. Al enviar,
                      recibiré automáticamente una copia de esta hoja en el correo electrónico indicado, con
                      constancia de la fecha y hora de recepción.
                    </span>
                  </label>
                </div>
              </Section>

              <button
                type="submit"
                disabled={sending}
                data-testid="complaint-submit-btn"
                className="w-full inline-flex items-center justify-center gap-2 bg-[#0284C7] hover:bg-[#0EA5E9] disabled:opacity-60 text-white font-bold py-4 rounded-full text-sm transition-colors"
              >
                {sending ? (
                  <>
                    <Loader2 className="animate-spin" size={16} /> Registrando…
                  </>
                ) : (
                  <>
                    <BookOpenCheck size={16} /> Enviar Hoja de Reclamación
                  </>
                )}
              </button>
            </form>
          </>
        )}
      </main>

      <footer className="py-8 text-center">
        <p className="text-[11px] text-slate-400 max-w-2xl mx-auto px-6 leading-relaxed">
          ONBUYSOLUTIONS S.A.C. — RUC 20606439327. Las hojas de reclamación se conservan por un mínimo de dos
          (2) años conforme al reglamento del Libro de Reclamaciones. Tratamiento de datos según la Ley N° 29733
          y D.S. N° 016-2024-JUS.
        </p>
      </footer>
    </div>
  );
}
