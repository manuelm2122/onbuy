import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ArrowRight, CheckCircle2, FolderKanban, FileSignature, ScanSearch, Scale, Calculator, Globe,
  ShieldCheck, CalendarClock, ListChecks, BookOpenText, Wallet, FileStack, Smartphone,
  Home as HomeIcon, ShieldAlert, Baby, Briefcase, Banknote, Users, FileWarning, Landmark,
} from "lucide-react";
import { api } from "@/lib/api";
import { LEGAL_HERO_IMG } from "@/constants/services";
import { SiteNav } from "@/components/SiteNav";
import { SiteFooter } from "@/components/SiteFooter";
import { WhatsAppButton } from "@/components/WhatsAppButton";
import { ContactSection } from "@/components/ContactSection";
import { LegalComparison } from "@/components/LegalComparison";
import { LEGAL_BENEFITS } from "@/constants/legalBenefits";

const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  visible: (i = 0) => ({ opacity: 1, y: 0, transition: { duration: 0.55, delay: i * 0.08, ease: "easeOut" } }),
};

const FEATURES = [
  { icon: FolderKanban, title: "Seguimiento de tu caso", desc: "Cada caso es un expediente digital: historial completo, archivos, novedades y el siguiente paso siempre a la vista. Retómalo cuando quieras." },
  { icon: FileSignature, title: "Generación de documentos", desc: "Cartas notariales, denuncias, demandas, contratos y requerimientos redactados a tu medida y descargables en PDF con un clic." },
  { icon: ScanSearch, title: "Procesamiento de documentos", desc: "Sube contratos, resoluciones, vouchers, fotos, audios o videos. El sistema los lee, los resume y los integra a tu expediente." },
  { icon: Scale, title: "Enfoque civil y penal", desc: "Análisis de tu situación desde ambas vías, con referencias a la normativa peruana aplicable para que sepas qué camino tomar." },
  { icon: Calculator, title: "Calculadoras exactas", desc: "Beneficios sociales, intereses legales, pensiones devengadas y alquileres impagos calculados por fórmula, con detalle mes a mes." },
  { icon: ShieldCheck, title: "Citas legales verificadas", desc: "Un botón busca en fuentes públicas cada norma que cita el agente, te muestra el enlace y marca las dudosas. No gasta mensajes." },
  { icon: CalendarClock, title: "Plazos con recordatorios", desc: "Línea de tiempo de tu caso con etapas y fechas límite. Te avisamos por correo 3 días antes, 1 día antes y el mismo día." },
  { icon: ListChecks, title: "Checklist de requisitos", desc: "Qué documentos reunir para tu desalojo, demanda de alimentos, reclamo ante Indecopi, cobro de deuda o reclamo laboral." },
  { icon: BookOpenText, title: "Cuaderno de hechos", desc: "Anota lo ocurrido con su fecha y su prueba. Se ordena solo y se convierte en la relación de hechos de tu escrito." },
  { icon: Wallet, title: "Pagos y deudas", desc: "Registra lo que te deben y cada pago con su comprobante. El saldo se actualiza solo y se exporta como estado de cuenta." },
  { icon: FileStack, title: "Expediente listo para presentar", desc: "Un solo PDF con carátula, índice, tu escrito y los anexos numerados y foliados, en el orden que elijas." },
  { icon: Smartphone, title: "Tu caso siempre contigo", desc: "Instala la app en tu celular, descarga tu caso completo en un ZIP y recibe un informe final al cerrarlo." },
];

const CASES = [
  { icon: HomeIcon, title: "Desalojo de inquilinos e invasiones", desc: "Requerimiento notarial, liquidación de rentas impagas y borrador de demanda de desalojo u ocupación precaria." },
  { icon: ShieldAlert, title: "Denuncias", desc: "Denuncias por estafa, usurpación, apropiación ilícita o violencia, ordenadas con hechos, pruebas y sustento legal." },
  { icon: Baby, title: "Pensión de alimentos", desc: "Demanda de alimentos, aumento o reducción, y liquidación de pensiones devengadas mes por mes." },
  { icon: Banknote, title: "Cobro de deudas", desc: "Cartas de requerimiento, reconocimiento de deuda y preparación de la demanda de obligación de dar suma de dinero." },
  { icon: Briefcase, title: "Conflictos laborales", desc: "Cálculo de beneficios sociales, cartas de cese o reclamo y orientación ante Sunafil." },
  { icon: FileWarning, title: "Reclamos de consumo", desc: "Reclamos ante Indecopi o proveedores, con la redacción y los plazos correctos." },
  { icon: Users, title: "Herencias y familia", desc: "Sucesión intestada, división y partición, tenencia y régimen de visitas explicados paso a paso." },
  { icon: Landmark, title: "Trámites tributarios y contables", desc: "Descargos ante SUNAT, fraccionamientos y orden de las cuentas de tu negocio o junta de propietarios." },
];

const STEPS = [
  ["Abre tu chat", "Crea tu cuenta, describe tu situación y prueba el agente gratis antes de habilitar el chat."],
  ["Sube tus documentos", "Contratos, mensajes, vouchers o resoluciones. Todo queda en tu expediente."],
  ["Recibe análisis y documentos", "Estrategia clara y escritos listos para descargar, firmar o llevar a tu abogado."],
  ["Haz seguimiento", "Registra cada novedad y obtén un informe final al cerrar el caso."],
];

const PREVIEWS = [
  { src: "/previews/consultoria-chat.jpg", caption: "Expediente del caso con análisis y documentos al instante" },
  { src: "/previews/consultoria-biblioteca.jpg", caption: "Biblioteca: cada documento descargable en PDF" },
  { src: "/previews/consultoria-imagen.jpg", caption: "Diagramas y evidencia visual para tu caso" },
];

export default function LegalService() {
  const [cfg, setCfg] = useState({ price_chat_usd: 15.99, chat_messages: 60, price_extra_usd: 7.99, extra_messages: 30, trial_messages: 3 });

  useEffect(() => {
    window.scrollTo(0, 0);
    api.get("/public/settings").then(({ data }) => setCfg((c) => ({ ...c, ...data }))).catch(() => {});
  }, []);

  const priceLabel = `US$ ${Number(cfg.price_chat_usd).toFixed(2)}`;

  return (
    <div className="bg-[#020617] text-slate-100 min-h-screen" data-testid="legal-service-page">
      <SiteNav />

      <header className="relative min-h-[90vh] flex items-center grain overflow-hidden">
        <div className="absolute inset-0">
          <img src={LEGAL_HERO_IMG} alt="Asesoría legal y contable" className="w-full h-full object-cover" />
          <div className="absolute inset-0 bg-gradient-to-r from-[#020617] via-[#020617]/85 to-[#020617]/40" />
        </div>
        <div className="relative max-w-7xl mx-auto px-6 lg:px-10 w-full pt-28 pb-20">
          <div className="max-w-3xl">
            <motion.p variants={fadeUp} initial="hidden" animate="visible" custom={0} className="text-xs tracking-[0.3em] uppercase text-[#0EA5E9] font-semibold mb-6">
              Asesoría legal y contable · Perú
            </motion.p>
            <motion.h1 variants={fadeUp} initial="hidden" animate="visible" custom={1} className="font-heading font-black text-4xl sm:text-5xl lg:text-6xl leading-[1.05] tracking-tight text-white" data-testid="legal-hero-title">
              Tu caso legal, <span className="text-[#0EA5E9]">ordenado y en marcha</span> desde hoy
            </motion.h1>
            <motion.p variants={fadeUp} initial="hidden" animate="visible" custom={2} className="mt-8 text-base md:text-lg text-slate-300 leading-relaxed max-w-2xl">
              Asesoría especializada con un sistema que hace seguimiento a tu caso, procesa tus documentos y
              redacta los escritos que necesitas: desalojos, denuncias, pensión de alimentos, cobro de deudas y más.
            </motion.p>
            <motion.div variants={fadeUp} initial="hidden" animate="visible" custom={3} className="mt-10 flex flex-col sm:flex-row gap-4">
              <Link to="/acceso" data-testid="legal-hero-cta" className="inline-flex items-center justify-center gap-2 bg-[#0284C7] hover:bg-[#0EA5E9] text-white font-semibold px-8 py-4 rounded-full text-base transition-colors">
                {cfg.trial_messages > 0 ? `Probar gratis (${cfg.trial_messages} mensajes)` : `Abrir mi chat por ${priceLabel}`} <ArrowRight size={18} />
              </Link>
              <a href="#casos" data-testid="legal-hero-secondary" className="inline-flex items-center justify-center gap-2 border border-slate-600 hover:border-slate-300 text-slate-200 font-semibold px-8 py-4 rounded-full text-base transition-colors">
                Ver casos que resolvemos
              </a>
            </motion.div>
          </div>
        </div>
      </header>

      <section className="bg-[#F8FAFC] text-[#0F172A] py-24 lg:py-32" data-testid="legal-features">
        <div className="max-w-7xl mx-auto px-6 lg:px-10">
          <p className="text-xs tracking-[0.3em] uppercase text-[#0284C7] font-semibold mb-4">Características</p>
          <h2 className="font-heading font-black text-2xl sm:text-3xl lg:text-4xl tracking-tight max-w-2xl">
            Mucho más que una consulta: un sistema completo para tu caso
          </h2>
          <div className="mt-16 grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {FEATURES.map((f, i) => (
              <motion.div key={f.title} variants={fadeUp} initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-60px" }} custom={i % 4} className="bg-white border border-slate-200 p-7 hover:border-[#0284C7] transition-colors" data-testid={`legal-feature-${i}`}>
                <f.icon className="text-[#0284C7]" size={30} strokeWidth={1.5} />
                <h3 className="font-heading font-bold text-lg mt-6">{f.title}</h3>
                <p className="text-slate-600 text-sm leading-relaxed mt-3">{f.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      <section id="casos" className="bg-[#020617] py-24 lg:py-32 grain relative" data-testid="legal-cases">
        <div className="max-w-7xl mx-auto px-6 lg:px-10 relative">
          <p className="text-xs tracking-[0.3em] uppercase text-[#0EA5E9] font-semibold mb-4">Casos que puedes resolver</p>
          <h2 className="font-heading font-black text-2xl sm:text-3xl lg:text-4xl tracking-tight text-white max-w-2xl">
            Situaciones reales, con un camino claro
          </h2>
          <div className="mt-16 grid sm:grid-cols-2 lg:grid-cols-4 gap-px bg-slate-800">
            {CASES.map((c, i) => (
              <motion.div key={c.title} variants={fadeUp} initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-60px" }} custom={i % 4} className="bg-[#020617] p-8 hover:bg-slate-900/60 transition-colors" data-testid={`legal-case-${i}`}>
                <c.icon className="text-[#0EA5E9]" size={26} strokeWidth={1.5} />
                <h3 className="font-heading font-bold text-white mt-5">{c.title}</h3>
                <p className="text-slate-400 text-sm leading-relaxed mt-3">{c.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      <section className="bg-white text-[#0F172A] py-24 lg:py-32" data-testid="legal-steps">
        <div className="max-w-7xl mx-auto px-6 lg:px-10">
          <p className="text-xs tracking-[0.3em] uppercase text-[#0284C7] font-semibold mb-4">Cómo funciona</p>
          <h2 className="font-heading font-black text-2xl sm:text-3xl lg:text-4xl tracking-tight max-w-2xl">
            De la preocupación al plan, en cuatro pasos
          </h2>
          <div className="mt-16 grid sm:grid-cols-2 lg:grid-cols-4 gap-8">
            {STEPS.map(([title, desc], i) => (
              <div key={title} className="border-t-2 border-[#0284C7] pt-6" data-testid={`legal-step-${i + 1}`}>
                <span className="font-heading font-black text-4xl text-slate-200">0{i + 1}</span>
                <h3 className="font-heading font-bold text-lg mt-3">{title}</h3>
                <p className="text-slate-600 text-sm leading-relaxed mt-2">{desc}</p>
              </div>
            ))}
          </div>
          <div className="mt-20 grid md:grid-cols-3 gap-6">
            {PREVIEWS.map((s, i) => (
              <figure key={s.src} data-testid={`legal-preview-${i}`}>
                <div className="border border-slate-200 rounded-lg overflow-hidden shadow-lg shadow-slate-200/60">
                  <div className="bg-slate-100 border-b border-slate-200 px-3 py-2 flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-red-300" />
                    <span className="w-2.5 h-2.5 rounded-full bg-amber-300" />
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-300" />
                  </div>
                  <img src={s.src} alt={s.caption} loading="lazy" className="w-full h-auto" />
                </div>
                <figcaption className="mt-3 text-xs text-slate-500 flex items-start gap-2">
                  <CheckCircle2 className="text-[#0284C7] shrink-0 mt-0.5" size={14} /> {s.caption}
                </figcaption>
              </figure>
            ))}
          </div>
        </div>
      </section>

      <LegalComparison />

      <section id="beneficios" className="bg-[#020617] py-24 lg:py-32 scroll-mt-16" data-testid="legal-benefits">
        <div className="max-w-7xl mx-auto px-6 lg:px-10">
          <p className="text-xs tracking-[0.3em] uppercase text-[#0EA5E9] font-semibold mb-4">Incluido en tu pago</p>
          <h2 className="font-heading font-black text-2xl sm:text-3xl lg:text-4xl tracking-tight text-white max-w-3xl">
            Todo lo que recibes al habilitar tu chat por {priceLabel}
          </h2>
          <p className="mt-5 text-slate-400 text-sm md:text-base leading-relaxed max-w-2xl">
            {cfg.chat_messages} mensajes con el agente y todas las herramientas del expediente, que puedes usar las veces que quieras sin gastar mensajes.
          </p>
          <div className="mt-14 grid md:grid-cols-3 gap-px bg-slate-800 border border-slate-800">
            {LEGAL_BENEFITS.map((g, i) => (
              <div key={g.group} className="bg-[#020617] p-8" data-testid={`legal-benefit-group-${i}`}>
                <h3 className="font-heading font-bold text-white text-lg">{g.group}</h3>
                <ul className="mt-6 space-y-3.5">
                  {g.items.map((item) => (
                    <li key={item} className="flex items-start gap-3 text-sm text-slate-300 leading-relaxed">
                      <CheckCircle2 size={16} className="text-[#0EA5E9] shrink-0 mt-0.5" /> {item}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="bg-[#0284C7] py-20" data-testid="legal-pricing">
        <div className="max-w-7xl mx-auto px-6 lg:px-10 flex flex-col lg:flex-row items-start lg:items-center justify-between gap-8">
          <div>
            <h2 className="font-heading font-black text-2xl sm:text-3xl lg:text-4xl tracking-tight text-white max-w-2xl" data-testid="legal-price">
              {priceLabel} por chat habilitado. Sin mensualidades.
            </h2>
            <p className="text-sky-100 mt-3 max-w-2xl text-sm leading-relaxed" data-testid="legal-price-detail">
              Cada chat incluye {cfg.chat_messages} mensajes con el agente (o su equivalente en soles al tipo de cambio del día).
              {cfg.trial_messages > 0 ? ` Al crear tu cuenta puedes probarlo gratis con ${cfg.trial_messages} mensajes.` : ""} Si
              necesitas más, agregas {cfg.extra_messages} mensajes por US$ {Number(cfg.price_extra_usd).toFixed(2)} y sigues en el
              mismo caso. Paga con PayPal (activación inmediata) o por depósito o transferencia en soles o dólares. Esta
              asesoría es orientación informativa y no reemplaza el patrocinio de un abogado colegiado en un proceso judicial.
            </p>
          </div>
          <Link to="/acceso" data-testid="legal-pricing-cta" className="inline-flex items-center gap-2 bg-[#020617] hover:bg-slate-900 text-white font-semibold px-8 py-4 rounded-full transition-colors shrink-0">
            Contratar ahora <ArrowRight size={18} />
          </Link>
        </div>
      </section>

      <ContactSection defaultService="legal" heading="Cuéntanos tu caso" />
      <SiteFooter />
      <WhatsAppButton defaultService="legal" />
    </div>
  );
}
