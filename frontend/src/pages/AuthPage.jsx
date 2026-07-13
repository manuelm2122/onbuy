import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ShieldCheck, ArrowLeft, MailCheck, KeyRound } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/context/AuthContext";
import { formatApiErrorDetail } from "@/lib/api";
import { ThemeToggle } from "@/components/ThemeToggle";

const inputClass =
  "mt-2 w-full bg-white border border-slate-300 focus:border-[#0284C7] outline-none px-4 py-3.5 text-sm text-[#0F172A] transition-colors";
const labelClass = "text-xs tracking-[0.2em] uppercase text-slate-500 font-semibold";
const submitClass =
  "w-full bg-[#0284C7] hover:bg-[#0EA5E9] disabled:opacity-60 text-white font-semibold py-4 rounded-full text-sm transition-colors";
const codeInputClass =
  "mt-2 w-full bg-white border border-slate-300 focus:border-[#0284C7] outline-none px-4 py-3.5 text-center text-2xl font-mono tracking-[0.5em] text-[#0F172A] transition-colors";

export default function AuthPage() {
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [acceptedTerms, setAcceptedTerms] = useState(false);
  const [loading, setLoading] = useState(false);
  const [code, setCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [cooldown, setCooldown] = useState(0);
  const { login, register, verifyEmail, resendCode, forgotPassword, resetPassword } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (cooldown <= 0) return;
    const t = setTimeout(() => setCooldown((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [cooldown]);

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
        toast.success("Bienvenido de nuevo");
        navigate("/panel");
      } else {
        const data = await register(form.name, form.email, form.password, acceptedTerms);
        if (data.requires_verification) {
          toast.success(data.message);
          setCode("");
          setMode("verify");
          setCooldown(60);
        } else {
          navigate("/panel");
        }
      }
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (err.response?.status === 403 && detail?.error_code === "EMAIL_NOT_VERIFIED") {
        toast.info(detail.msg);
        setCode("");
        setMode("verify");
        setCooldown(60);
      } else {
        toast.error(formatApiErrorDetail(detail) || err.message);
      }
    } finally {
      setLoading(false);
    }
  };

  const submitCode = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await verifyEmail(form.email, code.trim());
      toast.success("¡Correo verificado! Bienvenido a OnBuySolutions");
      navigate("/panel");
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail) || err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    try {
      const data = await resendCode(form.email);
      toast.success(data.message);
      setCooldown(60);
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail) || err.message);
    }
  };

  const submitForgot = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const data = await forgotPassword(form.email);
      toast.success(data.message);
      setCode("");
      setNewPassword("");
      setMode("reset");
      setCooldown(60);
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail) || err.message);
    } finally {
      setLoading(false);
    }
  };

  const submitReset = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const data = await resetPassword(form.email, code.trim(), newPassword);
      toast.success(data.message);
      setForm({ ...form, password: "" });
      setMode("login");
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail) || err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleResendReset = async () => {
    try {
      const data = await forgotPassword(form.email);
      toast.success(data.message);
      setCooldown(60);
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail) || err.message);
    }
  };

  const titles = {
    login: "Accede a tu panel",
    register: "Crea tu cuenta",
    verify: "Verifica tu correo",
    forgot: "Recupera tu contraseña",
    reset: "Nueva contraseña",
  };
  const subtitles = {
    login: "Ingresa tus credenciales para continuar.",
    register: "Regístrate gratis y comienza tu primera auditoría.",
    verify: `Ingresa el código de 6 dígitos que enviamos a ${form.email}. Revisa también tu carpeta de spam.`,
    forgot: "Ingresa tu correo y te enviaremos un código para restablecer tu contraseña.",
    reset: `Ingresa el código que enviamos a ${form.email} y define tu nueva contraseña.`,
  };

  return (
    <div className="themeable min-h-screen grid lg:grid-cols-2">
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
          <div className="flex items-center justify-between mb-10">
            <Link to="/" className="inline-flex items-center gap-2 text-sm text-slate-500 hover:text-[#0284C7] transition-colors" data-testid="auth-back-link">
              <ArrowLeft size={16} /> Volver al inicio
            </Link>
            <ThemeToggle />
          </div>
          {(mode === "verify" || mode === "reset") && (
            <div className="w-12 h-12 rounded-full bg-[#E0F2FE] flex items-center justify-center mb-6">
              {mode === "verify" ? (
                <MailCheck size={22} className="text-[#0284C7]" />
              ) : (
                <KeyRound size={22} className="text-[#0284C7]" />
              )}
            </div>
          )}
          <h2 className="font-heading font-black text-3xl tracking-tight text-[#0F172A]" data-testid="auth-title">
            {titles[mode]}
          </h2>
          <p className="text-slate-500 text-sm mt-2" data-testid="auth-subtitle">
            {subtitles[mode]}
          </p>

          {(mode === "login" || mode === "register") && (
            <>
              <form onSubmit={submit} className="mt-10 space-y-5">
                {mode === "register" && (
                  <div>
                    <label className={labelClass}>Nombre</label>
                    <input
                      required
                      data-testid="auth-name-input"
                      value={form.name}
                      onChange={(e) => setForm({ ...form, name: e.target.value })}
                      placeholder="Tu nombre completo"
                      className={inputClass}
                    />
                  </div>
                )}
                <div>
                  <label className={labelClass}>Correo</label>
                  <input
                    required
                    type="email"
                    data-testid="auth-email-input"
                    value={form.email}
                    onChange={(e) => setForm({ ...form, email: e.target.value })}
                    placeholder="tucorreo@ejemplo.com"
                    className={inputClass}
                  />
                </div>
                <div>
                  <label className={labelClass}>Contraseña</label>
                  <input
                    required
                    type="password"
                    minLength={6}
                    data-testid="auth-password-input"
                    value={form.password}
                    onChange={(e) => setForm({ ...form, password: e.target.value })}
                    placeholder="Mínimo 6 caracteres"
                    className={inputClass}
                  />
                  {mode === "login" && (
                    <div className="text-right mt-2">
                      <button
                        type="button"
                        data-testid="auth-forgot-link"
                        onClick={() => setMode("forgot")}
                        className="text-xs text-[#0284C7] font-semibold hover:underline"
                      >
                        ¿Olvidaste tu contraseña?
                      </button>
                    </div>
                  )}
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
                <button type="submit" disabled={loading} data-testid="auth-submit-btn" className={submitClass}>
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
            </>
          )}

          {mode === "verify" && (
            <>
              <form onSubmit={submitCode} className="mt-10 space-y-5">
                <div>
                  <label className={labelClass}>Código de verificación</label>
                  <input
                    required
                    autoFocus
                    inputMode="numeric"
                    pattern="[0-9]{6}"
                    maxLength={6}
                    data-testid="auth-otp-input"
                    value={code}
                    onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
                    placeholder="000000"
                    className={codeInputClass}
                  />
                </div>
                <button
                  type="submit"
                  disabled={loading || code.length !== 6}
                  data-testid="auth-verify-btn"
                  className={submitClass}
                >
                  {loading ? "Verificando…" : "Verificar correo"}
                </button>
              </form>
              <div className="text-sm text-slate-500 mt-8 text-center space-y-3">
                <p>
                  ¿No recibiste el código?{" "}
                  <button
                    type="button"
                    disabled={cooldown > 0}
                    data-testid="auth-resend-btn"
                    onClick={handleResend}
                    className="text-[#0284C7] font-semibold hover:underline disabled:text-slate-400 disabled:no-underline"
                  >
                    {cooldown > 0 ? `Reenviar en ${cooldown}s` : "Reenviar código"}
                  </button>
                </p>
                <button
                  type="button"
                  data-testid="auth-verify-back-btn"
                  onClick={() => setMode("login")}
                  className="text-slate-500 hover:text-[#0284C7] text-xs underline"
                >
                  Volver a iniciar sesión
                </button>
              </div>
            </>
          )}

          {mode === "forgot" && (
            <>
              <form onSubmit={submitForgot} className="mt-10 space-y-5">
                <div>
                  <label className={labelClass}>Correo</label>
                  <input
                    required
                    type="email"
                    autoFocus
                    data-testid="auth-forgot-email-input"
                    value={form.email}
                    onChange={(e) => setForm({ ...form, email: e.target.value })}
                    placeholder="tucorreo@ejemplo.com"
                    className={inputClass}
                  />
                </div>
                <button type="submit" disabled={loading} data-testid="auth-forgot-submit-btn" className={submitClass}>
                  {loading ? "Enviando…" : "Enviar código"}
                </button>
              </form>
              <p className="text-sm text-slate-500 mt-8 text-center">
                <button
                  type="button"
                  data-testid="auth-forgot-back-btn"
                  onClick={() => setMode("login")}
                  className="text-[#0284C7] font-semibold hover:underline"
                >
                  Volver a iniciar sesión
                </button>
              </p>
            </>
          )}

          {mode === "reset" && (
            <>
              <form onSubmit={submitReset} className="mt-10 space-y-5">
                <div>
                  <label className={labelClass}>Código de recuperación</label>
                  <input
                    required
                    autoFocus
                    inputMode="numeric"
                    pattern="[0-9]{6}"
                    maxLength={6}
                    data-testid="auth-reset-code-input"
                    value={code}
                    onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
                    placeholder="000000"
                    className={codeInputClass}
                  />
                </div>
                <div>
                  <label className={labelClass}>Nueva contraseña</label>
                  <input
                    required
                    type="password"
                    minLength={6}
                    data-testid="auth-reset-password-input"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="Mínimo 6 caracteres"
                    className={inputClass}
                  />
                </div>
                <button
                  type="submit"
                  disabled={loading || code.length !== 6}
                  data-testid="auth-reset-submit-btn"
                  className={submitClass}
                >
                  {loading ? "Actualizando…" : "Cambiar contraseña"}
                </button>
              </form>
              <div className="text-sm text-slate-500 mt-8 text-center space-y-3">
                <p>
                  ¿No recibiste el código?{" "}
                  <button
                    type="button"
                    disabled={cooldown > 0}
                    data-testid="auth-reset-resend-btn"
                    onClick={handleResendReset}
                    className="text-[#0284C7] font-semibold hover:underline disabled:text-slate-400 disabled:no-underline"
                  >
                    {cooldown > 0 ? `Reenviar en ${cooldown}s` : "Reenviar código"}
                  </button>
                </p>
                <button
                  type="button"
                  data-testid="auth-reset-back-btn"
                  onClick={() => setMode("login")}
                  className="text-slate-500 hover:text-[#0284C7] text-xs underline"
                >
                  Volver a iniciar sesión
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
