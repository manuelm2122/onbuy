import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Building2,
  FileSearch,
  ScanLine,
  ShieldCheck,
  FileCheck2,
  Landmark,
  ArrowRight,
  Upload,
  BrainCircuit,
  FileBadge,
  CheckCircle2,
  Scale,
  FileSignature,
  Video,
} from "lucide-react";
import { toast } from "sonner";
import { api, formatApiErrorDetail } from "@/lib/api";

const HERO_IMG =
  "https://images.unsplash.com/photo-1479839672679-a46483c0e7c8?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjAxODF8MHwxfHNlYXJjaHwzfHxtb2Rlcm4lMjBjb25kb21pbml1bSUyMGFyY2hpdGVjdHVyZXxlbnwwfHx8fDE3ODM2Mjk2ODZ8MA&ixlib=rb-4.1.0&q=85";
const LIMA_IMG =
  "https://images.unsplash.com/photo-1531968455001-5c5272a41129?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NTYxODF8MHwxfHNlYXJjaHwyfHxsaW1hJTIwcGVydSUyMGNpdHl8ZW58MHx8fHwxNzgzNjI5Njg2fDA&ixlib=rb-4.1.0&q=85";

const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  visible: (i = 0) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.55, delay: i * 0.08, ease: "easeOut" },
  }),
};

const steps = [
  {
    icon: Upload,
    title: "Sube tus documentos",
    desc: "Facturas, estados de cuenta bancarios, recibos, actas y presupuestos. Aceptamos PDF, imágenes, Excel y CSV.",
  },
  {
    icon: BrainCircuit,
    title: "La IA audita todo",
    desc: "Google Gemini, la IA más avanzada, cruza cada documento: concilia cuentas, detecta duplicados, pagos sin sustento e irregularidades.",
  },
  {
    icon: FileBadge,
    title: "Recibe tu informe legal",
    desc: "Informe profesional en PDF con hallazgos, severidades, recomendaciones y opinión del auditor, listo para el fin que decidas.",
  },
];

const features = [
  {
    icon: FileSearch,
    title: "Detección de irregularidades",
    desc: "Identifica pagos duplicados, montos inconsistentes, retiros inusuales y gastos sin sustento documentario.",
  },
  {
    icon: Landmark,
    title: "Conciliación bancaria",
    desc: "Cruza estados de cuenta con facturas y recibos para verificar que cada egreso tenga respaldo real.",
  },
  {
    icon: ShieldCheck,
    title: "Marco legal peruano",
    desc: "Análisis conforme a la Ley N° 27157, su Reglamento (D.S. N° 035-2006-VIVIENDA) y las Normas Internacionales de Auditoría.",
  },
  {
    icon: FileCheck2,
    title: "Informe con valor legal",
    desc: "PDF profesional con código de verificación, apto para juntas de propietarios, administraciones o procedimientos legales.",
  },
  {
    icon: ScanLine,
    title: "Lectura de cualquier formato",
    desc: "Facturas escaneadas, fotos de recibos, PDFs bancarios o planillas Excel: la IA lee y entiende todo.",
  },
  {
    icon: Building2,
    title: "Hecho para condominios",
    desc: "Diseñado para juntas de propietarios, administradores y residentes que exigen transparencia en las cuentas.",
  },
];

export default function Landing() {
  const [pricing, setPricing] = useState({ price_small: 1100, price_medium: 2100 });

  useEffect(() => {
    api
      .get("/public/settings")
      .then(({ data }) => setPricing(data))
      .catch(() => {});
  }, []);

  const [form, setForm] = useState({ name: "", email: "", phone: "", message: "" });
  const [sending, setSending] = useState(false);

  const submitContact = async (e) => {
    e.preventDefault();
    setSending(true);
    try {
      await api.post("/contact", form);
      toast.success("Mensaje enviado. Te contactaremos pronto.");
      setForm({ name: "", email: "", phone: "", message: "" });
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail));
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="bg-[#020617] text-slate-100 min-h-screen">
      {/* NAV */}
      <nav className="glass-nav fixed top-0 inset-x-0 z-50" data-testid="landing-nav">
        <div className="max-w-7xl mx-auto px-6 lg:px-10 h-16 flex items-center justify-between">
          <a href="#inicio" className="font-heading font-black text-xl tracking-tight" data-testid="nav-logo">
            OnBuy<span className="text-[#0EA5E9]">Solutions</span>
          </a>
          <div className="hidden md:flex items-center gap-8 text-sm text-slate-300">
            <a href="#como-funciona" className="hover:text-white transition-colors" data-testid="nav-link-como-funciona">Cómo funciona</a>
            <a href="#servicios" className="hover:text-white transition-colors" data-testid="nav-link-servicios">Servicios</a>
            <a href="#consultoria" className="hover:text-white transition-colors" data-testid="nav-link-consultoria">Consultoría</a>
            <a href="#precios" className="hover:text-white transition-colors" data-testid="nav-link-precios">Precios</a>
            <a href="#contacto" className="hover:text-white transition-colors" data-testid="nav-link-contacto">Contacto</a>
          </div>
          <Link
            to="/acceso"
            data-testid="nav-login-btn"
            className="bg-[#0284C7] hover:bg-[#0EA5E9] text-white text-sm font-semibold px-5 py-2.5 rounded-full transition-colors"
          >
            Acceder al panel
          </Link>
        </div>
      </nav>

      {/* HERO */}
      <header id="inicio" className="relative min-h-screen flex items-center grain overflow-hidden">
        <div className="absolute inset-0">
          <img src={HERO_IMG} alt="Condominio moderno" className="w-full h-full object-cover" />
          <div className="absolute inset-0 bg-gradient-to-r from-[#020617] via-[#020617]/85 to-[#020617]/40" />
        </div>
        <div className="relative max-w-7xl mx-auto px-6 lg:px-10 w-full pt-28 pb-20">
          <div className="max-w-3xl">
            <motion.p
              variants={fadeUp}
              initial="hidden"
              animate="visible"
              custom={0}
              className="text-xs tracking-[0.3em] uppercase text-[#0EA5E9] font-semibold mb-6"
            >
              Auditoría inteligente de condominios · Perú
            </motion.p>
            <motion.h1
              variants={fadeUp}
              initial="hidden"
              animate="visible"
              custom={1}
              className="font-heading font-black text-4xl sm:text-5xl lg:text-6xl leading-[1.05] tracking-tight text-white"
              data-testid="hero-title"
            >
              Las cuentas de tu condominio, auditadas por{" "}
              <span className="text-[#0EA5E9]">Inteligencia Artificial</span>
            </motion.h1>
            <motion.p
              variants={fadeUp}
              initial="hidden"
              animate="visible"
              custom={2}
              className="mt-8 text-base md:text-lg text-slate-300 leading-relaxed max-w-2xl"
            >
              Sube facturas, estados de cuenta y recibos. Nuestra IA — Google Gemini, la más
              avanzada del mundo — realiza la auditoría completa y genera un informe profesional
              con valor legal en minutos, no en semanas.
            </motion.p>
            <motion.div
              variants={fadeUp}
              initial="hidden"
              animate="visible"
              custom={3}
              className="mt-10 flex flex-col sm:flex-row gap-4"
            >
              <Link
                to="/acceso"
                data-testid="hero-cta-btn"
                className="inline-flex items-center justify-center gap-2 bg-[#0284C7] hover:bg-[#0EA5E9] text-white font-semibold px-8 py-4 rounded-full text-base transition-colors"
              >
                Comenzar mi auditoría <ArrowRight size={18} />
              </Link>
              <a
                href="#como-funciona"
                data-testid="hero-secondary-btn"
                className="inline-flex items-center justify-center gap-2 border border-slate-600 hover:border-slate-300 text-slate-200 font-semibold px-8 py-4 rounded-full text-base transition-colors"
              >
                Ver cómo funciona
              </a>
            </motion.div>
            <motion.div
              variants={fadeUp}
              initial="hidden"
              animate="visible"
              custom={4}
              className="mt-16 grid grid-cols-3 gap-6 max-w-lg"
            >
              {[
                ["100%", "Documentos revisados"],
                ["8", "Secciones de informe"],
                ["24/7", "Disponible siempre"],
              ].map(([num, label]) => (
                <div key={label} className="border-l-2 border-[#0284C7] pl-4">
                  <p className="font-heading font-800 font-extrabold text-2xl text-white">{num}</p>
                  <p className="text-xs text-slate-400 mt-1">{label}</p>
                </div>
              ))}
            </motion.div>
          </div>
        </div>
      </header>

      {/* CÓMO FUNCIONA */}
      <section id="como-funciona" className="bg-[#F8FAFC] text-[#0F172A] py-24 lg:py-32">
        <div className="max-w-7xl mx-auto px-6 lg:px-10">
          <p className="text-xs tracking-[0.3em] uppercase text-[#0284C7] font-semibold mb-4">Proceso</p>
          <h2 className="font-heading font-black text-2xl sm:text-3xl lg:text-4xl tracking-tight max-w-2xl">
            Tres pasos. Cero complicaciones.
          </h2>
          <div className="mt-16 grid md:grid-cols-3 gap-8">
            {steps.map((s, i) => (
              <motion.div
                key={s.title}
                variants={fadeUp}
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true, margin: "-80px" }}
                custom={i}
                className="relative bg-white border border-slate-200 p-8 lg:p-10 group hover:border-[#0284C7] transition-colors"
                data-testid={`step-card-${i + 1}`}
              >
                <span className="font-heading font-black text-6xl text-slate-100 absolute top-6 right-8 group-hover:text-sky-50 transition-colors">
                  0{i + 1}
                </span>
                <s.icon className="text-[#0284C7]" size={32} strokeWidth={1.5} />
                <h3 className="font-heading font-bold text-xl mt-6">{s.title}</h3>
                <p className="text-slate-600 text-sm leading-relaxed mt-3">{s.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* SERVICIOS */}
      <section id="servicios" className="bg-[#020617] py-24 lg:py-32 grain relative">
        <div className="max-w-7xl mx-auto px-6 lg:px-10 relative">
          <p className="text-xs tracking-[0.3em] uppercase text-[#0EA5E9] font-semibold mb-4">Servicios</p>
          <h2 className="font-heading font-black text-2xl sm:text-3xl lg:text-4xl tracking-tight text-white max-w-2xl">
            Todo lo que un auditor haría, más rápido y sin sesgos
          </h2>
          <div className="mt-16 grid sm:grid-cols-2 lg:grid-cols-3 gap-px bg-slate-800">
            {features.map((f, i) => (
              <motion.div
                key={f.title}
                variants={fadeUp}
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true, margin: "-60px" }}
                custom={i % 3}
                className="bg-[#020617] p-8 lg:p-10 hover:bg-slate-900/60 transition-colors"
                data-testid={`feature-card-${i + 1}`}
              >
                <f.icon className="text-[#0EA5E9]" size={28} strokeWidth={1.5} />
                <h3 className="font-heading font-bold text-lg text-white mt-5">{f.title}</h3>
                <p className="text-slate-400 text-sm leading-relaxed mt-3">{f.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* PERÚ */}
      <section className="bg-[#F8FAFC] text-[#0F172A] py-24 lg:py-32">
        <div className="max-w-7xl mx-auto px-6 lg:px-10 grid lg:grid-cols-12 gap-12 items-center">
          <div className="lg:col-span-5">
            <img src={LIMA_IMG} alt="Lima, Perú" className="w-full h-[420px] object-cover" />
          </div>
          <div className="lg:col-span-7">
            <p className="text-xs tracking-[0.3em] uppercase text-[#0284C7] font-semibold mb-4">
              Especialistas en Perú
            </p>
            <h2 className="font-heading font-black text-2xl sm:text-3xl lg:text-4xl tracking-tight">
              Auditoría conforme a la normativa peruana
            </h2>
            <p className="mt-6 text-slate-600 leading-relaxed">
              Cada informe se elabora aplicando el marco legal que rige a los condominios y juntas
              de propietarios en el Perú, para que tenga sustento real ante cualquier instancia.
            </p>
            <ul className="mt-8 space-y-4">
              {[
                "Ley N° 27157 — Regularización de Edificaciones, Propiedad Exclusiva y Común",
                "D.S. N° 035-2006-VIVIENDA — TUO del Reglamento de la Ley N° 27157",
                "Normas Internacionales de Auditoría (NIA)",
                "Código Civil peruano y buenas prácticas contables",
              ].map((item) => (
                <li key={item} className="flex items-start gap-3 text-sm text-slate-700">
                  <CheckCircle2 className="text-[#0284C7] shrink-0 mt-0.5" size={18} />
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      {/* CONSULTORÍA INCLUIDA */}
      <section id="consultoria" className="bg-white py-24 lg:py-32" data-testid="section-consultoria">
        <div className="max-w-7xl mx-auto px-6 lg:px-10">
          <div className="flex items-center gap-3 mb-4">
            <p className="text-xs tracking-[0.3em] uppercase text-[#0284C7] font-semibold">Beneficio incluido</p>
            <span className="bg-emerald-50 border border-emerald-200 text-emerald-700 text-[10px] font-bold tracking-[0.15em] uppercase px-3 py-1 rounded-full" data-testid="consultoria-free-badge">
              Gratis con tu auditoría
            </span>
          </div>
          <h2 className="font-heading font-black text-2xl sm:text-3xl lg:text-4xl tracking-tight text-[#0F172A] max-w-3xl">
            1 hora de consultoría legal-contable por Zoom, incluida con cualquier auditoría
          </h2>
          <p className="text-slate-600 mt-4 max-w-2xl text-sm leading-relaxed">
            Al adquirir cualquier plan de auditoría, recibes una sesión de 1 hora por Zoom con
            nuestro consultor. Trabajamos tu caso en un expediente digital potenciado por IA que
            combina tres especialidades y produce entregables listos para usar.
          </p>

          <div className="mt-10 grid sm:grid-cols-3 gap-6 max-w-4xl">
            {[
              {
                icon: Scale,
                title: "Abogado civil, penal y contador",
                desc: "Análisis integral de tu caso con el marco legal peruano: Código Civil, Código Penal, Ley 27157 y normativa SUNAT.",
              },
              {
                icon: FileSignature,
                title: "Documentos listos para usar",
                desc: "Cartas notariales, denuncias, contratos y requerimientos redactados durante la sesión, descargables en PDF.",
              },
              {
                icon: FileBadge,
                title: "Informe final del expediente",
                desc: "Al cierre recibes un informe PDF con resumen de hechos, análisis, recomendaciones y todos los documentos emitidos.",
              },
            ].map((b, i) => (
              <motion.div
                key={b.title}
                variants={fadeUp}
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true, margin: "-60px" }}
                custom={i}
                className="flex flex-col gap-3"
                data-testid={`consultoria-benefit-${i}`}
              >
                <b.icon className="text-[#0284C7]" size={26} strokeWidth={1.5} />
                <h3 className="font-heading font-bold text-[#0F172A] text-sm">{b.title}</h3>
                <p className="text-xs text-slate-500 leading-relaxed">{b.desc}</p>
              </motion.div>
            ))}
          </div>

          <div className="mt-14 grid md:grid-cols-3 gap-6">
            {[
              {
                src: "/previews/consultoria-chat.jpg",
                caption: "Expediente del caso: análisis legal y documentos redactados al instante",
              },
              {
                src: "/previews/consultoria-biblioteca.jpg",
                caption: "Biblioteca del expediente: cada documento descargable en PDF",
              },
              {
                src: "/previews/consultoria-imagen.jpg",
                caption: "Diagramas y evidencia visual generados con IA para tu caso",
              },
            ].map((s, i) => (
              <motion.figure
                key={s.src}
                variants={fadeUp}
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true, margin: "-60px" }}
                custom={i}
                className="group"
                data-testid={`consultoria-preview-${i}`}
              >
                <div className="border border-slate-200 rounded-lg overflow-hidden shadow-lg shadow-slate-200/60 group-hover:shadow-xl group-hover:border-[#0284C7]/40 transition-all">
                  <div className="bg-slate-100 border-b border-slate-200 px-3 py-2 flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-red-300" />
                    <span className="w-2.5 h-2.5 rounded-full bg-amber-300" />
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-300" />
                    <span className="ml-2 text-[10px] text-slate-400 font-medium">OnBuySolutions — Consultoría</span>
                  </div>
                  <img src={s.src} alt={s.caption} loading="lazy" className="w-full h-auto" />
                </div>
                <figcaption className="mt-3 text-xs text-slate-500 leading-relaxed flex items-start gap-2">
                  <CheckCircle2 className="text-[#0284C7] shrink-0 mt-0.5" size={14} />
                  {s.caption}
                </figcaption>
              </motion.figure>
            ))}
          </div>

          <div className="mt-12 bg-[#F8FAFC] border border-slate-200 p-6 lg:p-8 flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6" data-testid="consultoria-zoom-banner">
            <div className="flex items-start gap-4">
              <Video className="text-[#0284C7] shrink-0" size={28} strokeWidth={1.5} />
              <div>
                <h3 className="font-heading font-bold text-[#0F172A]">Sesión en vivo por Zoom</h3>
                <p className="text-sm text-slate-500 mt-1 max-w-xl leading-relaxed">
                  Agenda tu hora al confirmar tu auditoría: revisamos juntos tus hallazgos, resolvemos
                  tus dudas legales y contables, y te entregamos los documentos de tu expediente.
                </p>
              </div>
            </div>
            <Link
              to="/acceso"
              data-testid="consultoria-cta"
              className="shrink-0 inline-flex items-center gap-2 bg-[#0284C7] hover:bg-[#0EA5E9] text-white font-semibold px-6 py-3 rounded-full text-sm transition-colors"
            >
              Empezar mi auditoría <ArrowRight size={16} />
            </Link>
          </div>
        </div>
      </section>

      {/* PRECIOS */}
      <section id="precios" className="bg-[#020617] py-24 lg:py-32 grain relative">
        <div className="max-w-7xl mx-auto px-6 lg:px-10 relative">
          <p className="text-xs tracking-[0.3em] uppercase text-[#0EA5E9] font-semibold mb-4">Precios</p>
          <h2 className="font-heading font-black text-2xl sm:text-3xl lg:text-4xl tracking-tight text-white max-w-2xl">
            Tarifas claras, por año auditado
          </h2>
          <p className="text-slate-400 mt-4 max-w-xl text-sm leading-relaxed">
            Un pago único por cada año de documentación procesada: estados de cuenta bancarios,
            facturas y recibos de mantenimiento.
          </p>
          <div className="mt-14 grid md:grid-cols-2 gap-8 max-w-4xl">
            {[
              {
                name: "Condominio pequeño",
                target: "Menos de 50 departamentos",
                price: Number(pricing.price_small).toLocaleString("es-PE"),
                testid: "pricing-card-pequeno",
                featured: false,
              },
              {
                name: "Condominio mediano a grande",
                target: "De 50 a 150 departamentos",
                price: Number(pricing.price_medium).toLocaleString("es-PE"),
                testid: "pricing-card-mediano",
                featured: true,
              },
            ].map((p, i) => (
              <motion.div
                key={p.name}
                variants={fadeUp}
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true, margin: "-60px" }}
                custom={i}
                data-testid={p.testid}
                className={`relative p-8 lg:p-10 border transition-colors ${
                  p.featured
                    ? "border-[#0EA5E9] bg-slate-900/70"
                    : "border-slate-700 bg-slate-900/40 hover:border-slate-500"
                }`}
              >
                {p.featured && (
                  <span className="absolute -top-3 left-8 bg-[#0284C7] text-white text-[10px] font-bold tracking-[0.2em] uppercase px-3 py-1 rounded-full">
                    Más solicitado
                  </span>
                )}
                <h3 className="font-heading font-bold text-lg text-white">{p.name}</h3>
                <p className="text-xs text-slate-400 mt-1">{p.target}</p>
                <div className="mt-6 flex items-baseline gap-2">
                  <span className="font-heading font-black text-5xl text-white">
                    <span className="text-2xl align-top text-[#0EA5E9]">S/ </span>
                    {p.price}
                  </span>
                  <span className="text-xs text-slate-400">por año auditado</span>
                </div>
                <ul className="mt-8 space-y-3">
                  {[
                    "Procesamiento de 12 meses de estados bancarios y recibos",
                    "Análisis completo con IA: duplicados, faltantes e irregularidades",
                    "Informe PDF profesional con valor legal y código de verificación",
                    "Hallazgos clasificados por severidad + recomendaciones",
                  ].map((feat) => (
                    <li key={feat} className="flex items-start gap-3 text-sm text-slate-300">
                      <CheckCircle2 className="text-[#0EA5E9] shrink-0 mt-0.5" size={16} />
                      {feat}
                    </li>
                  ))}
                </ul>
                <div className="mt-6 bg-emerald-500/10 border border-emerald-500/30 px-4 py-3 flex items-start gap-3 rounded" data-testid={`${p.testid}-consultoria-bonus`}>
                  <Video className="text-emerald-400 shrink-0 mt-0.5" size={16} />
                  <p className="text-xs text-emerald-300 leading-relaxed">
                    <b>GRATIS:</b> 1 hora de consultoría legal-contable por Zoom con tu auditoría.
                  </p>
                </div>
                <Link
                  to="/acceso"
                  data-testid={`${p.testid}-cta`}
                  className={`mt-10 inline-flex w-full items-center justify-center gap-2 font-semibold px-6 py-3.5 rounded-full text-sm transition-colors ${
                    p.featured
                      ? "bg-[#0284C7] hover:bg-[#0EA5E9] text-white"
                      : "border border-slate-600 hover:border-slate-300 text-slate-200"
                  }`}
                >
                  Solicitar auditoría <ArrowRight size={16} />
                </Link>
              </motion.div>
            ))}
          </div>
          <p className="mt-10 text-sm text-slate-400" data-testid="pricing-custom-note">
            ¿Más de 150 departamentos o varios años por auditar?{" "}
            <a href="#contacto" className="text-[#0EA5E9] font-semibold hover:underline">
              Solicita una cotización personalizada
            </a>
            .
          </p>
        </div>
      </section>

      {/* CTA */}
      <section className="bg-[#0284C7] py-20">
        <div className="max-w-7xl mx-auto px-6 lg:px-10 flex flex-col lg:flex-row items-start lg:items-center justify-between gap-8">
          <div>
            <h2 className="font-heading font-black text-2xl sm:text-3xl lg:text-4xl tracking-tight text-white max-w-xl">
              ¿Sospechas de las cuentas de tu condominio?
            </h2>
            <p className="text-sky-100 mt-3 max-w-xl">
              Obtén claridad hoy mismo con una auditoría completa impulsada por IA.
            </p>
          </div>
          <Link
            to="/acceso"
            data-testid="cta-banner-btn"
            className="inline-flex items-center gap-2 bg-[#020617] hover:bg-slate-900 text-white font-semibold px-8 py-4 rounded-full transition-colors shrink-0"
          >
            Crear cuenta gratis <ArrowRight size={18} />
          </Link>
        </div>
      </section>

      {/* CONTACTO */}
      <section id="contacto" className="bg-[#020617] py-24 lg:py-32">
        <div className="max-w-7xl mx-auto px-6 lg:px-10 grid lg:grid-cols-2 gap-16">
          <div>
            <p className="text-xs tracking-[0.3em] uppercase text-[#0EA5E9] font-semibold mb-4">Contacto</p>
            <h2 className="font-heading font-black text-2xl sm:text-3xl lg:text-4xl tracking-tight text-white">
              Hablemos de tu condominio
            </h2>
            <p className="text-slate-400 mt-6 leading-relaxed max-w-md">
              ¿Tienes dudas sobre el servicio, los documentos necesarios o el valor legal del
              informe? Escríbenos y un especialista de OnBuySolutions te responderá.
            </p>
          </div>
          <form onSubmit={submitContact} className="space-y-5" data-testid="contact-form">
            <div className="grid sm:grid-cols-2 gap-5">
              <input
                required
                data-testid="contact-name-input"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="Nombre completo"
                className="w-full bg-slate-900 border border-slate-700 focus:border-[#0EA5E9] outline-none text-white px-5 py-4 text-sm transition-colors"
              />
              <input
                required
                type="email"
                data-testid="contact-email-input"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                placeholder="Correo electrónico"
                className="w-full bg-slate-900 border border-slate-700 focus:border-[#0EA5E9] outline-none text-white px-5 py-4 text-sm transition-colors"
              />
            </div>
            <input
              data-testid="contact-phone-input"
              value={form.phone}
              onChange={(e) => setForm({ ...form, phone: e.target.value })}
              placeholder="Teléfono (opcional)"
              className="w-full bg-slate-900 border border-slate-700 focus:border-[#0EA5E9] outline-none text-white px-5 py-4 text-sm transition-colors"
            />
            <textarea
              required
              rows={4}
              data-testid="contact-message-input"
              value={form.message}
              onChange={(e) => setForm({ ...form, message: e.target.value })}
              placeholder="Cuéntanos sobre tu condominio y qué necesitas auditar…"
              className="w-full bg-slate-900 border border-slate-700 focus:border-[#0EA5E9] outline-none text-white px-5 py-4 text-sm transition-colors resize-none"
            />
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

      {/* FOOTER */}
      <footer className="bg-[#020617] border-t border-slate-800 py-10">
        <div className="max-w-7xl mx-auto px-6 lg:px-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <div>
            <p className="font-heading font-black text-lg">
              OnBuy<span className="text-[#0EA5E9]">Solutions</span>
            </p>
            <p className="text-xs text-slate-500 mt-2">
              © {new Date().getFullYear()} OnBuySolutions — Auditorías de condominios con IA · Perú
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-xs text-slate-400">
            <Link to="/terminos" className="hover:text-white transition-colors" data-testid="footer-link-terminos">
              Términos y Condiciones
            </Link>
            <Link to="/privacidad" className="hover:text-white transition-colors" data-testid="footer-link-privacidad">
              Política de Privacidad
            </Link>
            <Link to="/uso-ia" className="hover:text-white transition-colors" data-testid="footer-link-uso-ia">
              Aviso de Uso de IA
            </Link>
          </div>
        </div>
        <div className="max-w-7xl mx-auto px-6 lg:px-10 mt-6 pt-6 border-t border-slate-900">
          <p className="text-[11px] text-slate-600 leading-relaxed max-w-4xl">
            OnBuySolutions es un proveedor de servicios tecnológicos (SaaS) y no una entidad financiera: no
            capta depósitos del público ni administra fondos de terceros, por lo que no se encuentra bajo
            supervisión de la SBS ni de la SMV. Los informes son generados mediante algoritmos automatizados
            de Inteligencia Artificial y requieren la supervisión y validación final del usuario humano,
            conforme a la Ley N° 31814 y su Reglamento (D.S. N° 115-2025-PCM). Tratamiento de datos conforme a
            la Ley N° 29733 y D.S. N° 016-2024-JUS.
          </p>
        </div>
      </footer>
    </div>
  );
}
