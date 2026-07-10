import { useState, useEffect } from "react";
import { FileSignature, Download, Building2, Briefcase } from "lucide-react";
import { toast } from "sonner";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { api, BACKEND_URL, formatApiErrorDetail } from "@/lib/api";

const DOC_TYPES = [
  { value: "propuesta", label: "Propuesta comercial de venta" },
  { value: "contrato", label: "Contrato de prestación de servicios" },
  { value: "confidencialidad", label: "Acuerdo de confidencialidad (NDA)" },
  { value: "tratamiento_datos", label: "Acuerdo de encargo de tratamiento de datos (Ley 29733)" },
  { value: "autorizacion_bancaria", label: "Autorización de entrega de información bancaria" },
  { value: "recibo", label: "Recibo de pago" },
];

const today = new Date().toLocaleDateString("es-PE");

const initialFields = {
  empresa_razon_social: "OnBuySolutions S.A.C.",
  empresa_ruc: "",
  empresa_representante: "",
  empresa_dni: "",
  empresa_direccion: "",
  cliente_nombre: "",
  cliente_ruc: "",
  cliente_representante: "",
  cliente_dni: "",
  cliente_cargo: "Presidente de la Junta de Propietarios",
  cliente_direccion: "",
  cliente_distrito: "",
  num_departamentos: "",
  plan: "pequeno",
  monto: "1100",
  periodo: "",
  ciudad: "Lima",
  fecha: today,
  forma_pago: "Transferencia bancaria",
  plazo_entrega: "7 días hábiles",
  validez_dias: "15",
  vigencia_anios: "5",
  recibo_numero: "",
  concepto: "Servicio de auditoría de condominio asistida por IA",
  fecha_pago: today,
};

const Input = ({ label, field, value, onChange, placeholder, testid }) => (
  <div>
    <label className="text-[10px] tracking-[0.15em] uppercase text-slate-500 font-semibold">{label}</label>
    <input
      value={value}
      onChange={(e) => onChange(field, e.target.value)}
      placeholder={placeholder || label}
      data-testid={testid || `docgen-${field}-input`}
      className="mt-1 w-full border border-slate-300 focus:border-[#0284C7] outline-none px-3 py-2.5 text-sm transition-colors bg-white"
    />
  </div>
);

const SectionTitle = ({ icon: Icon, children }) => (
  <div className="flex items-center gap-2 mt-8 mb-4">
    <Icon className="text-[#0284C7]" size={16} strokeWidth={1.8} />
    <h4 className="font-heading font-bold text-sm text-[#0F172A] tracking-wide">{children}</h4>
    <div className="flex-1 border-t border-slate-200 ml-2" />
  </div>
);

export const AdminDocGenerator = () => {
  const [docType, setDocType] = useState("propuesta");
  const [f, setF] = useState(initialFields);
  const [generating, setGenerating] = useState(false);
  const [prices, setPrices] = useState({ small: 1100, medium: 2100 });

  useEffect(() => {
    api
      .get("/admin/settings")
      .then(({ data }) => {
        setPrices({ small: data.price_small, medium: data.price_medium });
        setF((prev) => ({
          ...prev,
          empresa_razon_social: data.empresa_razon_social || prev.empresa_razon_social,
          empresa_ruc: data.empresa_ruc || prev.empresa_ruc,
          empresa_representante: data.empresa_representante || prev.empresa_representante,
          empresa_dni: data.empresa_dni || prev.empresa_dni,
          empresa_direccion: data.empresa_direccion || prev.empresa_direccion,
          ciudad: data.empresa_ciudad || prev.ciudad,
          monto: prev.plan === "mediano" ? String(data.price_medium) : String(data.price_small),
        }));
      })
      .catch(() => {});
  }, []);

  const set = (field, value) => setF((prev) => ({ ...prev, [field]: value }));

  const setPlan = (plan) =>
    setF((prev) => ({ ...prev, plan, monto: String(plan === "mediano" ? prices.medium : prices.small) }));

  const generate = async () => {
    setGenerating(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/admin/documents/generate`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ doc_type: docType, fields: f }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(formatApiErrorDetail(err.detail) || "No se pudo generar el documento");
      }
      const cd = res.headers.get("Content-Disposition") || "";
      const match = cd.match(/filename="(.+)"/);
      const filename = match ? match[1] : `${docType}.pdf`;
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      toast.success("Documento PDF generado y descargado");
    } catch (err) {
      toast.error(err.message);
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="grid lg:grid-cols-3 gap-6">
      <div className="bg-white border border-slate-200 p-6 h-fit">
        <div className="flex items-center gap-3">
          <FileSignature className="text-[#0284C7]" size={24} strokeWidth={1.5} />
          <h3 className="font-heading font-bold text-[#0F172A]">Generador de documentos</h3>
        </div>
        <p className="text-xs text-slate-500 mt-3 leading-relaxed">
          Genera los documentos entre OnBuySolutions S.A.C. y el cliente (condominio), listos en PDF
          para imprimir y firmar. Los campos vacíos aparecerán como líneas en blanco para completar a
          mano.
        </p>
        <div className="mt-5">
          <label className="text-[10px] tracking-[0.15em] uppercase text-slate-500 font-semibold">
            Tipo de documento
          </label>
          <Select value={docType} onValueChange={setDocType}>
            <SelectTrigger className="mt-1 w-full" data-testid="docgen-type-select">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {DOC_TYPES.map((d) => (
                <SelectItem key={d.value} value={d.value} data-testid={`docgen-type-${d.value}`}>
                  {d.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <button
          onClick={generate}
          disabled={generating}
          data-testid="docgen-generate-btn"
          className="mt-6 w-full inline-flex items-center justify-center gap-2 bg-[#0284C7] hover:bg-[#0EA5E9] disabled:opacity-60 text-white font-semibold py-3.5 rounded-full text-sm transition-colors"
        >
          <Download size={16} />
          {generating ? "Generando PDF…" : "Generar y descargar PDF"}
        </button>
        <p className="text-[10px] text-slate-400 mt-4 leading-relaxed">
          Plantillas basadas en la normativa peruana vigente (Ley 29733, D.S. 016-2024-JUS, Ley 31814,
          D.S. 115-2025-PCM, Ley 26702). Se recomienda revisión legal antes de la firma.
        </p>
      </div>

      <div className="lg:col-span-2 bg-white border border-slate-200 p-6 lg:p-8">
        <SectionTitle icon={Briefcase}>Datos de OnBuySolutions (La Empresa)</SectionTitle>
        <div className="grid sm:grid-cols-2 gap-4">
          <Input label="Razón social" field="empresa_razon_social" value={f.empresa_razon_social} onChange={set} />
          <Input label="RUC" field="empresa_ruc" value={f.empresa_ruc} onChange={set} placeholder="20XXXXXXXXX" />
          <Input label="Representante legal" field="empresa_representante" value={f.empresa_representante} onChange={set} />
          <Input label="DNI del representante" field="empresa_dni" value={f.empresa_dni} onChange={set} />
          <div className="sm:col-span-2">
            <Input label="Dirección fiscal" field="empresa_direccion" value={f.empresa_direccion} onChange={set} />
          </div>
        </div>

        <SectionTitle icon={Building2}>Datos del cliente (Condominio / Junta)</SectionTitle>
        <div className="grid sm:grid-cols-2 gap-4">
          <div className="sm:col-span-2">
            <Input label="Nombre / Razón social" field="cliente_nombre" value={f.cliente_nombre} onChange={set} placeholder="Junta de Propietarios del Condominio…" />
          </div>
          <Input label="RUC del cliente" field="cliente_ruc" value={f.cliente_ruc} onChange={set} />
          <Input label="N° de departamentos" field="num_departamentos" value={f.num_departamentos} onChange={set} />
          <Input label="Representante" field="cliente_representante" value={f.cliente_representante} onChange={set} />
          <Input label="DNI del representante" field="cliente_dni" value={f.cliente_dni} onChange={set} />
          <Input label="Cargo" field="cliente_cargo" value={f.cliente_cargo} onChange={set} />
          <Input label="Distrito / Ciudad" field="cliente_distrito" value={f.cliente_distrito} onChange={set} />
          <div className="sm:col-span-2">
            <Input label="Dirección del condominio" field="cliente_direccion" value={f.cliente_direccion} onChange={set} />
          </div>
        </div>

        <SectionTitle icon={FileSignature}>Datos del servicio y del documento</SectionTitle>
        <div className="grid sm:grid-cols-2 gap-4">
          <div>
            <label className="text-[10px] tracking-[0.15em] uppercase text-slate-500 font-semibold">Plan</label>
            <Select value={f.plan} onValueChange={setPlan}>
              <SelectTrigger className="mt-1 w-full" data-testid="docgen-plan-select">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="pequeno" data-testid="docgen-plan-pequeno">Pequeño (&lt;50 dptos.) — S/ 1,100</SelectItem>
                <SelectItem value="mediano" data-testid="docgen-plan-mediano">Mediano a grande (50–150) — S/ 2,100</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <Input label="Monto (S/)" field="monto" value={f.monto} onChange={set} />
          <Input label="Período a auditar" field="periodo" value={f.periodo} onChange={set} placeholder="Enero - Diciembre 2025" />
          <Input label="Fecha del documento" field="fecha" value={f.fecha} onChange={set} />
          <Input label="Ciudad" field="ciudad" value={f.ciudad} onChange={set} />
          <Input label="Forma de pago" field="forma_pago" value={f.forma_pago} onChange={set} />
          {docType === "propuesta" && (
            <>
              <Input label="Validez de la oferta (días)" field="validez_dias" value={f.validez_dias} onChange={set} />
              <Input label="Plazo de entrega" field="plazo_entrega" value={f.plazo_entrega} onChange={set} />
            </>
          )}
          {docType === "contrato" && (
            <Input label="Plazo de entrega" field="plazo_entrega" value={f.plazo_entrega} onChange={set} />
          )}
          {docType === "confidencialidad" && (
            <Input label="Vigencia de confidencialidad (años)" field="vigencia_anios" value={f.vigencia_anios} onChange={set} />
          )}
          {docType === "recibo" && (
            <>
              <Input label="N° de recibo" field="recibo_numero" value={f.recibo_numero} onChange={set} placeholder="001-2026" />
              <Input label="Fecha de pago" field="fecha_pago" value={f.fecha_pago} onChange={set} />
              <div className="sm:col-span-2">
                <Input label="Concepto" field="concepto" value={f.concepto} onChange={set} />
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
