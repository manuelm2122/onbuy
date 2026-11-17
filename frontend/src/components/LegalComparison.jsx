import { Check, Minus } from "lucide-react";

const ROWS = [
  ["Tu caso guardado", "Expediente por caso con todo el historial y tus archivos; lo retomas cuando quieras", "Conversaciones sueltas que se pierden o se mezclan"],
  ["Especialización", "Agente configurado como abogado civil, penal y contador del Perú", "Asistente genérico para cualquier tema y país"],
  ["Documentos", "Cartas notariales, denuncias y demandas listas en PDF, con biblioteca por caso e informe final", "Texto para copiar, pegar y dar formato por tu cuenta"],
  ["Cálculos", "Calculadoras exactas por fórmula: beneficios sociales, intereses legales, alimentos devengados y alquileres, mes a mes", "Aritmética hecha por la IA, que puede equivocarse"],
  ["Plazos", "Línea de tiempo del caso con recordatorios por correo antes de cada vencimiento", "No te avisa de nada"],
  ["Citas legales", "Botón \"Verificar citas\": busca cada norma citada en fuentes públicas, te muestra el enlace y marca las dudosas", "Puede citar artículos que no existen sin advertirlo"],
  ["Respaldo", "Empresa peruana con RUC, Libro de Reclamaciones y protección de datos bajo la ley peruana", "Sin atención local ni responsable en el Perú"],
];

export const LegalComparison = () => (
  <section id="comparativa" className="bg-[#F8FAFC] text-[#0F172A] py-24 lg:py-32 scroll-mt-16" data-testid="legal-comparison">
    <div className="max-w-7xl mx-auto px-6 lg:px-10">
      <p className="text-xs tracking-[0.3em] uppercase text-[#0284C7] font-semibold mb-4">La pregunta que más nos hacen</p>
      <h2 className="font-heading font-black text-2xl sm:text-3xl lg:text-4xl tracking-tight max-w-3xl">
        ¿Qué obtengo aquí que no me da una IA gratuita?
      </h2>
      <p className="mt-5 text-slate-600 text-sm md:text-base leading-relaxed max-w-2xl">
        ChatGPT, Gemini, Copilot o Grok sirven para resolver dudas generales. Llevar un caso real necesita orden,
        cálculos exactos, documentos listos y alguien que responda.
      </p>
      <div className="mt-14 border border-slate-200 bg-white">
        <div className="hidden md:grid grid-cols-[200px_1fr_1fr] border-b border-slate-200 text-xs tracking-[0.15em] uppercase font-semibold">
          <span className="p-5 text-slate-400" />
          <span className="p-5 bg-[#020617] text-white">OnBuySolutions</span>
          <span className="p-5 text-slate-500">IA gratuita de uso general</span>
        </div>
        {ROWS.map(([topic, ours, theirs], i) => (
          <div key={topic} className="grid md:grid-cols-[200px_1fr_1fr] border-b last:border-b-0 border-slate-200" data-testid={`comparison-row-${i}`}>
            <p className="p-5 pb-0 md:pb-5 font-heading font-bold text-sm">{topic}</p>
            <p className="p-5 text-sm leading-relaxed flex items-start gap-3 md:bg-sky-50/60">
              <Check size={18} className="text-[#0284C7] shrink-0 mt-0.5" strokeWidth={2.5} /> {ours}
            </p>
            <p className="p-5 pt-0 md:pt-5 text-sm leading-relaxed text-slate-500 flex items-start gap-3">
              <Minus size={18} className="text-slate-300 shrink-0 mt-0.5" /> {theirs}
            </p>
          </div>
        ))}
      </div>
      <p className="text-[11px] text-slate-400 mt-5 max-w-3xl leading-relaxed">
        La asesoría es orientación informativa y no reemplaza el patrocinio de un abogado colegiado en un proceso judicial.
        La verificación de citas es una comprobación automática: confirma siempre en la fuente oficial.
      </p>
    </div>
  </section>
);
