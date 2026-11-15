import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight, ArrowUpRight, Quote, Sparkles, ShieldCheck, Zap, HeartHandshake } from "lucide-react";
import { api } from "@/lib/api";
import { SERVICES, HOME_HERO_IMG } from "@/constants/services";
import { SiteNav } from "@/components/SiteNav";
import { SiteFooter } from "@/components/SiteFooter";
import { WhatsAppButton } from "@/components/WhatsAppButton";
import { ContactSection } from "@/components/ContactSection";
import { BlogCard } from "@/components/BlogCard";

const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  visible: (i = 0) => ({ opacity: 1, y: 0, transition: { duration: 0.55, delay: i * 0.08, ease: "easeOut" } }),
};

const STATS = [
  ["5", "Servicios digitales"],
  ["+320", "Clientes atendidos"],
  ["+1,800", "Documentos procesados"],
  ["24/7", "Plataforma disponible"],
];

const TESTIMONIALS = [
  {
    name: "Carla Rojas",
    role: "Presidenta de junta, Residencial Los Cedros",
    text: "En dos días tuvimos un informe claro de las cuentas del edificio. Encontramos un pago duplicado que nadie había notado.",
  },
  {
    name: "Miguel Paredes",
    role: "Propietario, Surco",
    text: "Tenía un inquilino que no pagaba hace meses. Con el expediente y los documentos listos, mi abogado avanzó muchísimo más rápido.",
  },
  {
    name: "Lucía Huamán",
    role: "Dueña de cevichería, Miraflores",
    text: "Mis clientes escanean el QR y ven la carta con fotos. Cambio precios desde el celular y ya no imprimo nada.",
  },
];

const VALUES = [
  { icon: Sparkles, title: "Tecnología que se entiende", desc: "Inteligencia artificial y herramientas QR explicadas en simple, listas para usar desde el primer día." },
  { icon: ShieldCheck, title: "Hecho para el Perú", desc: "Normativa, moneda y realidad local. Empresa peruana identificable, con Libro de Reclamaciones." },
  { icon: Zap, title: "Resultados en minutos", desc: "Informes, documentos y catálogos que antes tomaban semanas, ahora al instante." },
  { icon: HeartHandshake, title: "Acompañamiento real", desc: "Seguimiento de tu caso o tu negocio, con soporte por WhatsApp y correo." },
];

const ServiceLink = ({ s, className, children, testid }) =>
  s.external ? (
    <a href={s.href} target="_blank" rel="noopener noreferrer" className={className} data-testid={testid}>{children}</a>
  ) : (
    <Link to={s.href} className={className} data-testid={testid}>{children}</Link>
  );

export default function Home() {
  const [posts, setPosts] = useState([]);
  const { hash } = useLocation();

  useEffect(() => {
    api.get("/blog").then(({ data }) => setPosts(data.slice(0, 3))).catch(() => {});
  }, []);

  useEffect(() => {
    if (hash) document.querySelector(hash)?.scrollIntoView({ behavior: "smooth" });
  }, [hash]);

  return (
    <div className="bg-[#020617] text-slate-100 min-h-screen" data-testid="home-page">
      <SiteNav />

      <header className="relative min-h-screen flex items-center grain overflow-hidden">
        <div className="absolute inset-0">
          <img src={HOME_HERO_IMG} alt="Lima de noche" className="w-full h-full object-cover" />
          <div className="absolute inset-0 bg-gradient-to-r from-[#020617] via-[#020617]/80 to-[#020617]/30" />
        </div>
        <div className="relative max-w-7xl mx-auto px-6 lg:px-10 w-full pt-28 pb-20">
          <div className="max-w-3xl">
            <motion.p variants={fadeUp} initial="hidden" animate="visible" custom={0} className="text-xs tracking-[0.3em] uppercase text-[#0EA5E9] font-semibold mb-6">
              Servicios digitales · Perú
            </motion.p>
            <motion.h1 variants={fadeUp} initial="hidden" animate="visible" custom={1} className="font-heading font-black text-4xl sm:text-5xl lg:text-6xl leading-[1.05] tracking-tight text-white" data-testid="home-hero-title">
              Soluciones digitales que <span className="text-[#0EA5E9]">resuelven</span> problemas reales
            </motion.h1>
            <motion.p variants={fadeUp} initial="hidden" animate="visible" custom={2} className="mt-8 text-base md:text-lg text-slate-300 leading-relaxed max-w-2xl">
              Auditamos las cuentas de tu condominio con inteligencia artificial, te asesoramos en tus casos
              legales y contables, y digitalizamos tu restaurante, hotel o tienda con menús y catálogos QR.
            </motion.p>
            <motion.div variants={fadeUp} initial="hidden" animate="visible" custom={3} className="mt-10 flex flex-col sm:flex-row gap-4">
              <a href="#servicios" data-testid="home-hero-cta" className="inline-flex items-center justify-center gap-2 bg-[#0284C7] hover:bg-[#0EA5E9] text-white font-semibold px-8 py-4 rounded-full text-base transition-colors">
                Ver servicios <ArrowRight size={18} />
              </a>
              <a href="#contacto" data-testid="home-hero-secondary" className="inline-flex items-center justify-center gap-2 border border-slate-600 hover:border-slate-300 text-slate-200 font-semibold px-8 py-4 rounded-full text-base transition-colors">
                Hablar con un especialista
              </a>
            </motion.div>
          </div>
          <motion.div variants={fadeUp} initial="hidden" animate="visible" custom={4} className="mt-20 grid grid-cols-2 md:grid-cols-4 gap-6 max-w-3xl" data-testid="home-stats">
            {STATS.map(([num, label]) => (
              <div key={label} className="border-l-2 border-[#0284C7] pl-4">
                <p className="font-heading font-extrabold text-2xl text-white">{num}</p>
                <p className="text-xs text-slate-400 mt-1">{label}</p>
              </div>
            ))}
          </motion.div>
        </div>
      </header>

      <section id="servicios" className="bg-[#F8FAFC] text-[#0F172A] py-24 lg:py-32" data-testid="section-servicios">
        <div className="max-w-7xl mx-auto px-6 lg:px-10">
          <p className="text-xs tracking-[0.3em] uppercase text-[#0284C7] font-semibold mb-4">Nuestros servicios</p>
          <h2 className="font-heading font-black text-2xl sm:text-3xl lg:text-4xl tracking-tight max-w-2xl">
            Cinco servicios, una sola empresa detrás
          </h2>
          <div className="mt-16 grid md:grid-cols-6 gap-6">
            {SERVICES.map((s, i) => (
              <motion.div
                key={s.key}
                variants={fadeUp}
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true, margin: "-60px" }}
                custom={i % 3}
                className={i < 2 ? "md:col-span-3" : "md:col-span-2"}
              >
                <ServiceLink s={s} testid={`service-card-${s.key}`} className="group relative flex flex-col justify-end h-full min-h-[380px] overflow-hidden bg-[#020617] text-white">
                  <img src={s.image} alt={s.title} loading="lazy" className="absolute inset-0 w-full h-full object-cover opacity-60 group-hover:opacity-45 group-hover:scale-105 transition-[opacity,transform] duration-500" />
                  <div className="absolute inset-0 bg-gradient-to-t from-[#020617] via-[#020617]/70 to-transparent" />
                  <div className="relative p-8">
                    <div className="flex items-center gap-3">
                      <span className="w-10 h-10 rounded-full bg-[#0284C7] flex items-center justify-center">
                        <s.icon size={18} strokeWidth={1.75} />
                      </span>
                      <span className="text-[10px] tracking-[0.2em] uppercase text-sky-300 font-semibold">{s.tag}</span>
                    </div>
                    <h3 className="font-heading font-bold text-xl mt-5 leading-snug">{s.title}</h3>
                    <p className="text-sm text-slate-300 leading-relaxed mt-3">{s.desc}</p>
                    <span className="mt-6 inline-flex items-center gap-1.5 text-sm font-semibold text-[#38BDF8]">
                      {s.cta}
                      {s.external ? <ArrowUpRight size={16} /> : <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform" />}
                    </span>
                  </div>
                </ServiceLink>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      <section className="bg-[#020617] py-24 lg:py-32 grain relative" data-testid="section-valores">
        <div className="max-w-7xl mx-auto px-6 lg:px-10 relative grid lg:grid-cols-12 gap-12">
          <div className="lg:col-span-4">
            <p className="text-xs tracking-[0.3em] uppercase text-[#0EA5E9] font-semibold mb-4">Por qué OnBuySolutions</p>
            <h2 className="font-heading font-black text-2xl sm:text-3xl lg:text-4xl tracking-tight text-white">
              Digital, simple y con respaldo
            </h2>
          </div>
          <div className="lg:col-span-8 grid sm:grid-cols-2 gap-px bg-slate-800">
            {VALUES.map((v, i) => (
              <motion.div key={v.title} variants={fadeUp} initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-60px" }} custom={i % 2} className="bg-[#020617] p-8 lg:p-10 hover:bg-slate-900/60 transition-colors" data-testid={`value-card-${i}`}>
                <v.icon className="text-[#0EA5E9]" size={28} strokeWidth={1.5} />
                <h3 className="font-heading font-bold text-lg text-white mt-5">{v.title}</h3>
                <p className="text-slate-400 text-sm leading-relaxed mt-3">{v.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      <section className="bg-white text-[#0F172A] py-24 lg:py-32" data-testid="section-testimonios">
        <div className="max-w-7xl mx-auto px-6 lg:px-10">
          <p className="text-xs tracking-[0.3em] uppercase text-[#0284C7] font-semibold mb-4">Testimonios</p>
          <h2 className="font-heading font-black text-2xl sm:text-3xl lg:text-4xl tracking-tight max-w-2xl">
            Lo que dicen quienes ya lo usaron
          </h2>
          <div className="mt-14 grid md:grid-cols-3 gap-8">
            {TESTIMONIALS.map((t, i) => (
              <motion.figure key={t.name} variants={fadeUp} initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-60px" }} custom={i} className="border border-slate-200 p-8 lg:p-10 flex flex-col" data-testid={`testimonial-${i}`}>
                <Quote className="text-[#0284C7]" size={28} strokeWidth={1.5} />
                <blockquote className="mt-6 text-slate-700 leading-relaxed flex-1">{t.text}</blockquote>
                <figcaption className="mt-8 pt-6 border-t border-slate-200">
                  <p className="font-heading font-bold text-sm">{t.name}</p>
                  <p className="text-xs text-slate-500 mt-1">{t.role}</p>
                </figcaption>
              </motion.figure>
            ))}
          </div>
          <p className="text-[11px] text-slate-400 mt-6">Testimonios y cifras de ejemplo.</p>
        </div>
      </section>

      {posts.length > 0 && (
        <section className="bg-[#020617] py-24 lg:py-32" data-testid="section-blog">
          <div className="max-w-7xl mx-auto px-6 lg:px-10">
            <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-6">
              <div>
                <p className="text-xs tracking-[0.3em] uppercase text-[#0EA5E9] font-semibold mb-4">Blog</p>
                <h2 className="font-heading font-black text-2xl sm:text-3xl lg:text-4xl tracking-tight text-white max-w-2xl">
                  Casos y guías prácticas
                </h2>
              </div>
              <Link to="/blog" className="inline-flex items-center gap-2 text-sm font-semibold text-[#0EA5E9] hover:text-white transition-colors" data-testid="home-blog-all-link">
                Ver todos los artículos <ArrowRight size={16} />
              </Link>
            </div>
            <div className="mt-14 grid md:grid-cols-3 gap-8">
              {posts.map((p) => <BlogCard key={p.id} post={p} dark />)}
            </div>
          </div>
        </section>
      )}

      <ContactSection />
      <SiteFooter />
      <WhatsAppButton />
    </div>
  );
}
