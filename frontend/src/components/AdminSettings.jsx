import { useEffect, useState } from "react";
import { KeyRound, Settings2, Building2, Save } from "lucide-react";
import { toast } from "sonner";
import { api, formatApiErrorDetail } from "@/lib/api";

const Input = ({ label, field, value, onChange, type = "text", placeholder, hint }) => (
  <div>
    <label className="text-[10px] tracking-[0.15em] uppercase text-slate-500 font-semibold">{label}</label>
    <input
      type={type}
      value={value ?? ""}
      onChange={(e) => onChange(field, e.target.value)}
      placeholder={placeholder || label}
      data-testid={`settings-${field}-input`}
      className="mt-1 w-full border border-slate-300 focus:border-[#0284C7] outline-none px-3 py-2.5 text-sm transition-colors bg-white"
    />
    {hint && <p className="text-[10px] text-slate-400 mt-1">{hint}</p>}
  </div>
);

export const AdminSettings = () => {
  const [s, setS] = useState(null);
  const [llmKey, setLlmKey] = useState("");
  const [saving, setSaving] = useState(false);
  const [pw, setPw] = useState({ current: "", next: "", confirm: "" });
  const [changingPw, setChangingPw] = useState(false);

  useEffect(() => {
    api
      .get("/admin/settings")
      .then(({ data }) => setS(data))
      .catch(() => toast.error("No se pudo cargar la configuración"));
  }, []);

  const set = (field, value) => setS((prev) => ({ ...prev, [field]: value }));

  const save = async () => {
    setSaving(true);
    try {
      const payload = {
        ai_model: s.ai_model,
        price_small: parseFloat(s.price_small) || 1100,
        price_medium: parseFloat(s.price_medium) || 2100,
        contact_email: s.contact_email,
        empresa_razon_social: s.empresa_razon_social,
        empresa_ruc: s.empresa_ruc,
        empresa_representante: s.empresa_representante,
        empresa_dni: s.empresa_dni,
        empresa_direccion: s.empresa_direccion,
        empresa_ciudad: s.empresa_ciudad,
      };
      if (llmKey.trim()) payload.llm_key = llmKey.trim();
      await api.put("/admin/settings", payload);
      toast.success("Configuración guardada. Los cambios se aplican de inmediato.");
      setLlmKey("");
      const { data } = await api.get("/admin/settings");
      setS(data);
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail));
    } finally {
      setSaving(false);
    }
  };

  const changePassword = async (e) => {
    e.preventDefault();
    if (pw.next !== pw.confirm) {
      toast.error("La nueva contraseña y su confirmación no coinciden");
      return;
    }
    setChangingPw(true);
    try {
      const { data } = await api.post("/auth/change-password", {
        current_password: pw.current,
        new_password: pw.next,
      });
      toast.success(data.message);
      setPw({ current: "", next: "", confirm: "" });
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail));
    } finally {
      setChangingPw(false);
    }
  };

  if (!s)
    return (
      <div className="bg-white border border-slate-200 p-12 flex justify-center">
        <div className="w-6 h-6 border-2 border-[#0284C7] border-t-transparent rounded-full animate-spin" />
      </div>
    );

  return (
    <div className="grid lg:grid-cols-3 gap-6">
      {/* Cambio de contraseña */}
      <div className="bg-white border border-slate-200 p-6 h-fit">
        <div className="flex items-center gap-3">
          <KeyRound className="text-[#0284C7]" size={22} strokeWidth={1.5} />
          <h3 className="font-heading font-bold text-[#0F172A]">Cambiar contraseña</h3>
        </div>
        <form onSubmit={changePassword} className="mt-5 space-y-4">
          <div>
            <label className="text-[10px] tracking-[0.15em] uppercase text-slate-500 font-semibold">Contraseña actual</label>
            <input
              required
              type="password"
              value={pw.current}
              onChange={(e) => setPw({ ...pw, current: e.target.value })}
              data-testid="password-current-input"
              className="mt-1 w-full border border-slate-300 focus:border-[#0284C7] outline-none px-3 py-2.5 text-sm transition-colors"
            />
          </div>
          <div>
            <label className="text-[10px] tracking-[0.15em] uppercase text-slate-500 font-semibold">Nueva contraseña</label>
            <input
              required
              type="password"
              minLength={6}
              value={pw.next}
              onChange={(e) => setPw({ ...pw, next: e.target.value })}
              data-testid="password-new-input"
              className="mt-1 w-full border border-slate-300 focus:border-[#0284C7] outline-none px-3 py-2.5 text-sm transition-colors"
            />
          </div>
          <div>
            <label className="text-[10px] tracking-[0.15em] uppercase text-slate-500 font-semibold">Confirmar nueva contraseña</label>
            <input
              required
              type="password"
              minLength={6}
              value={pw.confirm}
              onChange={(e) => setPw({ ...pw, confirm: e.target.value })}
              data-testid="password-confirm-input"
              className="mt-1 w-full border border-slate-300 focus:border-[#0284C7] outline-none px-3 py-2.5 text-sm transition-colors"
            />
          </div>
          <button
            type="submit"
            disabled={changingPw}
            data-testid="change-password-btn"
            className="w-full bg-[#0F172A] hover:bg-slate-800 disabled:opacity-60 text-white font-semibold py-3 rounded-full text-sm transition-colors"
          >
            {changingPw ? "Actualizando…" : "Actualizar contraseña"}
          </button>
        </form>
      </div>

      {/* Variables de la plataforma */}
      <div className="lg:col-span-2 space-y-6">
        <div className="bg-white border border-slate-200 p-6">
          <div className="flex items-center gap-3">
            <Settings2 className="text-[#0284C7]" size={22} strokeWidth={1.5} />
            <h3 className="font-heading font-bold text-[#0F172A]">Variables de la plataforma</h3>
          </div>
          <p className="text-xs text-slate-500 mt-2 leading-relaxed">
            Estos valores se aplican de inmediato en toda la plataforma sin necesidad de tocar
            código: la clave de IA se usa en los análisis y clasificaciones, y los precios se
            reflejan en el landing.
          </p>
          <div className="mt-5 grid sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <label className="text-[10px] tracking-[0.15em] uppercase text-slate-500 font-semibold">API Key de IA (Emergent LLM Key)</label>
              <input
                type="text"
                value={llmKey}
                onChange={(e) => setLlmKey(e.target.value)}
                placeholder={s.llm_key_masked ? `Actual: ${s.llm_key_masked} — escribe aquí para reemplazarla` : "sk-emergent-…"}
                data-testid="settings-llm_key-input"
                className="mt-1 w-full border border-slate-300 focus:border-[#0284C7] outline-none px-3 py-2.5 text-sm transition-colors font-mono"
              />
              <p className="text-[10px] text-slate-400 mt-1">
                Déjalo vacío para mantener la clave actual. Se usa para el análisis y la clasificación con Gemini.
              </p>
            </div>
            <Input label="Modelo de IA" field="ai_model" value={s.ai_model} onChange={set} hint="Ej.: gemini-3.1-pro-preview" />
            <Input label="Email de contacto" field="contact_email" value={s.contact_email} onChange={set} />
            <Input label="Precio plan pequeño (S/, <50 dptos.)" field="price_small" value={s.price_small} onChange={set} />
            <Input label="Precio plan mediano-grande (S/, 50-150)" field="price_medium" value={s.price_medium} onChange={set} />
          </div>
        </div>

        <div className="bg-white border border-slate-200 p-6">
          <div className="flex items-center gap-3">
            <Building2 className="text-[#0284C7]" size={22} strokeWidth={1.5} />
            <h3 className="font-heading font-bold text-[#0F172A]">Datos de OnBuySolutions S.A.C.</h3>
          </div>
          <p className="text-xs text-slate-500 mt-2 leading-relaxed">
            Se usan para pre-llenar automáticamente el generador de documentos (contratos, propuestas, recibos).
          </p>
          <div className="mt-5 grid sm:grid-cols-2 gap-4">
            <Input label="Razón social" field="empresa_razon_social" value={s.empresa_razon_social} onChange={set} />
            <Input label="RUC" field="empresa_ruc" value={s.empresa_ruc} onChange={set} placeholder="20XXXXXXXXX" />
            <Input label="Representante legal" field="empresa_representante" value={s.empresa_representante} onChange={set} />
            <Input label="DNI del representante" field="empresa_dni" value={s.empresa_dni} onChange={set} />
            <Input label="Dirección fiscal" field="empresa_direccion" value={s.empresa_direccion} onChange={set} />
            <Input label="Ciudad" field="empresa_ciudad" value={s.empresa_ciudad} onChange={set} />
          </div>
        </div>

        <button
          onClick={save}
          disabled={saving}
          data-testid="settings-save-btn"
          className="inline-flex items-center gap-2 bg-[#0284C7] hover:bg-[#0EA5E9] disabled:opacity-60 text-white font-semibold px-8 py-3.5 rounded-full text-sm transition-colors"
        >
          <Save size={16} />
          {saving ? "Guardando…" : "Guardar configuración"}
        </button>
      </div>
    </div>
  );
};
