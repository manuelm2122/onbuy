import { useState } from "react";
import { toast } from "sonner";
import { api, formatApiErrorDetail } from "@/lib/api";
import { SERVICES } from "@/constants/services";

const field =
  "w-full bg-slate-900 border border-slate-700 focus:border-[#0EA5E9] outline-none text-white px-5 py-4 text-sm transition-colors";

export const ContactSection = ({ defaultService = "", heading = "Hablemos de tu proyecto" }) => {
  const empty = { name: "", email: "", phone: "", message: "", service: defaultService };
  const [form, setForm] = useState(empty);
  const [sending, setSending] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setSending(true);
    try {
      const title = SERVICES.find((s) => s.key === form.service)?.title;
      await api.post("/contact", { ...form, service: title || null });
      toast.success("Mensaje enviado. Te contactaremos pronto.");
      setForm(empty);
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail));
    } finally {
      setSending(false);
    }
  };

  return (
    <section id="contacto" className="bg-[#020617] py-24 lg:py-32" data-testid="section-contacto">
      <div className="max-w-7xl mx-auto px-6 lg:px-10 grid lg:grid-cols-2 gap-16">
        <div>
          <p className="text-xs tracking-[0.3em] uppercase text-[#0EA5E9] font-semibold mb-4">Contacto</p>
          <h2 className="font-heading font-black text-2xl sm:text-3xl lg:text-4xl tracking-tight text-white">{heading}</h2>
          <p className="text-slate-400 mt-6 leading-relaxed max-w-md">
            Cuéntanos qué necesitas y un especialista de OnBuySolutions te responderá. También puedes escribirnos
            por WhatsApp con el botón verde.
          </p>
        </div>
        <form onSubmit={submit} className="space-y-5" data-testid="contact-form">
          <div className="grid sm:grid-cols-2 gap-5">
            <input required data-testid="contact-name-input" value={form.name} onChange={set("name")} placeholder="Nombre completo" className={field} />
            <input required type="email" data-testid="contact-email-input" value={form.email} onChange={set("email")} placeholder="Correo electrónico" className={field} />
          </div>
          <div className="grid sm:grid-cols-2 gap-5">
            <input data-testid="contact-phone-input" value={form.phone} onChange={set("phone")} placeholder="Teléfono (opcional)" className={field} />
            <select data-testid="contact-service-select" value={form.service} onChange={set("service")} className={field}>
              <option value="">Servicio de interés</option>
              {SERVICES.map((s) => (
                <option key={s.key} value={s.key}>{s.title}</option>
              ))}
            </select>
          </div>
          <textarea required rows={4} data-testid="contact-message-input" value={form.message} onChange={set("message")} placeholder="Cuéntanos qué necesitas…" className={`${field} resize-none`} />
          <button
            type="submit"
            disabled={sending}
            data-testid="contact-submit-btn"
            className="bg-[#0284C7] hover:bg-[#0EA5E9] disabled:opacity-60 text-white font-semibold px-8 py-4 rounded-full text-sm transition-colors"
          >
            {sending ? "Enviando…" : "Enviar mensaje"}
          </button>
        </form>
      </div>
    </section>
  );
};
