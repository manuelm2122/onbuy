import re
from io import BytesIO
from datetime import datetime, timezone

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle

NAVY = colors.HexColor("#0F172A")
SKY = colors.HexColor("#0284C7")
GRAY = colors.HexColor("#64748B")
LIGHT = colors.HexColor("#F1F5F9")
DARK = colors.HexColor("#1E293B")

ST = {
    "title": ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=15, textColor=NAVY, alignment=TA_CENTER, spaceAfter=4, leading=19),
    "subtitle": ParagraphStyle("subtitle", fontName="Helvetica", fontSize=9, textColor=GRAY, alignment=TA_CENTER, spaceAfter=10),
    "clause": ParagraphStyle("clause", fontName="Helvetica-Bold", fontSize=10, textColor=NAVY, spaceBefore=12, spaceAfter=4),
    "body": ParagraphStyle("body", fontName="Helvetica", fontSize=9.5, textColor=DARK, alignment=TA_JUSTIFY, leading=14, spaceAfter=6),
    "bullet": ParagraphStyle("bullet", fontName="Helvetica", fontSize=9.5, textColor=DARK, alignment=TA_JUSTIFY, leading=14, leftIndent=14, spaceAfter=4),
    "cell": ParagraphStyle("cell", fontName="Helvetica", fontSize=8.5, textColor=DARK, leading=12),
    "cellh": ParagraphStyle("cellh", fontName="Helvetica-Bold", fontSize=8.5, textColor=colors.white, leading=12),
    "sign": ParagraphStyle("sign", fontName="Helvetica", fontSize=8.5, textColor=DARK, alignment=TA_CENTER, leading=12),
    "small": ParagraphStyle("small", fontName="Helvetica-Oblique", fontSize=7.5, textColor=GRAY, alignment=TA_JUSTIFY, leading=10),
    "big": ParagraphStyle("big", fontName="Helvetica-Bold", fontSize=13, textColor=NAVY, spaceAfter=6),
}

UNIDADES = ("", "UN", "DOS", "TRES", "CUATRO", "CINCO", "SEIS", "SIETE", "OCHO", "NUEVE")
DIECES = ("DIEZ", "ONCE", "DOCE", "TRECE", "CATORCE", "QUINCE", "DIECISEIS", "DIECISIETE", "DIECIOCHO", "DIECINUEVE")
DECENAS = ("", "", "VEINTE", "TREINTA", "CUARENTA", "CINCUENTA", "SESENTA", "SETENTA", "OCHENTA", "NOVENTA")
CENTENAS = ("", "CIENTO", "DOSCIENTOS", "TRESCIENTOS", "CUATROCIENTOS", "QUINIENTOS", "SEISCIENTOS", "SETECIENTOS", "OCHOCIENTOS", "NOVECIENTOS")


def _grupo(n: int) -> str:
    if n == 100:
        return "CIEN"
    out = ""
    c, u = n // 100, n % 10
    resto = n % 100
    if c:
        out += CENTENAS[c] + " "
    if 10 <= resto <= 19:
        out += DIECES[resto - 10]
    elif 21 <= resto <= 29:
        out += "VEINTI" + UNIDADES[u]
    elif resto >= 20:
        out += DECENAS[resto // 10]
        if u:
            out += " Y " + UNIDADES[u]
    else:
        out += UNIDADES[u]
    return out.strip()


def numero_a_letras(n: int) -> str:
    if n == 0:
        return "CERO"
    partes = []
    millones, miles, resto = n // 1_000_000, (n % 1_000_000) // 1000, n % 1000
    if millones:
        partes.append("UN MILLON" if millones == 1 else _grupo(millones) + " MILLONES")
    if miles:
        partes.append("MIL" if miles == 1 else _grupo(miles) + " MIL")
    if resto:
        partes.append(_grupo(resto))
    return " ".join(partes)


def monto_en_letras(amount: float) -> str:
    ent = int(amount)
    cent = int(round((amount - ent) * 100))
    return f"{numero_a_letras(ent)} CON {cent:02d}/100 SOLES"


def _esc(v: str) -> str:
    return str(v).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class F:
    def __init__(self, fields: dict):
        self.f = fields or {}

    def g(self, key: str, default: str = "") -> str:
        v = str(self.f.get(key) or "").strip()
        if v:
            return _esc(v)
        return _esc(default) if default else "__________________"

    def monto(self) -> float:
        try:
            return float(str(self.f.get("monto", "")).replace(",", "").replace("S/", "").strip())
        except (ValueError, TypeError):
            return 2100.0 if self.f.get("plan") == "mediano" else 1100.0


def _on_page(canvas, doc_):
    canvas.saveState()
    canvas.setStrokeColor(SKY)
    canvas.setLineWidth(2)
    canvas.line(2 * cm, A4[1] - 1.3 * cm, A4[0] - 2 * cm, A4[1] - 1.3 * cm)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.setFillColor(NAVY)
    canvas.drawString(2 * cm, A4[1] - 1.1 * cm, "ONBUYSOLUTIONS S.A.C.")
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(GRAY)
    canvas.drawRightString(A4[0] - 2 * cm, A4[1] - 1.1 * cm, "Auditoría de condominios asistida por IA · Perú")
    canvas.drawCentredString(A4[0] / 2, 1 * cm, f"OnBuySolutions S.A.C. | Página {doc_.page}")
    canvas.restoreState()


def _firmas(f: F, modo: str = "ambas"):
    linea = "_______________________________"
    empresa = [
        Paragraph(linea, ST["sign"]),
        Paragraph(f"<b>{f.g('empresa_representante')}</b>", ST["sign"]),
        Paragraph(f"DNI N° {f.g('empresa_dni')}", ST["sign"]),
        Paragraph(f.g("empresa_razon_social", "OnBuySolutions S.A.C."), ST["sign"]),
        Paragraph(f"RUC N° {f.g('empresa_ruc')}", ST["sign"]),
        Paragraph("LA EMPRESA", ST["sign"]),
    ]
    cliente = [
        Paragraph(linea, ST["sign"]),
        Paragraph(f"<b>{f.g('cliente_representante')}</b>", ST["sign"]),
        Paragraph(f"DNI N° {f.g('cliente_dni')}", ST["sign"]),
        Paragraph(f"{f.g('cliente_cargo', 'Representante')}", ST["sign"]),
        Paragraph(f.g("cliente_nombre"), ST["sign"]),
        Paragraph("EL CLIENTE", ST["sign"]),
    ]
    if modo == "empresa":
        data = [[empresa]]
        widths = [8 * cm]
    elif modo == "cliente":
        data = [[cliente]]
        widths = [8 * cm]
    else:
        data = [[empresa, cliente]]
        widths = [8.5 * cm, 8.5 * cm]
    t = Table(data, colWidths=widths)
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 6)]))
    return [Spacer(1, 48), t]


def _lugar_fecha(f: F):
    return Paragraph(f"{f.g('ciudad', 'Lima')}, {f.g('fecha')}", ST["body"])


def _partes_intro(f: F, tipo_doc: str) -> str:
    return (
        f"Conste por el presente documento el {tipo_doc} que celebran, de una parte, "
        f"<b>{f.g('empresa_razon_social', 'OnBuySolutions S.A.C.')}</b>, con RUC N° {f.g('empresa_ruc')}, con domicilio en "
        f"{f.g('empresa_direccion')}, debidamente representada por {f.g('empresa_representante')}, identificado(a) con "
        f"DNI N° {f.g('empresa_dni')}, a quien en adelante se denominará <b>«LA EMPRESA»</b>; y, de la otra parte, "
        f"<b>{f.g('cliente_nombre')}</b>, con RUC N° {f.g('cliente_ruc')}, con domicilio en {f.g('cliente_direccion')}, "
        f"{f.g('cliente_distrito')}, debidamente representada por {f.g('cliente_representante')}, identificado(a) con "
        f"DNI N° {f.g('cliente_dni')}, en su calidad de {f.g('cliente_cargo', 'Presidente de la Junta de Propietarios')}, "
        f"a quien en adelante se denominará <b>«EL CLIENTE»</b>; en los términos y condiciones siguientes:"
    )


def _plan_desc(f: F) -> str:
    if f.f.get("plan") == "mediano":
        return "Condominio mediano a grande (50 a 150 departamentos)"
    return "Condominio pequeño (menos de 50 departamentos)"


# ---------------- BUILDERS ----------------

def _doc_propuesta(f: F):
    m = f.monto()
    story = [
        _lugar_fecha(f),
        Spacer(1, 8),
        Paragraph(f"Señores<br/><b>{f.g('cliente_nombre')}</b><br/>Atención: {f.g('cliente_representante')} — {f.g('cliente_cargo', 'Presidente de la Junta de Propietarios')}<br/>{f.g('cliente_direccion')}, {f.g('cliente_distrito')}", ST["body"]),
        Paragraph("Referencia: Propuesta de servicio de auditoría de condominio asistida por Inteligencia Artificial", ST["clause"]),
        Paragraph(
            "De nuestra consideración: por medio de la presente, OnBuySolutions S.A.C. tiene el agrado de presentar su "
            "propuesta comercial para el servicio de auditoría financiera de su condominio, realizada mediante nuestra "
            "plataforma tecnológica con Inteligencia Artificial (Google Gemini), conforme al siguiente detalle:", ST["body"]),
        Paragraph("1. Alcance del servicio", ST["clause"]),
        Paragraph("• Procesamiento y análisis de hasta doce (12) meses de estados de cuenta bancarios, facturas, recibos de mantenimiento, actas y presupuestos del condominio, correspondientes al período " + f.g("periodo") + ".", ST["bullet"]),
        Paragraph("• Conciliación de egresos bancarios contra comprobantes de sustento; detección de pagos duplicados, montos inconsistentes, retiros sin sustento y posibles irregularidades.", ST["bullet"]),
        Paragraph("• Informe final profesional en PDF con ocho (8) secciones: resumen ejecutivo, alcance, documentos revisados, análisis financiero, hallazgos con severidad, posibles irregularidades, recomendaciones y opinión técnica, elaborado conforme al marco de la Ley N° 27157 y su Reglamento.", ST["bullet"]),
        Paragraph("• Código de verificación único por informe y aviso de transparencia algorítmica (Ley N° 31814 y D.S. N° 115-2025-PCM).", ST["bullet"]),
        Paragraph("2. Inversión", ST["clause"]),
    ]
    tabla = Table(
        [
            [Paragraph("Plan", ST["cellh"]), Paragraph("Descripción", ST["cellh"]), Paragraph("Precio por año auditado", ST["cellh"])],
            [Paragraph(_plan_desc(f), ST["cell"]), Paragraph(f"Auditoría de {f.g('num_departamentos')} departamentos — Período {f.g('periodo')}", ST["cell"]), Paragraph(f"<b>S/ {m:,.2f}</b>", ST["cell"])],
        ],
        colWidths=[6 * cm, 7.5 * cm, 3.5 * cm],
    )
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story += [
        tabla,
        Spacer(1, 6),
        Paragraph(f"Son: {monto_en_letras(m)}. Precio no incluye IGV salvo indicación en contrario.", ST["body"]),
        Paragraph("3. Condiciones comerciales", ST["clause"]),
        Paragraph("• Forma de pago: 50% a la aceptación de la propuesta y 50% contra entrega del informe final.", ST["bullet"]),
        Paragraph(f"• Plazo de entrega estimado: {f.g('plazo_entrega', '7 días hábiles')} contados desde la recepción completa de la documentación.", ST["bullet"]),
        Paragraph(f"• Validez de la oferta: {f.g('validez_dias', '15')} días calendario desde la fecha de emisión.", ST["bullet"]),
        Paragraph("• La prestación del servicio se formalizará mediante contrato, acuerdo de confidencialidad y acuerdo de encargo de tratamiento de datos personales.", ST["bullet"]),
        Paragraph(
            "Quedamos a su disposición para cualquier consulta. En señal de aceptación de la presente propuesta, se suscribe el presente documento.", ST["body"]),
    ]
    return "PROPUESTA COMERCIAL DE SERVICIOS", story, "ambas"


def _doc_contrato(f: F):
    m = f.monto()
    story = [
        Paragraph(_partes_intro(f, "CONTRATO DE PRESTACIÓN DE SERVICIOS TECNOLÓGICOS DE AUDITORÍA ASISTIDA POR INTELIGENCIA ARTIFICIAL"), ST["body"]),
        Paragraph("PRIMERA: ANTECEDENTES", ST["clause"]),
        Paragraph("LA EMPRESA es un proveedor de servicios tecnológicos (Software as a Service) que opera una plataforma de auditoría financiera de condominios asistida por Inteligencia Artificial. LA EMPRESA no es una entidad del sistema financiero, no capta depósitos del público ni administra fondos de terceros, y no se encuentra bajo supervisión de la SBS ni de la SMV. EL CLIENTE es una junta de propietarios / administración de condominio que requiere el análisis de su documentación financiera.", ST["body"]),
        Paragraph("SEGUNDA: OBJETO", ST["clause"]),
        Paragraph(f"Por el presente contrato, LA EMPRESA se obliga a prestar a EL CLIENTE el servicio de auditoría financiera asistida por IA del condominio ubicado en {f.g('cliente_direccion')}, {f.g('cliente_distrito')} ({_plan_desc(f)}, {f.g('num_departamentos')} departamentos), respecto del período {f.g('periodo')}, a cambio de la contraprestación pactada en la cláusula cuarta.", ST["body"]),
        Paragraph("TERCERA: ALCANCE DEL SERVICIO", ST["clause"]),
        Paragraph("El servicio comprende: (i) la recepción de los documentos financieros que EL CLIENTE cargue voluntariamente en la plataforma (estados de cuenta bancarios, facturas, recibos, actas y presupuestos); (ii) su análisis mediante algoritmos de Inteligencia Artificial; (iii) la emisión de un informe final en PDF con hallazgos clasificados por severidad, recomendaciones y opinión técnica referencial, con código de verificación único.", ST["body"]),
        Paragraph("CUARTA: CONTRAPRESTACIÓN Y FORMA DE PAGO", ST["clause"]),
        Paragraph(f"EL CLIENTE pagará a LA EMPRESA la suma única de S/ {m:,.2f} ({monto_en_letras(m)}) por año auditado, de la siguiente forma: 50% a la firma del presente contrato y 50% contra entrega del informe final. Los pagos se realizarán mediante {f.g('forma_pago', 'transferencia bancaria')}.", ST["body"]),
        Paragraph("QUINTA: NATURALEZA DEL SERVICIO Y SUPERVISIÓN HUMANA", ST["clause"]),
        Paragraph("Las partes declaran conocer que los informes son generados mediante algoritmos automatizados de Inteligencia Artificial (Ley N° 31814 y D.S. N° 115-2025-PCM), que constituyen un análisis técnico referencial y no reemplazan una auditoría oficial practicada por auditor o contador público colegiado. EL CLIENTE se obliga a mantener la supervisión humana final y a validar el contenido del informe antes de utilizarlo para formular denuncias, iniciar procedimientos legales o adoptar medidas contra terceros.", ST["body"]),
        Paragraph("SEXTA: OBLIGACIONES DE EL CLIENTE", ST["clause"]),
        Paragraph("(i) Entregar documentación veraz, completa y obtenida lícitamente; (ii) contar con la autorización de la junta de propietarios y del titular de las cuentas bancarias para la entrega voluntaria de la información, en observancia del secreto bancario; (iii) pagar la contraprestación pactada; (iv) usar el informe conforme a la ley y bajo su exclusiva responsabilidad.", ST["body"]),
        Paragraph("SÉPTIMA: OBLIGACIONES DE LA EMPRESA", ST["clause"]),
        Paragraph("(i) Prestar el servicio con diligencia y conforme al alcance pactado; (ii) guardar estricta confidencialidad sobre la documentación; (iii) no vender, ceder ni utilizar los documentos para entrenar modelos de IA públicos; (iv) entregar el informe final dentro del plazo estimado de " + f.g("plazo_entrega", "7 días hábiles") + " desde la recepción completa de la documentación.", ST["body"]),
        Paragraph("OCTAVA: CONFIDENCIALIDAD", ST["clause"]),
        Paragraph("Toda información intercambiada tiene carácter confidencial y se rige, adicionalmente, por el Acuerdo de Confidencialidad suscrito entre las partes, el cual forma parte integrante del presente contrato.", ST["body"]),
        Paragraph("NOVENA: PROTECCIÓN DE DATOS PERSONALES", ST["clause"]),
        Paragraph("El tratamiento de los datos personales contenidos en la documentación se rige por la Ley N° 29733 y su Reglamento (D.S. N° 016-2024-JUS). LA EMPRESA actúa como encargada de tratamiento por cuenta de EL CLIENTE, conforme al Acuerdo de Encargo de Tratamiento de Datos Personales suscrito entre las partes.", ST["body"]),
        Paragraph("DÉCIMA: PLAZO Y RESOLUCIÓN", ST["clause"]),
        Paragraph("El presente contrato rige desde su suscripción hasta la entrega del informe final y el pago total de la contraprestación. Cualquiera de las partes podrá resolverlo por incumplimiento de la otra, mediante comunicación escrita con quince (15) días calendario de anticipación.", ST["body"]),
        Paragraph("DÉCIMO PRIMERA: RESPONSABILIDAD", ST["clause"]),
        Paragraph("La responsabilidad total de LA EMPRESA frente a EL CLIENTE no excederá el monto efectivamente pagado por el servicio. LA EMPRESA no responde por la autenticidad de los documentos entregados por EL CLIENTE ni por decisiones adoptadas sin la validación humana prevista en la cláusula quinta.", ST["body"]),
        Paragraph("DÉCIMO SEGUNDA: LEY APLICABLE Y JURISDICCIÓN", ST["clause"]),
        Paragraph(f"El presente contrato se rige por las leyes de la República del Perú. Toda controversia se somete a la competencia de los jueces y tribunales de {f.g('ciudad', 'Lima')}. Suscrito en dos ejemplares de igual tenor, en {f.g('ciudad', 'Lima')}, el {f.g('fecha')}.", ST["body"]),
    ]
    return "CONTRATO DE PRESTACIÓN DE SERVICIOS", story, "ambas"


def _doc_confidencialidad(f: F):
    story = [
        Paragraph(_partes_intro(f, "ACUERDO DE CONFIDENCIALIDAD (NDA)"), ST["body"]),
        Paragraph("PRIMERA: OBJETO", ST["clause"]),
        Paragraph("Regular el tratamiento de la información confidencial que EL CLIENTE entregue a LA EMPRESA con ocasión del servicio de auditoría de condominio asistida por Inteligencia Artificial.", ST["body"]),
        Paragraph("SEGUNDA: INFORMACIÓN CONFIDENCIAL", ST["clause"]),
        Paragraph("Se considera información confidencial toda la documentación financiera, contable, bancaria y administrativa del condominio, incluyendo estados de cuenta, facturas, recibos, actas, presupuestos, listas de propietarios y cualquier dato personal contenido en ellos, así como los informes generados a partir de dicha información.", ST["body"]),
        Paragraph("TERCERA: OBLIGACIONES DE LA EMPRESA", ST["clause"]),
        Paragraph("(i) Utilizar la información exclusivamente para prestar el servicio contratado; (ii) no divulgarla, venderla, cederla ni compartirla con terceros ajenos al servicio; (iii) no indexarla públicamente; (iv) NO utilizarla para entrenar modelos de Inteligencia Artificial públicos o de terceros; (v) restringir el acceso al personal y sistemas estrictamente necesarios; (vi) aplicar medidas de seguridad técnicas y organizativas razonables.", ST["body"]),
        Paragraph("CUARTA: EXCLUSIONES", ST["clause"]),
        Paragraph("No constituye información confidencial aquella que: (i) sea de dominio público sin mediar incumplimiento; (ii) haya sido conocida lícitamente con anterioridad; (iii) deba ser revelada por mandato legal o de autoridad competente, en cuyo caso se notificará previamente a EL CLIENTE en la medida permitida por ley.", ST["body"]),
        Paragraph("QUINTA: PROPIEDAD DE LA INFORMACIÓN", ST["clause"]),
        Paragraph("La documentación entregada y los informes generados a partir de ella pertenecen a EL CLIENTE. LA EMPRESA conserva la titularidad de su plataforma, tecnología y metodología.", ST["body"]),
        Paragraph("SEXTA: VIGENCIA", ST["clause"]),
        Paragraph(f"Las obligaciones de confidencialidad rigen durante la prestación del servicio y se mantendrán vigentes por un plazo de {f.g('vigencia_anios', '5')} años posteriores a su culminación.", ST["body"]),
        Paragraph("SÉPTIMA: INCUMPLIMIENTO", ST["clause"]),
        Paragraph("El incumplimiento de este acuerdo faculta a la parte afectada a resolver el contrato de servicios y a exigir la indemnización por los daños y perjuicios efectivamente causados, conforme a la legislación peruana.", ST["body"]),
        Paragraph("OCTAVA: LEY APLICABLE", ST["clause"]),
        Paragraph(f"Este acuerdo se rige por las leyes de la República del Perú y se somete a los jueces y tribunales de {f.g('ciudad', 'Lima')}. Suscrito en {f.g('ciudad', 'Lima')}, el {f.g('fecha')}.", ST["body"]),
    ]
    return "ACUERDO DE CONFIDENCIALIDAD (NDA)", story, "ambas"


def _doc_tratamiento_datos(f: F):
    story = [
        Paragraph(_partes_intro(f, "ACUERDO DE ENCARGO DE TRATAMIENTO DE DATOS PERSONALES"), ST["body"]),
        Paragraph("PRIMERA: MARCO NORMATIVO Y ROLES", ST["clause"]),
        Paragraph("El presente acuerdo se celebra al amparo de la Ley N° 29733 — Ley de Protección de Datos Personales — y su Reglamento vigente, aprobado por D.S. N° 016-2024-JUS (en vigor desde el 30 de marzo de 2025, norma que derogó el anterior D.S. N° 003-2013-JUS). EL CLIENTE actúa como titular del banco de datos y responsable del tratamiento de los datos personales contenidos en su documentación (propietarios, proveedores y terceros). LA EMPRESA actúa como ENCARGADA DE TRATAMIENTO, por cuenta y bajo las instrucciones de EL CLIENTE.", ST["body"]),
        Paragraph("SEGUNDA: OBJETO Y FINALIDAD", ST["clause"]),
        Paragraph(f"LA EMPRESA tratará los datos personales contenidos en los documentos que EL CLIENTE cargue en la plataforma (nombres, DNI, números de cuenta, montos y demás datos incluidos en estados de cuenta, facturas, recibos y actas) con la única finalidad de generar la auditoría y el informe final del período {f.g('periodo')}. Queda prohibido cualquier tratamiento para finalidades distintas.", ST["body"]),
        Paragraph("TERCERA: DECLARACIONES DE EL CLIENTE", ST["clause"]),
        Paragraph("EL CLIENTE declara que cuenta con la legitimidad, base legal y/o consentimientos necesarios para el tratamiento de los datos personales entregados, que la información bancaria se entrega de manera voluntaria con autorización del titular de la cuenta (en observancia del secreto bancario), y que sus bancos de datos se encuentran conforme a la normativa aplicable.", ST["body"]),
        Paragraph("CUARTA: OBLIGACIONES DE LA EMPRESA (ENCARGADA)", ST["clause"]),
        Paragraph("(i) Tratar los datos solo conforme a este acuerdo y a las instrucciones de EL CLIENTE; (ii) guardar confidencialidad; (iii) aplicar medidas de seguridad técnicas y organizativas (cifrado en tránsito, control de acceso por usuario, contraseñas con hash irreversible); (iv) no vender ni ceder los datos, ni utilizarlos para entrenar modelos de IA públicos; (v) notificar a EL CLIENTE los incidentes de seguridad sin dilación indebida y colaborar con la notificación a la ANPD dentro de las 48 horas cuando corresponda; (vi) asistir a EL CLIENTE en la atención de los derechos ARCO de los titulares; (vii) suprimir o devolver los datos al término del servicio, según instrucción de EL CLIENTE.", ST["body"]),
        Paragraph("QUINTA: SUBENCARGADOS Y FLUJO TRANSFRONTERIZO", ST["clause"]),
        Paragraph("EL CLIENTE autoriza a LA EMPRESA a utilizar como subencargados a sus proveedores de infraestructura tecnológica y al proveedor del modelo de Inteligencia Artificial (Google — modelo Gemini), cuyos servidores pueden ubicarse fuera del Perú, exclusivamente para la prestación del servicio y bajo condiciones de protección adecuadas. Dicho flujo transfronterizo se declara conforme a la normativa vigente.", ST["body"]),
        Paragraph("SEXTA: CONSERVACIÓN Y SUPRESIÓN", ST["clause"]),
        Paragraph("Los documentos y datos se conservarán únicamente mientras el servicio esté activo o hasta que EL CLIENTE los elimine desde la plataforma. A la culminación del servicio, y a solicitud de EL CLIENTE, LA EMPRESA suprimirá de manera definitiva la documentación cargada.", ST["body"]),
        Paragraph("SÉPTIMA: RESPONSABILIDAD Y VIGENCIA", ST["clause"]),
        Paragraph(f"Cada parte responde por el incumplimiento de sus propias obligaciones conforme a la Ley N° 29733. Este acuerdo rige desde su suscripción y durante todo el tratamiento de los datos. Suscrito en {f.g('ciudad', 'Lima')}, el {f.g('fecha')}.", ST["body"]),
    ]
    return "ACUERDO DE ENCARGO DE TRATAMIENTO DE DATOS PERSONALES", story, "ambas"


def _doc_autorizacion_bancaria(f: F):
    story = [
        _lugar_fecha(f),
        Spacer(1, 8),
        Paragraph("Señores<br/><b>OnBuySolutions S.A.C.</b><br/>Presente.-", ST["body"]),
        Paragraph("Referencia: Autorización para la entrega voluntaria de información bancaria del condominio", ST["clause"]),
        Paragraph(
            f"Yo, <b>{f.g('cliente_representante')}</b>, identificado(a) con DNI N° {f.g('cliente_dni')}, en mi calidad de "
            f"{f.g('cliente_cargo', 'Presidente de la Junta de Propietarios')} de <b>{f.g('cliente_nombre')}</b>, con RUC N° {f.g('cliente_ruc')}, "
            f"con domicilio en {f.g('cliente_direccion')}, {f.g('cliente_distrito')}, declaro contar con las facultades suficientes y, en tal virtud:", ST["body"]),
        Paragraph("PRIMERO.- AUTORIZO expresamente la entrega voluntaria a OnBuySolutions S.A.C. de los estados de cuenta bancarios, comprobantes de pago (vouchers), facturas, recibos y demás documentación financiera del condominio correspondiente al período " + f.g("periodo") + ", con la única finalidad de que sean analizados mediante su plataforma de auditoría asistida por Inteligencia Artificial.", ST["body"]),
        Paragraph("SEGUNDO.- DECLARO que la información se entrega en ejercicio de la titularidad de las cuentas del condominio y de manera libre y voluntaria, por lo que dicha entrega no vulnera el secreto bancario reconocido en el artículo 2°, inciso 5 de la Constitución Política del Perú y en la Ley N° 26702, quedando OnBuySolutions S.A.C. expresamente prohibida de obtener información bancaria por medios distintos a los documentos entregados (incluyendo el raspado web o acceso a banca en línea).", ST["body"]),
        Paragraph("TERCERO.- DECLARO conocer que OnBuySolutions S.A.C. actuará como encargada de tratamiento de los datos personales contenidos en la documentación, conforme a la Ley N° 29733 y su Reglamento (D.S. N° 016-2024-JUS), y que los informes se generan mediante algoritmos automatizados de Inteligencia Artificial sujetos a validación humana final.", ST["body"]),
        Paragraph("CUARTO.- Esta autorización rige exclusivamente para el servicio contratado y podrá ser revocada por escrito en cualquier momento, sin efecto retroactivo sobre los tratamientos ya realizados.", ST["body"]),
        Paragraph("Se suscribe la presente en señal de conformidad.", ST["body"]),
    ]
    return "AUTORIZACIÓN DE ENTREGA DE INFORMACIÓN BANCARIA", story, "cliente"


def _doc_recibo(f: F):
    m = f.monto()
    story = [
        Spacer(1, 6),
        Paragraph(f"RECIBO DE PAGO N° {f.g('recibo_numero')}", ST["big"]),
        HRFlowable(width="100%", thickness=1, color=SKY, spaceAfter=12),
    ]
    data = [
        [Paragraph("<b>Recibí de</b>", ST["cell"]), Paragraph(f"{f.g('cliente_nombre')} — RUC N° {f.g('cliente_ruc')}", ST["cell"])],
        [Paragraph("<b>Representado por</b>", ST["cell"]), Paragraph(f"{f.g('cliente_representante')} — DNI N° {f.g('cliente_dni')}", ST["cell"])],
        [Paragraph("<b>La suma de</b>", ST["cell"]), Paragraph(f"<b>S/ {m:,.2f}</b> ({monto_en_letras(m)})", ST["cell"])],
        [Paragraph("<b>Por concepto de</b>", ST["cell"]), Paragraph(f"{f.g('concepto', 'Servicio de auditoría de condominio asistida por IA')} — Período: {f.g('periodo')}", ST["cell"])],
        [Paragraph("<b>Forma de pago</b>", ST["cell"]), Paragraph(f.g("forma_pago", "Transferencia bancaria"), ST["cell"])],
        [Paragraph("<b>Fecha de pago</b>", ST["cell"]), Paragraph(f.g("fecha_pago", f.g("fecha")), ST["cell"])],
        [Paragraph("<b>Lugar</b>", ST["cell"]), Paragraph(f.g("ciudad", "Lima"), ST["cell"])],
    ]
    t = Table(data, colWidths=[4.5 * cm, 12.5 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), LIGHT),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story += [
        t,
        Spacer(1, 10),
        Paragraph("Se emite el presente recibo en señal de conformidad y cancelación del monto indicado. Este documento no constituye comprobante de pago tributario; el comprobante correspondiente (boleta/factura electrónica) se emite conforme a la normativa de SUNAT.", ST["small"]),
    ]
    return "RECIBO DE PAGO", story, "ambas"


DOC_BUILDERS = {
    "propuesta": _doc_propuesta,
    "contrato": _doc_contrato,
    "confidencialidad": _doc_confidencialidad,
    "tratamiento_datos": _doc_tratamiento_datos,
    "autorizacion_bancaria": _doc_autorizacion_bancaria,
    "recibo": _doc_recibo,
}

ADMIN_DOC_TYPES = list(DOC_BUILDERS.keys())

FILENAMES = {
    "propuesta": "Propuesta_Comercial",
    "contrato": "Contrato_Servicios",
    "confidencialidad": "Acuerdo_Confidencialidad_NDA",
    "tratamiento_datos": "Acuerdo_Tratamiento_Datos",
    "autorizacion_bancaria": "Autorizacion_Informacion_Bancaria",
    "recibo": "Recibo_Pago",
}


def build_document(doc_type: str, fields: dict):
    f = F(fields)
    title, body, firmas_modo = DOC_BUILDERS[doc_type](f)
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=2.2 * cm, bottomMargin=2 * cm, leftMargin=2 * cm, rightMargin=2 * cm)
    story = [
        Spacer(1, 4),
        Paragraph(title, ST["title"]),
        Paragraph(f"Entre {fields.get('empresa_razon_social') or 'OnBuySolutions S.A.C.'} y {fields.get('cliente_nombre') or 'el Cliente'}", ST["subtitle"]),
        HRFlowable(width="100%", thickness=1, color=SKY, spaceAfter=12),
    ]
    story += body
    story += _firmas(f, firmas_modo)
    story += [
        Spacer(1, 20),
        Paragraph(
            "Documento generado por la plataforma OnBuySolutions el "
            + datetime.now(timezone.utc).strftime("%d/%m/%Y")
            + ". Plantilla elaborada con base en la normativa peruana vigente; se recomienda su revisión por asesoría legal antes de su suscripción.",
            ST["small"]),
    ]
    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    cliente = re.sub(r"[^\w\-]", "_", str(fields.get("cliente_nombre") or "Cliente"))[:30]
    filename = f"{FILENAMES[doc_type]}_{cliente}.pdf"
    return buf.getvalue(), filename
