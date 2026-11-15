import { useEffect, useState } from "react";
import { KeyRound, Settings2, Building2, Save, MessageCircle } from "lucide-react";
import { toast } from "sonner";
import { api, formatApiErrorDetail } from "@/lib/api";
import { BackupPanel } from "@/components/BackupPanel";

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
  const [googleKey, setGoogleKey] = useState("");
  const [vertexJson, setVertexJson] = useState("");
  const [resendKey, setResendKey] = useState("");
  const [paypalSecret, setPaypalSecret] = useState("");
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
        price_consulting: parseFloat(s.price_consulting) || 30,
        consulting_budget_usd: parseFloat(s.consulting_budget_usd) || 3.5,
        contact_email: s.contact_email,
        empresa_razon_social: s.empresa_razon_social,
        empresa_ruc: s.empresa_ruc,
        empresa_representante: s.empresa_representante,
        empresa_dni: s.empresa_dni,
        empresa_direccion: s.empresa_direccion,
        empresa_ciudad: s.empresa_ciudad,
      };
      payload.llm_provider = s.llm_provider || "emergent";
      payload.whatsapp_enabled = !!s.whatsapp_enabled;
      payload.whatsapp_number = s.whatsapp_number || "";
      payload.whatsapp_message = s.whatsapp_message || "";
      if (llmKey.trim()) payload.llm_key = llmKey.trim();
      if (googleKey.trim()) payload.google_api_key = googleKey.trim();
      if (vertexJson.trim()) payload.vertex_service_account_json = vertexJson.trim();
      if (s.vertex_project) payload.vertex_project = s.vertex_project;
      if (s.vertex_location) payload.vertex_location = s.vertex_location;
      if (resendKey.trim()) payload.resend_api_key = resendKey.trim();
      if (paypalSecret.trim()) payload.paypal_secret = paypalSecret.trim();
      payload.resend_sender = s.resend_sender;
      payload.complaints_notify_email = s.complaints_notify_email;
      payload.paypal_client_id = s.paypal_client_id;
      payload.paypal_mode = s.paypal_mode;
      await api.put("/admin/settings", payload);
      toast.success("Configuración guardada. Los cambios se aplican de inmediato.");
      setLlmKey("");
      setGoogleKey("");
      setVertexJson("");
      setResendKey("");
      setPaypalSecret("");
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
              <label className="text-[10px] tracking-[0.15em] uppercase text-slate-500 font-semibold">Proveedor de IA activo</label>
              <select
                value={s.llm_provider || "emergent"}
                onChange={(e) => set("llm_provider", e.target.value)}
                data-testid="settings-llm_provider-select"
                className="mt-1 w-full border border-slate-300 focus:border-[#0284C7] outline-none px-3 py-2.5 text-sm transition-colors bg-white"
              >
                <option value="emergent">Universal Key de Emergent</option>
                <option value="google">Google Gemini — API Key propia</option>
                <option value="vertex">Google Vertex AI — cuenta de servicio (JSON)</option>
              </select>
              <p className="text-[10px] text-slate-400 mt-1">
                Con "Universal Key" usas el saldo de tu clave de Emergent, sin cuenta de Google. Con "Google Gemini" usas tu API Key de aistudio.google.com. Con "Vertex AI" usas una cuenta de servicio de Google Cloud (archivo JSON) — ideal si tu organización no permite crear API keys.
              </p>
            </div>
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
                Déjalo vacío para mantener la clave actual. Se usa cuando el proveedor activo es "Emergent Universal Key".
              </p>
            </div>
            <div className="sm:col-span-2">
              <label className="text-[10px] tracking-[0.15em] uppercase text-slate-500 font-semibold">API Key de Google Gemini (opcional)</label>
              <input
                type="text"
                value={googleKey}
                onChange={(e) => setGoogleKey(e.target.value)}
                placeholder={s.google_key_masked ? `Actual: ${s.google_key_masked} — escribe aquí para reemplazarla` : "AIza…"}
                data-testid="settings-google_api_key-input"
                className="mt-1 w-full border border-slate-300 focus:border-[#0284C7] outline-none px-3 py-2.5 text-sm transition-colors font-mono"
              />
              <p className="text-[10px] text-slate-400 mt-1">
                Obtén tu clave en aistudio.google.com → "Get API key". Solo se usa si el proveedor activo es "Google Gemini".
              </p>
            </div>
            {(s.llm_provider === "vertex" || s.vertex_json_saved) && (
              <>
                <div className="sm:col-span-2">
                  <label className="text-[10px] tracking-[0.15em] uppercase text-slate-500 font-semibold">JSON de la cuenta de servicio (Vertex AI)</label>
                  <textarea
                    rows={5}
                    value={vertexJson}
                    onChange={(e) => setVertexJson(e.target.value)}
                    placeholder={
                      s.vertex_json_saved
                        ? `Guardado: ${s.vertex_client_email || "cuenta de servicio configurada"} — pega aquí un nuevo JSON para reemplazarlo`
                        : '{"type": "service_account", "project_id": "...", "private_key": "...", "client_email": "..."}'
                    }
                    data-testid="settings-vertex_service_account_json-input"
                    className="mt-1 w-full border border-slate-300 focus:border-[#0284C7] outline-none px-3 py-2.5 text-xs transition-colors font-mono resize-y bg-white"
                  />
                  <p className="text-[10px] text-slate-400 mt-1">
                    Pega el contenido COMPLETO del archivo .json descargado de Google Cloud (IAM → Cuentas de servicio → Claves → Crear clave JSON). La cuenta necesita el rol "Usuario de Vertex AI" y la API de Vertex AI habilitada en el proyecto.
                  </p>
                </div>
                <Input label="Project ID de Google Cloud" field="vertex_project" value={s.vertex_project} onChange={set} placeholder="mi-proyecto-123456" hint="Se autocompleta desde el JSON si lo dejas vacío" />
                <Input label="Región de Vertex AI" field="vertex_location" value={s.vertex_location} onChange={set} placeholder="us-central1" hint="Ej.: us-central1, southamerica-east1" />
              </>
            )}
            <Input label="Modelo de IA" field="ai_model" value={s.ai_model} onChange={set} hint="Ej.: gemini-3.1-pro-preview" />
            <Input label="Email de contacto" field="contact_email" value={s.contact_email} onChange={set} />
            <Input label="Precio plan pequeño (S/, <50 dptos.)" field="price_small" value={s.price_small} onChange={set} />
            <Input label="Precio plan mediano-grande (S/, 50-150)" field="price_medium" value={s.price_medium} onChange={set} />
            <Input label="Precio consulta legal IA (S/)" field="price_consulting" value={s.price_consulting} onChange={set} hint="Precio por consulta y por cada recarga" />
            <Input label="Uso de IA incluido por pago (USD)" field="consulting_budget_usd" value={s.consulting_budget_usd} onChange={set} hint="Presupuesto en tokens Gemini que incluye cada pago de consulta" />
          </div>
        </div>

        <div className="bg-white border border-slate-200 p-6" data-testid="settings-whatsapp-card">
          <div className="flex items-center gap-3">
            <MessageCircle className="text-[#0284C7]" size={22} strokeWidth={1.5} />
            <h3 className="font-heading font-bold text-[#0F172A]">Botón flotante de WhatsApp</h3>
          </div>
          <p className="text-xs text-slate-500 mt-2 leading-relaxed">
            Aparece en las páginas públicas. El visitante elige el servicio que le interesa y se abre el chat con el
            mensaje ya escrito.
          </p>
          <div className="mt-5 grid sm:grid-cols-2 gap-4">
            <label className="sm:col-span-2 flex items-center gap-2 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={!!s.whatsapp_enabled}
                onChange={(e) => set("whatsapp_enabled", e.target.checked)}
                data-testid="settings-whatsapp_enabled-checkbox"
              />
              Mostrar el botón de WhatsApp en la web
            </label>
            <Input label="Número de WhatsApp" field="whatsapp_number" value={s.whatsapp_number} onChange={set} placeholder="51999888777" hint="Con código de país, solo dígitos. Ej.: 51 + número" />
            <Input label="Mensaje inicial" field="whatsapp_message" value={s.whatsapp_message} onChange={set} hint="Usa {servicio} donde debe ir el servicio elegido" />
          </div>
        </div>

        <div className="bg-white border border-slate-200 p-6">
          <div className="flex items-center gap-3">
            <KeyRound className="text-[#0284C7]" size={22} strokeWidth={1.5} />
            <h3 className="font-heading font-bold text-[#0F172A]">Email y Libro de Reclamaciones (Resend)</h3>
          </div>
          <p className="text-xs text-slate-500 mt-2 leading-relaxed">
            Se usa para enviar la constancia de la hoja de reclamación al consumidor y la notificación de
            nuevos reclamos a tu correo. Con dominio verificado en Resend, cambia el remitente a tu dominio.
          </p>
          <div className="mt-5 grid sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <label className="text-[10px] tracking-[0.15em] uppercase text-slate-500 font-semibold">API Key de Resend</label>
              <input
                type="text"
                value={resendKey}
                onChange={(e) => setResendKey(e.target.value)}
                placeholder={s.resend_key_masked ? `Actual: ${s.resend_key_masked} — escribe aquí para reemplazarla` : "re_…"}
                data-testid="settings-resend_api_key-input"
                className="mt-1 w-full border border-slate-300 focus:border-[#0284C7] outline-none px-3 py-2.5 text-sm transition-colors font-mono"
              />
              <p className="text-[10px] text-slate-400 mt-1">Déjalo vacío para mantener la clave actual.</p>
            </div>
            <Input label="Remitente (from)" field="resend_sender" value={s.resend_sender} onChange={set} hint="Debe ser de un dominio verificado en Resend. En modo prueba: onboarding@resend.dev" />
            <Input label="Email de notificación de reclamos" field="complaints_notify_email" value={s.complaints_notify_email} onChange={set} hint="Aquí recibirás cada nuevo reclamo o queja" />
          </div>
        </div>

        <div className="bg-white border border-slate-200 p-6">
          <div className="flex items-center gap-3">
            <KeyRound className="text-[#0284C7]" size={22} strokeWidth={1.5} />
            <h3 className="font-heading font-bold text-[#0F172A]">Pagos con PayPal</h3>
          </div>
          <p className="text-xs text-slate-500 mt-2 leading-relaxed">
            Credenciales de tu app en developer.paypal.com. En modo <b>sandbox</b> los pagos son de prueba (sin
            dinero real); cambia a <b>live</b> con las credenciales de producción cuando estés listo para cobrar.
            El cobro se realiza en USD al tipo de cambio del día y la auditoría se activa automáticamente al pagar.
          </p>
          <div className="mt-5 grid sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <Input label="Client ID de PayPal" field="paypal_client_id" value={s.paypal_client_id} onChange={set} placeholder="Ae68…" />
            </div>
            <div className="sm:col-span-2">
              <label className="text-[10px] tracking-[0.15em] uppercase text-slate-500 font-semibold">Secret Key de PayPal</label>
              <input
                type="text"
                value={paypalSecret}
                onChange={(e) => setPaypalSecret(e.target.value)}
                placeholder={s.paypal_secret_masked ? `Actual: ${s.paypal_secret_masked} — escribe aquí para reemplazarla` : "EEY5…"}
                data-testid="settings-paypal_secret-input"
                className="mt-1 w-full border border-slate-300 focus:border-[#0284C7] outline-none px-3 py-2.5 text-sm transition-colors font-mono"
              />
              <p className="text-[10px] text-slate-400 mt-1">Déjalo vacío para mantener la clave actual.</p>
            </div>
            <div>
              <label className="text-[10px] tracking-[0.15em] uppercase text-slate-500 font-semibold">Modo</label>
              <select
                value={s.paypal_mode || "sandbox"}
                onChange={(e) => set("paypal_mode", e.target.value)}
                data-testid="settings-paypal_mode-select"
                className="mt-1 w-full border border-slate-300 focus:border-[#0284C7] outline-none px-3 py-2.5 text-sm transition-colors bg-white"
              >
                <option value="sandbox">Sandbox (pruebas)</option>
                <option value="live">Live (producción)</option>
              </select>
            </div>
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

        <BackupPanel />

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
