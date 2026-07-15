import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown } from "lucide-react";

const FAQS = [
  {
    q: "¿OnBuySolutions cuenta con abogados en su equipo? ¿Cómo pueden brindar orientación legal?",
    a: (
      <>
        <p>
          Somos una <b className="text-slate-200">empresa de tecnología</b> — con actividades registradas ante SUNAT
          bajo los CIIU 6201 (Programación informática) y 6311 (Procesamiento de datos, hospedaje y actividades
          conexas) — y no un estudio de abogados: nuestro equipo no está integrado por abogados. Lo que ofrecemos es{" "}
          <b className="text-slate-200">orientación informativa legal y contable</b> elaborada con inteligencia
          artificial entrenada en la normativa peruana, siempre con referencias normativas verificables.
        </p>
        <p>
          La legislación peruana reserva a los abogados colegiados únicamente el{" "}
          <b className="text-slate-200">patrocinio judicial</b> (artículos 285 y 286 de la Ley Orgánica del Poder
          Judicial); la orientación informativa, como la que brindamos, no constituye patrocinio ni defensa legal. Por
          ello, si decides iniciar acciones judiciales, te recomendamos validar la estrategia con un abogado colegiado
          de tu confianza: nuestros informes te permitirán llegar a esa etapa con el caso documentado, ordenado y
          sustentado, reduciendo significativamente las horas de honorarios profesionales.
        </p>
      </>
    ),
  },
  {
    q: "¿Un informe elaborado con inteligencia artificial carece de valor legal?",
    a: (
      <>
        <p>
          No. En el Perú, el uso de la inteligencia artificial es lícito y promovido por el Estado mediante la{" "}
          <b className="text-slate-200">Ley N.° 31814</b> y su Reglamento (Decreto Supremo N.° 115-2025-PCM, vigente
          desde enero de 2026), que exigen un uso responsable, transparente y con supervisión humana — principios que
          cumplimos declarando expresamente en cada informe que fue generado con IA.
        </p>
        <p>
          Jurídicamente, nuestro informe constituye un <b className="text-slate-200">documento privado</b> (artículo
          233 y siguientes del Código Procesal Civil): es admisible como medio probatorio y el juez lo valora en
          conjunto con la documentación que lo sustenta. Dado que cada hallazgo se referencia a los comprobantes,
          estados de cuenta y actas que tú mismo aportas, su fuerza descansa en esa{" "}
          <b className="text-slate-200">evidencia documental verificable</b>, no en quién — o qué herramienta — lo
          redactó.
        </p>
      </>
    ),
  },
  {
    q: "¿Se requiere alguna autorización o permiso especial para brindar este servicio en el Perú?",
    a: (
      <>
        <p>
          No. Los servicios de análisis documental automatizado y procesamiento de datos que brindamos se encuentran
          comprendidos en las actividades económicas que ONBUYSOLUTIONS S.A.C. (RUC 20606439327) tiene{" "}
          <b className="text-slate-200">registradas ante SUNAT</b> (CIIU 6201 y 6311), y se ejercen al amparo de las
          libertades de empresa e iniciativa privada reconocidas en los artículos 58 y 59 de la Constitución Política
          del Perú.
        </p>
        <p>
          No requerimos licencias sectoriales adicionales porque <b className="text-slate-200">no realizamos
          actividades reguladas reservadas</b>: no emitimos dictámenes de auditoría financiera (reservados por la Ley
          N.° 13253 y la Ley N.° 28951 al Contador Público Colegiado) ni ejercemos patrocinio judicial. Asimismo,
          cumplimos la Ley N.° 29733 — Ley de Protección de Datos Personales — y la normativa peruana sobre
          inteligencia artificial.
        </p>
      </>
    ),
  },
  {
    q: "¿El informe final equivale a una auditoría financiera tradicional, cuyo costo asciende de S/ 8,000 a S/ 12,000?",
    a: (
      <>
        <p>
          Son productos de naturaleza distinta, y lo señalamos con total transparencia. Un{" "}
          <b className="text-slate-200">dictamen de auditoría financiera</b> solo puede ser emitido por un Contador
          Público Colegiado o una Sociedad de Auditoría inscrita (Ley N.° 28951) y es exigible únicamente en supuestos
          regulados, como los estados financieros auditados de determinadas empresas.
        </p>
        <p>
          Nuestro informe es una <b className="text-slate-200">revisión técnica y documental independiente</b>:
          verifica el cuadre de ingresos y egresos, detecta inconsistencias, gastos sin sustento y posibles
          irregularidades sobre la documentación real de tu condominio, con el valor de un documento privado admisible
          como prueba. Para el objetivo que persigue un propietario — transparentar las cuentas de la junta o de la
          administración, sustentar reclamos y decidir si escalar el caso — cumple la misma función práctica, a una
          fracción del costo y en horas en lugar de semanas.
        </p>
        <p>
          Y si tu caso amerita un proceso formal, nuestro informe será el mejor punto de partida para la sociedad de
          auditoría o el abogado que decidas contratar.
        </p>
      </>
    ),
  },
  {
    q: "¿En qué se diferencia su servicio de consultar directamente a ChatGPT, Grok u otra IA de uso general?",
    a: (
      <>
        <p>
          La diferencia está en la <b className="text-slate-200">especialización, el procesamiento de tu documentación
          real y el resultado profesional</b>. Un chat de uso general responde en abstracto y limitado a lo que puedas
          copiar y pegar en la conversación; nuestro sistema procesa de forma masiva y estructurada los estados de
          cuenta, comprobantes, actas y presupuestos reales de tu condominio, cruza los datos entre sí (cuadre de
          ingresos y egresos, gastos sin sustento, inconsistencias) y aplica motores de análisis configurados
          específicamente con la normativa peruana aplicable a condominios y juntas de propietarios.
        </p>
        <p>
          El resultado tampoco es comparable: no recibes una respuesta suelta en un chat, sino un{" "}
          <b className="text-slate-200">informe profesional descargable en PDF</b>, con estructura de auditoría,
          hallazgos referenciados a tu evidencia documental y recomendaciones accionables — un documento que puedes
          presentar ante tu junta de propietarios o utilizar como medio probatorio. Además, tu caso queda guardado en
          tu panel con su biblioteca de documentos y seguimiento multi-sesión.
        </p>
        <p>
          Finalmente, detrás del servicio hay una <b className="text-slate-200">empresa peruana identificable</b>{" "}
          (ONBUYSOLUTIONS S.A.C., RUC 20606439327) que responde por el servicio: soporte real, Libro de Reclamaciones,
          cumplimiento de la Ley N.° 29733 de Protección de Datos Personales y de la normativa peruana de IA. Un chat
          genérico no asume ninguna de esas responsabilidades frente a ti como consumidor.
        </p>
      </>
    ),
  },
];

export const FaqSection = () => {
  const [open, setOpen] = useState(0);

  return (
    <section id="faq" className="bg-[#020617] py-24 lg:py-32 border-t border-slate-800/60" data-testid="section-faq">
      <div className="max-w-4xl mx-auto px-6 lg:px-10">
        <p className="text-xs tracking-[0.3em] uppercase text-[#0EA5E9] font-semibold mb-4">Transparencia</p>
        <h2 className="font-heading font-black text-2xl sm:text-3xl lg:text-4xl tracking-tight text-white" data-testid="faq-title">
          Preguntas frecuentes
        </h2>
        <p className="text-slate-400 mt-4 max-w-2xl">
          Respondemos con claridad las dudas legales más comunes sobre nuestro servicio, conforme a la normativa
          peruana vigente.
        </p>

        <div className="mt-12 divide-y divide-slate-800 border-y border-slate-800">
          {FAQS.map((item, i) => (
            <div key={i} data-testid={`faq-item-${i}`}>
              <button
                type="button"
                onClick={() => setOpen(open === i ? null : i)}
                data-testid={`faq-question-${i}`}
                aria-expanded={open === i}
                className="w-full flex items-start justify-between gap-6 py-6 text-left group"
              >
                <span className={`font-heading font-bold text-base sm:text-lg tracking-tight transition-colors ${open === i ? "text-[#0EA5E9]" : "text-white group-hover:text-[#0EA5E9]"}`}>
                  {item.q}
                </span>
                <ChevronDown
                  size={20}
                  className={`shrink-0 mt-1 transition-transform duration-300 ${open === i ? "rotate-180 text-[#0EA5E9]" : "text-slate-500"}`}
                />
              </button>
              <AnimatePresence initial={false}>
                {open === i && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.28, ease: "easeInOut" }}
                    className="overflow-hidden"
                    data-testid={`faq-answer-${i}`}
                  >
                    <div className="pb-8 pr-10 text-sm text-slate-400 leading-relaxed space-y-4">{item.a}</div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          ))}
        </div>

        <p className="text-xs text-slate-600 mt-8 leading-relaxed" data-testid="faq-disclaimer">
          Esta sección tiene carácter informativo y no constituye asesoría legal. Conoce más en nuestro{" "}
          <a href="/uso-ia" target="_blank" rel="noreferrer" className="text-slate-500 underline hover:text-[#0EA5E9] transition-colors">
            Aviso de Uso de IA
          </a>{" "}
          y nuestros{" "}
          <a href="/terminos" target="_blank" rel="noreferrer" className="text-slate-500 underline hover:text-[#0EA5E9] transition-colors">
            Términos y Condiciones
          </a>
          .
        </p>
      </div>
    </section>
  );
};
