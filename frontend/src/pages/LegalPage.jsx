import { Link, useLocation } from "react-router-dom";
import { ArrowLeft, Scale, ShieldCheck, BrainCircuit } from "lucide-react";
import { ThemeToggle } from "@/components/ThemeToggle";

const S = ({ n, title, children }) => (
  <section className="mt-10">
    <h2 className="font-heading font-bold text-lg text-[#0F172A]">
      {n}. {title}
    </h2>
    <div className="mt-3 space-y-3 text-sm text-slate-600 leading-relaxed">{children}</div>
  </section>
);

const UL = ({ items }) => (
  <ul className="list-disc ml-5 space-y-2">
    {items.map((it, i) => (
      <li key={i}>{it}</li>
    ))}
  </ul>
);

const LAST_UPDATE = "Junio de 2026";

const Terminos = () => (
  <>
    <S n={1} title="Identificación y objeto">
      <p>
        Los presentes Términos y Condiciones (en adelante, los "Términos") regulan el acceso y uso de la
        plataforma web <b>OnBuySolutions</b> (en adelante, la "Plataforma"), un servicio de software como
        servicio (SaaS) que permite realizar auditorías financieras de condominios y juntas de propietarios
        en el Perú, asistidas por Inteligencia Artificial. Al registrarte y usar la Plataforma aceptas
        íntegramente estos Términos, la Política de Privacidad y el Aviso de Transparencia Algorítmica.
      </p>
    </S>
    <S n={2} title="Naturaleza del servicio: proveedor tecnológico, no entidad financiera">
      <p>
        OnBuySolutions es exclusivamente un <b>proveedor de servicios tecnológicos (SaaS)</b>. La empresa:
      </p>
      <UL
        items={[
          "NO capta depósitos del público ni administra dinero, fondos o activos de terceros.",
          "NO es una empresa del sistema financiero ni del mercado de valores, por lo que NO se encuentra bajo supervisión de la Superintendencia de Banca, Seguros y AFP (SBS) ni de la Superintendencia del Mercado de Valores (SMV), ni requiere licencia de dichas entidades para operar.",
          "NO otorga créditos, no realiza scoring crediticio ni intermediación financiera de ningún tipo.",
        ]}
      />
    </S>
    <S n={3} title="Naturaleza de los informes generados">
      <p>
        Los informes de auditoría de la Plataforma son <b>generados mediante algoritmos automatizados de
        Inteligencia Artificial</b> (Google Gemini) a partir de los documentos que el propio usuario
        proporciona. En consecuencia:
      </p>
      <UL
        items={[
          "Los informes constituyen un análisis técnico referencial y NO reemplazan una auditoría oficial practicada por un auditor o contador público colegiado, ni constituyen asesoría legal, contable, tributaria o financiera.",
          "El usuario humano (la Junta de Propietarios, la administración o el cliente) debe mantener la SUPERVISIÓN FINAL del resultado ('human in the loop') y validar el contenido del informe antes de utilizarlo para tomar decisiones, formular denuncias formales o iniciar procedimientos legales.",
          "La exactitud del informe depende de la calidad, integridad y veracidad de los documentos proporcionados por el usuario.",
          "Todo informe se emite con la indicación expresa de haber sido generado mediante Inteligencia Artificial y con un código de verificación único.",
        ]}
      />
    </S>
    <S n={4} title="Registro de cuenta">
      <p>
        Para acceder al panel privado debes crear una cuenta con datos veraces y mantener la confidencialidad
        de tus credenciales. Eres responsable de toda actividad realizada desde tu cuenta. Debes ser mayor de
        18 años y contar con capacidad legal para contratar.
      </p>
    </S>
    <S n={5} title="Obligaciones y declaraciones del usuario">
      <p>Al subir documentos a la Plataforma, el usuario declara y garantiza que:</p>
      <UL
        items={[
          "Cuenta con la autorización formal de la Junta de Propietarios, de la administración del condominio o del titular de la información para tratar los documentos y los datos personales contenidos en ellos.",
          "Los documentos fueron obtenidos de manera lícita y son entregados de forma voluntaria.",
          "No subirá información obtenida mediante accesos no autorizados, vulneración de sistemas o cualquier medio ilícito.",
          "Utilizará los informes conforme a la ley y asumirá responsabilidad exclusiva por el uso que haga de ellos frente a terceros.",
        ]}
      />
    </S>
    <S n={6} title="Secreto bancario y entrega voluntaria de documentos">
      <p>
        La información sobre depósitos y estados de cuenta bancarios se encuentra protegida por el{" "}
        <b>secreto bancario</b> (artículo 2°, inciso 5 de la Constitución Política del Perú y Ley N° 26702).
        Por ello:
      </p>
      <UL
        items={[
          "OnBuySolutions NO extrae, ni extraerá, información bancaria directamente de bancas en línea ni mediante técnicas de raspado web (web scraping).",
          "Todos los documentos analizados son cargados voluntariamente por el usuario, quien declara contar con la autorización del titular de la cuenta (la Junta de Propietarios o el condominio).",
          "OnBuySolutions actúa únicamente como Encargado de Tratamiento de los datos contenidos en dichos documentos, por cuenta y encargo del usuario.",
        ]}
      />
    </S>
    <S n={7} title="Licencia de uso y propiedad intelectual">
      <p>
        OnBuySolutions te otorga una licencia limitada, no exclusiva e intransferible para usar la Plataforma.
        El software, el diseño, las marcas y la tecnología son de propiedad de OnBuySolutions. Los documentos
        que subes y los informes generados a partir de ellos te pertenecen; nos otorgas únicamente la licencia
        estrictamente necesaria para procesarlos y prestarte el servicio.
      </p>
    </S>
    <S n={8} title="Confidencialidad">
      <p>
        Los documentos financieros que subas a la Plataforma <b>jamás serán vendidos, compartidos con
        terceros ajenos al servicio, indexados públicamente ni utilizados para entrenar modelos de IA
        públicos</b>. El acceso a tus auditorías está restringido exclusivamente a tu cuenta.
      </p>
    </S>
    <S n={9} title="Protección de datos personales">
      <p>
        El tratamiento de datos personales se rige por nuestra{" "}
        <Link to="/privacidad" className="text-[#0284C7] font-semibold hover:underline">
          Política de Privacidad
        </Link>
        , elaborada conforme a la Ley N° 29733 — Ley de Protección de Datos Personales — y su Reglamento
        (D.S. N° 016-2024-JUS).
      </p>
    </S>
    <S n={10} title="Uso de Inteligencia Artificial">
      <p>
        El uso de sistemas de IA en la Plataforma se rige por nuestro{" "}
        <Link to="/uso-ia" className="text-[#0284C7] font-semibold hover:underline">
          Aviso de Transparencia Algorítmica
        </Link>
        , conforme a la Ley N° 31814 y su Reglamento (D.S. N° 115-2025-PCM).
      </p>
    </S>
    <S n={11} title="Limitación de responsabilidad">
      <UL
        items={[
          "OnBuySolutions no será responsable por decisiones, denuncias, acciones legales o de cualquier otra índole adoptadas por el usuario con base en los informes, sin la validación humana exigida en estos Términos.",
          "OnBuySolutions no garantiza que los informes estén libres de errores u omisiones, dado que se generan de forma automatizada a partir de la documentación proporcionada.",
          "En ningún caso la responsabilidad total de OnBuySolutions excederá el monto efectivamente pagado por el usuario por el servicio en los últimos 12 meses.",
          "OnBuySolutions no responde por la autenticidad de los documentos cargados por el usuario.",
        ]}
      />
    </S>
    <S n={12} title="Disponibilidad del servicio">
      <p>
        Procuramos una disponibilidad continua de la Plataforma; sin embargo, el servicio puede suspenderse
        temporalmente por mantenimiento, fallas técnicas o causas de fuerza mayor, sin que ello genere
        responsabilidad para OnBuySolutions.
      </p>
    </S>
    <S n={13} title="Modificaciones y terminación">
      <p>
        Podemos actualizar estos Términos publicando la nueva versión en la Plataforma. El uso posterior del
        servicio implica su aceptación. Puedes eliminar tu cuenta, tus auditorías y tus documentos en
        cualquier momento. Podemos suspender cuentas que infrinjan estos Términos o la ley.
      </p>
    </S>
    <S n={14} title="Ley aplicable, jurisdicción y reclamos">
      <p>
        Estos Términos se rigen por las leyes de la República del Perú. Toda controversia se somete a los
        jueces y tribunales de Lima, Perú. Conforme al Código de Protección y Defensa del Consumidor (Ley N°
        29571), el usuario consumidor puede presentar reclamos a través de nuestro canal de contacto o ante
        INDECOPI. Contacto: <b>legal@onbuysolutions.com</b>.
      </p>
    </S>
  </>
);

const Privacidad = () => (
  <>
    <S n={1} title="Responsable del tratamiento">
      <p>
        <b>OnBuySolutions</b> (en adelante, "nosotros") es responsable del tratamiento de los datos personales
        recopilados a través de la plataforma. Contacto para asuntos de privacidad:{" "}
        <b>privacidad@onbuysolutions.com</b>.
      </p>
    </S>
    <S n={2} title="Marco normativo">
      <p>Esta Política se elabora en cumplimiento de:</p>
      <UL
        items={[
          "Ley N° 29733 — Ley de Protección de Datos Personales.",
          "D.S. N° 016-2024-JUS — Reglamento vigente de la Ley N° 29733 (en vigor desde el 30 de marzo de 2025; derogó el anterior D.S. N° 003-2013-JUS).",
          "Lineamientos de la Autoridad Nacional de Protección de Datos Personales (ANPD) del Ministerio de Justicia y Derechos Humanos.",
        ]}
      />
    </S>
    <S n={3} title="Datos que recopilamos">
      <UL
        items={[
          "Datos de cuenta: nombre, correo electrónico y contraseña (almacenada de forma cifrada e irreversible mediante hash bcrypt).",
          "Datos de contacto: nombre, correo, teléfono y mensaje, cuando usas el formulario de contacto.",
          "Documentos cargados: facturas, estados de cuenta bancarios, recibos, actas y presupuestos, que pueden contener datos personales de terceros (nombres, DNI, números de cuenta, montos).",
          "Datos técnicos: registros de acceso y cookies estrictamente necesarias para la sesión (httpOnly).",
        ]}
      />
    </S>
    <S n={4} title="Roles: Responsable y Encargado de Tratamiento">
      <UL
        items={[
          "Respecto de tus datos de cuenta y contacto, OnBuySolutions actúa como RESPONSABLE del tratamiento.",
          "Respecto de los datos personales de terceros contenidos en los documentos que subes (vecinos, proveedores, propietarios), OnBuySolutions actúa como ENCARGADO DE TRATAMIENTO, por cuenta y bajo las instrucciones del usuario (la Junta de Propietarios o administración), quien declara contar con la legitimidad y autorización para dicho tratamiento.",
        ]}
      />
    </S>
    <S n={5} title="Finalidades del tratamiento">
      <UL
        items={[
          "Crear y gestionar tu cuenta y autenticarte en el panel privado.",
          "Procesar los documentos cargados para generar la auditoría y el informe final solicitados por ti.",
          "Atender tus consultas, reclamos y el ejercicio de tus derechos.",
          "Cumplir obligaciones legales aplicables.",
        ]}
      />
      <p>
        No utilizamos tus datos ni tus documentos para finalidades distintas, ni para publicidad de terceros.
      </p>
    </S>
    <S n={6} title="Consentimiento">
      <p>
        El tratamiento se sustenta en tu consentimiento <b>libre, previo, expreso, informado, inequívoco y
        demostrable</b>, otorgado al marcar la casilla de aceptación durante el registro. Conservamos la fecha
        y hora de dicha aceptación como evidencia, conforme al principio de responsabilidad proactiva del
        Reglamento.
      </p>
    </S>
    <S n={7} title="Banco de datos y registro ante la ANPD">
      <p>
        Los datos personales se almacenan en los bancos de datos de titularidad de OnBuySolutions
        ("Usuarios de la plataforma" y "Contactos"), cuya inscripción se gestiona ante el{" "}
        <b>Registro Nacional de Protección de Datos Personales de la ANPD</b>, conforme a la Ley N° 29733 y su
        Reglamento.
      </p>
    </S>
    <S n={8} title="Flujo transfronterizo y encargados">
      <p>
        Para generar la auditoría, los documentos se procesan mediante el modelo de Inteligencia Artificial{" "}
        <b>Google Gemini</b>, cuyos servidores pueden estar ubicados fuera del Perú. Esta transferencia se
        realiza únicamente para la prestación del servicio, bajo acuerdos que garantizan niveles adecuados de
        protección, y se declara como flujo transfronterizo conforme a la normativa. Nuestros proveedores de
        infraestructura actúan como encargados o subencargados y no pueden usar tus datos para fines propios.
      </p>
    </S>
    <S n={9} title="Conservación y eliminación">
      <UL
        items={[
          "Los documentos y auditorías se conservan mientras mantengas tu cuenta activa o hasta que los elimines desde el panel (eliminación inmediata de archivos y registros).",
          "Los datos de cuenta se conservan mientras exista la relación contractual y, luego, solo por los plazos exigidos por ley.",
          "Recomendamos descargar tus informes y eliminar las auditorías que ya no necesites (principio de minimización).",
        ]}
      />
    </S>
    <S n={10} title="Medidas de seguridad">
      <UL
        items={[
          "Cifrado de las comunicaciones en tránsito (HTTPS/TLS).",
          "Contraseñas almacenadas con hash bcrypt (irreversible).",
          "Sesiones mediante cookies httpOnly y tokens firmados, con bloqueo automático ante intentos reiterados de acceso fallido.",
          "Aislamiento estricto por usuario: solo tú puedes acceder a tus auditorías y documentos.",
          "Los documentos no se indexan públicamente ni se comparten entre cuentas.",
        ]}
      />
    </S>
    <S n={11} title="No comercialización ni entrenamiento de modelos">
      <p>
        Tus datos y documentos <b>no se venden, no se ceden con fines comerciales y no se utilizan para
        entrenar modelos de Inteligencia Artificial públicos</b>. El procesamiento por IA se limita a generar
        el informe que tú solicitas.
      </p>
    </S>
    <S n={12} title="Notificación de incidentes de seguridad">
      <p>
        Ante un incidente de seguridad que afecte datos personales (filtración, acceso no autorizado o
        pérdida), notificaremos a la <b>ANPD dentro de las 48 horas</b> de conocido el incidente y, cuando
        corresponda, a los titulares afectados, conforme al D.S. N° 016-2024-JUS.
      </p>
    </S>
    <S n={13} title="Derechos ARCO y portabilidad">
      <p>
        Puedes ejercer en cualquier momento tus derechos de <b>Acceso, Rectificación, Cancelación y
        Oposición (ARCO)</b>, así como el derecho a la <b>portabilidad</b> de tus datos, escribiendo a{" "}
        <b>privacidad@onbuysolutions.com</b> con el asunto "Derechos ARCO", adjuntando copia de tu documento de
        identidad. Responderemos dentro de los plazos legales. Si consideras que tu solicitud no fue atendida,
        puedes presentar un reclamo ante la ANPD (www.gob.pe/anpd).
      </p>
    </S>
    <S n={14} title="Menores de edad">
      <p>
        La Plataforma está dirigida a mayores de 18 años. No recopilamos deliberadamente datos de menores de
        edad.
      </p>
    </S>
    <S n={15} title="Cambios a esta política">
      <p>
        Cualquier modificación será publicada en esta página con su fecha de actualización. Los cambios
        sustanciales serán comunicados a través de la Plataforma.
      </p>
    </S>
  </>
);

const UsoIA = () => (
  <>
    <S n={1} title="Marco normativo">
      <p>
        Este Aviso se emite en cumplimiento de la <b>Ley N° 31814</b> — Ley que promueve el uso de la
        Inteligencia Artificial en favor del desarrollo económico y social del Perú — y su Reglamento,
        aprobado por <b>D.S. N° 115-2025-PCM</b>, cuya autoridad técnico-normativa es la Secretaría de
        Gobierno y Transformación Digital (SGTD) de la PCM.
      </p>
    </S>
    <S n={2} title="Clasificación de riesgo del sistema">
      <p>
        El sistema de auditoría de OnBuySolutions califica como un sistema de IA de{" "}
        <b>riesgo aceptable</b> bajo el D.S. N° 115-2025-PCM, dado que:
      </p>
      <UL
        items={[
          "No interviene en infraestructura crítica ni gestiona activos críticos.",
          "No realiza evaluación o puntaje crediticio (credit scoring) de personas.",
          "No emplea identificación biométrica ni vigilancia masiva.",
          "No adopta decisiones automatizadas con efectos jurídicos directos sobre personas: produce informes técnicos referenciales sujetos a validación humana.",
        ]}
      />
    </S>
    <S n={3} title="Cómo funciona el sistema">
      <UL
        items={[
          "El usuario carga voluntariamente documentos financieros del condominio (facturas, estados de cuenta, recibos, actas, presupuestos).",
          "El modelo de lenguaje Google Gemini analiza los documentos: extrae montos, cruza egresos con sustentos, identifica duplicados, inconsistencias y operaciones sin respaldo.",
          "El sistema genera un informe estructurado con hallazgos clasificados por severidad, recomendaciones y una opinión técnica referencial.",
          "Cada informe queda etiquetado de forma visible como 'generado mediante análisis de Inteligencia Artificial' e incluye un código de verificación único.",
        ]}
      />
    </S>
    <S n={4} title="Supervisión humana obligatoria (human in the loop)">
      <p>
        De forma explícita se informa que <b>los informes contables y de auditoría de esta plataforma son
        generados mediante algoritmos automatizados</b>. El usuario humano — la Junta de Propietarios, la
        administración del condominio o el cliente — <b>debe mantener la supervisión final</b> y:
      </p>
      <UL
        items={[
          "Revisar y validar el contenido del informe contrastándolo con la documentación original.",
          "Validar los hallazgos antes de realizar denuncias formales, iniciar procesos judiciales o adoptar medidas contra personas.",
          "Tener presente que conserva en todo momento la autoridad para corregir, descartar o invalidar los resultados del sistema.",
        ]}
      />
    </S>
    <S n={5} title="Limitaciones del sistema">
      <UL
        items={[
          "La IA puede incurrir en errores de lectura, interpretación u omisión, especialmente con documentos ilegibles, incompletos o de baja calidad.",
          "El informe refleja únicamente la documentación proporcionada; la ausencia de documentos limita el alcance del análisis.",
          "El sistema no verifica la autenticidad de los documentos frente a las entidades emisoras.",
        ]}
      />
    </S>
    <S n={6} title="Buenas prácticas y gobernanza">
      <UL
        items={[
          "Mantenemos políticas y procedimientos internos de seguridad, privacidad, transparencia y rendición de cuentas en el uso de la IA.",
          "Mantenemos registro documentado del funcionamiento del sistema, sus fuentes de datos y la lógica general del análisis.",
          "Los documentos de los usuarios no se emplean para entrenar modelos públicos.",
          "El tratamiento de datos personales asociado se rige por nuestra Política de Privacidad (Ley N° 29733 y D.S. N° 016-2024-JUS).",
        ]}
      />
    </S>
    <S n={7} title="Contacto">
      <p>
        Para consultas sobre el funcionamiento del sistema de IA: <b>legal@onbuysolutions.com</b>.
      </p>
    </S>
  </>
);

const DOCS = {
  "/terminos": {
    icon: Scale,
    label: "Documento legal",
    title: "Términos y Condiciones",
    subtitle:
      "Condiciones de uso de la plataforma OnBuySolutions de auditoría de condominios asistida por Inteligencia Artificial.",
    body: <Terminos />,
  },
  "/privacidad": {
    icon: ShieldCheck,
    label: "Protección de datos",
    title: "Política de Privacidad",
    subtitle:
      "Tratamiento de datos personales conforme a la Ley N° 29733 y su Reglamento (D.S. N° 016-2024-JUS).",
    body: <Privacidad />,
  },
  "/uso-ia": {
    icon: BrainCircuit,
    label: "Transparencia algorítmica",
    title: "Aviso de Uso de Inteligencia Artificial",
    subtitle:
      "Transparencia algorítmica y supervisión humana conforme a la Ley N° 31814 y su Reglamento (D.S. N° 115-2025-PCM).",
    body: <UsoIA />,
  },
};

export default function LegalPage() {
  const { pathname } = useLocation();
  const doc = DOCS[pathname] || DOCS["/terminos"];
  const Icon = doc.icon;

  return (
    <div className="themeable min-h-screen bg-[#F8FAFC]">
      <header className="bg-[#020617] text-white">
        <div className="max-w-4xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link to="/" onClick={() => window.scrollTo(0, 0)} className="font-heading font-black text-lg tracking-tight" data-testid="legal-logo-link">
            OnBuy<span className="text-[#0EA5E9]">Solutions</span>
          </Link>
          <nav className="flex items-center gap-5 text-xs text-slate-300">
            <Link to="/terminos" className={`hover:text-white transition-colors ${pathname === "/terminos" ? "text-white font-semibold" : ""}`} data-testid="legal-nav-terminos">Términos</Link>
            <Link to="/privacidad" className={`hover:text-white transition-colors ${pathname === "/privacidad" ? "text-white font-semibold" : ""}`} data-testid="legal-nav-privacidad">Privacidad</Link>
            <Link to="/uso-ia" className={`hover:text-white transition-colors ${pathname === "/uso-ia" ? "text-white font-semibold" : ""}`} data-testid="legal-nav-uso-ia">Uso de IA</Link>
            <ThemeToggle onDark />
          </nav>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-12" data-testid="legal-page-content">
        <Link to="/" className="inline-flex items-center gap-2 text-sm text-slate-500 hover:text-[#0284C7] transition-colors" data-testid="legal-back-link">
          <ArrowLeft size={16} /> Volver al inicio
        </Link>
        <div className="mt-8 bg-white border border-slate-200 p-8 lg:p-12">
          <div className="flex items-center gap-3">
            <Icon className="text-[#0284C7]" size={24} strokeWidth={1.5} />
            <p className="text-xs tracking-[0.25em] uppercase text-[#0284C7] font-semibold">{doc.label}</p>
          </div>
          <h1 className="font-heading font-black text-3xl sm:text-4xl tracking-tight text-[#0F172A] mt-4" data-testid="legal-title">
            {doc.title}
          </h1>
          <p className="text-slate-500 text-sm mt-3 leading-relaxed">{doc.subtitle}</p>
          <p className="text-xs text-slate-400 mt-2">Última actualización: {LAST_UPDATE}</p>
          <div className="mt-4 border-t border-slate-100" />
          {doc.body}
          <div className="mt-12 border-t border-slate-100 pt-6">
            <p className="text-xs text-slate-400 leading-relaxed">
              Este documento es una plantilla informativa elaborada para OnBuySolutions con base en la
              normativa peruana vigente. Se recomienda su revisión final por un abogado especializado en
              derecho tecnológico y protección de datos antes de su publicación definitiva.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
