import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ShieldCheck, ArrowLeft } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/context/AuthContext";
import { formatApiErrorDetail } from "@/lib/api";

export default function AuthPage() {
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [acceptedTerms, setAcceptedTerms] = useState(false);
  const [loading, setLoading] = useState(false);
  const { login, register } = useAuth();
  const navigate = useNavigate();

  const submit = async (e) => {
    e.preventDefault();
    if (mode === "register" && !acceptedTerms) {
      toast.error("Debes aceptar los Términos y Condiciones y la Política de Privacidad");
      return;
    }
    setLoading(true);
    try {
      if (mode === "login") {
        await login(form.email, form.password);
      } else {
        await register(form.name, form.email, form.password, acceptedTerms);
      }
      toast.success(mode === "login" ? "Bienvenido de nuevo" : "Cuenta creada con éxito");
      navigate("/panel");
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail) || err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      {/* Panel izquierdo */}
      <div className="hidden lg:flex flex-col justify-between bg-[#020617] text-white p-12 grain relative">
        <Link to="/" className="font-heading font-black text-xl tracking-tight" data-testid="auth-logo-link">
          OnBuy<span className="text-[#0EA5E9]">Solutions</span>
        </Link>
        <div className="max-w-md">
          <ShieldCheck size={40} className="text-[#0EA5E9]" strokeWidth={1.5} />
          <h1 className="font-heading font-black text-4xl tracking-tight mt-8 leading-tight">
            Transparencia total para tu condominio
          </h1>
          <p className="text-slate-400 mt-6 leading-relaxed">
            Sube tus documentos, deja que la IA de Google haga la auditoría y descarga un informe
            profesional con valor legal. Todo desde un solo panel.
          </p>
        </div>
        <p className="text-xs text-slate-600">
          © {new Date().getFullYear()} OnBuySolutions · Perú
        </p>
      </div>

      {/* Formulario */}
      <div className="flex items-center justify-center bg-[#F8FAFC] p-6 lg:p-12">
        <div className="w-full max-w-md">
          <Link to="/" className="inline-flex items-center gap-2 text-sm text-slate-500 hover:text-[#0284C7] transition-colors mb-10" data-testid="auth-back-link">
            <ArrowLeft size={16} /> Volver al inicio
          </Link>
          <h2 className="font-heading font-black text-3xl tracking-tight text-[#0F172A]" data-testid="auth-title">
            {mode === "login" ? "Accede a tu panel" : "Crea tu cuenta"}
          </h2>
          <p className="text-slate-500 text-sm mt-2">
            {mode === "login"
              ? "Ingresa tus credenciales para continuar."
              : "Regístrate gratis y comienza tu primera auditoría."}
          </p>

          <form onSubmit={submit} className="mt-10 space-y-5">
            {mode === "register" && (
              <div>
                <label className="text-xs tracking-[0.2em] uppercase text-slate-500 font-semibold">Nombre</label>
                <input
                  required
                  data-testid="auth-name-input"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="Tu nombre completo"
                  className="mt-2 w-full bg-white border border-slate-300 focus:border-[#0284C7] outline-none px-4 py-3.5 text-sm text-[#0F172A] transition-colors"
                />
              </div>
            )}
            <div>
              <label className="text-xs tracking-[0.2em] uppercase text-slate-500 font-semibold">Correo</label>
              <input
                required
                type="email"
                data-testid="auth-email-input"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                placeholder="tucorreo@ejemplo.com"
                className="mt-2 w-full bg-white border border-slate-300 focus:border-[#0284C7] outline-none px-4 py-3.5 text-sm text-[#0F172A] transition-colors"
              />
            </div>
            <div>
              <label className="text-xs tracking-[0.2em] uppercase text-slate-500 font-semibold">Contraseña</label>
              <input
                required
                type="password"
                minLength={6}
                data-testid="auth-password-input"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                placeholder="Mínimo 6 caracteres"
                className="mt-2 w-full bg-white border border-slate-300 focus:border-[#0284C7] outline-none px-4 py-3.5 text-sm text-[#0F172A] transition-colors"
              />
            </div>
            {mode === "register" && (
              <label className="flex items-start gap-3 cursor-pointer" data-testid="auth-terms-label">
                <input
                  type="checkbox"
                  checked={acceptedTerms}
                  onChange={(e) => setAcceptedTerms(e.target.checked)}
                  data-testid="auth-terms-checkbox"
                  className="mt-0.5 h-4 w-4 accent-[#0284C7] shrink-0"
                />
                <span className="text-xs text-slate-500 leading-relaxed">
                  Declaro haber leído y acepto los{" "}
                  <Link to="/terminos" target="_blank" className="text-[#0284C7] font-semibold hover:underline">
                    Términos y Condiciones
                  </Link>
                  , la{" "}
                  <Link to="/privacidad" target="_blank" className="text-[#0284C7] font-semibold hover:underline">
                    Política de Privacidad
                  </Link>{" "}
                  y el{" "}
                  <Link to="/uso-ia" target="_blank" className="text-[#0284C7] font-semibold hover:underline">
                    Aviso de Uso de IA
                  </Link>
                  , y otorgo mi consentimiento para el tratamiento de mis datos personales conforme a la Ley
                  N° 29733.
                </span>
              </label>
            )}
            <button
              type="submit"
              disabled={loading}
              data-testid="auth-submit-btn"
              className="w-full bg-[#0284C7] hover:bg-[#0EA5E9] disabled:opacity-60 text-white font-semibold py-4 rounded-full text-sm transition-colors"
            >
              {loading ? "Procesando…" : mode === "login" ? "Ingresar" : "Crear cuenta"}
            </button>
          </form>

          <p className="text-sm text-slate-500 mt-8 text-center">
            {mode === "login" ? "¿No tienes cuenta?" : "¿Ya tienes cuenta?"}{" "}
            <button
              type="button"
              data-testid="auth-toggle-mode-btn"
              onClick={() => setMode(mode === "login" ? "register" : "login")}
              className="text-[#0284C7] font-semibold hover:underline"
            >
              {mode === "login" ? "Regístrate gratis" : "Inicia sesión"}
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}
