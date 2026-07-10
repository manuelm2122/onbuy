import re
from io import BytesIO
from datetime import datetime, timezone, timedelta

from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors as rl_colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle

from core import db, logger, get_app_settings
from models import ComplaintInput, ComplaintStatusInput
from security import get_current_user, require_admin
from email_service import send_email

router = APIRouter()

PROVIDER = {
    "razon_social": "ONBUYSOLUTIONS S.A.C.",
    "ruc": "20606439327",
    "direccion": "Parque Rospigliosi 153, Pueblo Libre, Lima, Perú",
    "marca": "OnBuySolutions",
    "web": "www.onbuysolutions.com",
}

DOC_TYPES = {"DNI", "CE", "RUC", "Pasaporte"}
ITEM_TYPES = {"Producto", "Servicio"}
REQUEST_TYPES = {"Reclamo", "Queja"}

LEGAL_NOTE = (
    "La formulación del reclamo no impide acudir a otras vías de solución de controversias "
    "ni es requisito previo para interponer una denuncia ante el INDECOPI. El proveedor deberá dar "
    "respuesta al reclamo en un plazo no mayor a quince (15) días hábiles improrrogables "
    "(Art. 24 de la Ley N° 29571, modificado por la Ley N° 31435)."
)

NAVY = rl_colors.HexColor("#0F172A")
SKY = rl_colors.HexColor("#0284C7")
GRAY = rl_colors.HexColor("#64748B")
LIGHT = rl_colors.HexColor("#F1F5F9")

PERU_TZ = timezone(timedelta(hours=-5))


def add_business_days(start: datetime, days: int) -> datetime:
    current = start
    added = 0
    while added < days:
        current += timedelta(days=1)
        if current.weekday() < 5:
            added += 1
    return current


def _esc(text) -> str:
    return str(text or "—").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_complaint_pdf(c: dict) -> bytes:
    buf = BytesIO()
    styles = {
        "title": ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=16, textColor=NAVY, spaceAfter=2, leading=20, alignment=TA_CENTER),
        "subtitle": ParagraphStyle("subtitle", fontName="Helvetica", fontSize=9, textColor=GRAY, spaceAfter=4, alignment=TA_CENTER),
        "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=10.5, textColor=rl_colors.white, leading=14),
        "cell_label": ParagraphStyle("cell_label", fontName="Helvetica-Bold", fontSize=8.5, textColor=NAVY, leading=12),
        "cell": ParagraphStyle("cell", fontName="Helvetica", fontSize=8.5, textColor=rl_colors.HexColor("#1E293B"), leading=12),
        "legal": ParagraphStyle("legal", fontName="Helvetica-Oblique", fontSize=7.5, textColor=GRAY, alignment=TA_JUSTIFY, leading=10),
        "body": ParagraphStyle("body", fontName="Helvetica", fontSize=8.5, textColor=rl_colors.HexColor("#1E293B"), alignment=TA_JUSTIFY, leading=12),
    }

    def on_page(canvas, doc_):
        canvas.saveState()
        canvas.setStrokeColor(SKY)
        canvas.setLineWidth(2)
        canvas.line(1.8 * cm, A4[1] - 1.2 * cm, A4[0] - 1.8 * cm, A4[1] - 1.2 * cm)
        canvas.setFont("Helvetica-Bold", 8)
        canvas.setFillColor(NAVY)
        canvas.drawString(1.8 * cm, A4[1] - 1 * cm, "ONBUYSOLUTIONS")
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(GRAY)
        canvas.drawRightString(A4[0] - 1.8 * cm, A4[1] - 1 * cm, "Libro de Reclamaciones Virtual")
        canvas.drawCentredString(A4[0] / 2, 0.9 * cm, f"Constancia emitida electrónicamente — {PROVIDER['web']} | Página {doc_.page}")
        canvas.restoreState()

    pdf = SimpleDocTemplate(buf, pagesize=A4, topMargin=1.9 * cm, bottomMargin=1.7 * cm, leftMargin=1.8 * cm, rightMargin=1.8 * cm)
    W = 17.4

    def section_header(text):
        t = Table([[Paragraph(text, styles["h2"])]], colWidths=[W * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), NAVY),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        return t

    def kv_table(rows, col1=4.8):
        data = [[Paragraph(k, styles["cell_label"]), Paragraph(_esc(v), styles["cell"])] for k, v in rows]
        t = Table(data, colWidths=[col1 * cm, (W - col1) * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), LIGHT),
            ("GRID", (0, 0), (-1, -1), 0.5, rl_colors.HexColor("#CBD5E1")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        return t

    created = datetime.fromisoformat(c["created_at"]).astimezone(PERU_TZ)
    story = [
        Paragraph("HOJA DE RECLAMACIÓN", styles["title"]),
        Paragraph("LIBRO DE RECLAMACIONES VIRTUAL — D.S. N° 011-2011-PCM y modificatorias", styles["subtitle"]),
        HRFlowable(width="100%", thickness=1, color=SKY, spaceAfter=8),
        kv_table([
            ("Razón Social del Proveedor", PROVIDER["razon_social"]),
            ("RUC", PROVIDER["ruc"]),
            ("Dirección del Establecimiento", PROVIDER["direccion"]),
            ("Plataforma / Marca Comercial", f"{PROVIDER['marca']} — {PROVIDER['web']}"),
            ("Número de Reclamo (Hoja)", c["code"]),
            ("Fecha y Hora de Recepción", created.strftime("%d/%m/%Y %H:%M:%S") + " (hora de Perú)"),
        ]),
        Spacer(1, 10),
        section_header("1. IDENTIFICACIÓN DEL CONSUMIDOR RECLAMANTE"),
        kv_table([
            ("Nombres y Apellidos / Razón Social", c["consumer_name"]),
            ("Tipo de Documento", c["doc_type"]),
            ("Número de Documento", c["doc_number"]),
            ("Domicilio", c["address"]),
            ("Teléfono / Celular", c["phone"]),
            ("Correo Electrónico", c["email"]),
        ]),
        Spacer(1, 10),
        section_header("2. IDENTIFICACIÓN DEL BIEN CONTRATADO"),
        kv_table([
            ("Tipo", c["item_type"]),
            ("Monto Reclamado", f"S/ {c['amount']:,.2f}" if c.get("amount") else "No precisado"),
            ("Descripción", c["service_description"]),
        ]),
        Spacer(1, 10),
        section_header("3. DETALLE DE LA RECLAMACIÓN Y PEDIDO DEL CONSUMIDOR"),
        kv_table([
            ("Tipo de Solicitud", c["request_type"] + (" (disconformidad relacionada a los productos o servicios)" if c["request_type"] == "Reclamo" else " (malestar o descontento respecto a la atención al público)")),
            ("Detalle", c["detail"]),
            ("Pedido del Consumidor", c["consumer_request"]),
        ]),
        Spacer(1, 10),
        section_header("4. DECLARACIÓN DEL CONSUMIDOR"),
        kv_table([
            ("Declaración", "El consumidor declaró que los datos consignados son correctos y se ajustan a la verdad, y aceptó la Política de Privacidad para el tratamiento de sus datos personales en la gestión de esta solicitud (mecanismo electrónico que sustituye a la firma, conforme al reglamento del Libro de Reclamaciones)."),
            ("Constancia de Recepción", f"Registrado electrónicamente el {created.strftime('%d/%m/%Y a las %H:%M:%S')} (hora de Perú). Plazo máximo de respuesta: {c['due_date_display']}."),
        ]),
        Spacer(1, 12),
        HRFlowable(width="100%", thickness=0.5, color=GRAY, spaceAfter=6),
        Paragraph(LEGAL_NOTE, styles["legal"]),
        Spacer(1, 4),
        Paragraph(
            "Tratamiento de datos personales conforme a la Ley N° 29733 y su Reglamento (D.S. N° 016-2024-JUS). "
            f"Esta hoja de reclamación es conservada por {PROVIDER['razon_social']} por un período mínimo de dos (2) años. "
            f"Código de verificación: {c['id']}.",
            styles["legal"],
        ),
    ]
    pdf.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return buf.getvalue()


def _consumer_email_html(c: dict, created_display: str) -> str:
    return f"""
<table width="100%" cellpadding="0" cellspacing="0" style="font-family: Arial, sans-serif; background:#F1F5F9; padding:24px 0;">
  <tr><td align="center">
    <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff; border:1px solid #E2E8F0;">
      <tr><td style="background:#0F172A; padding:20px 28px;">
        <span style="color:#ffffff; font-size:18px; font-weight:bold;">OnBuy<span style="color:#0EA5E9;">Solutions</span></span>
        <span style="color:#94A3B8; font-size:11px; float:right; padding-top:6px;">Libro de Reclamaciones Virtual</span>
      </td></tr>
      <tr><td style="padding:28px;">
        <h2 style="color:#0F172A; font-size:17px; margin:0 0 12px;">Constancia de registro de su {c['request_type'].lower()}</h2>
        <p style="color:#334155; font-size:13px; line-height:1.6; margin:0 0 16px;">
          Estimado(a) <b>{c['consumer_name']}</b>:<br><br>
          Hemos recibido su {c['request_type'].lower()} a través del Libro de Reclamaciones Virtual de
          <b>{PROVIDER['razon_social']}</b> (plataforma <b>{PROVIDER['marca']} — {PROVIDER['web']}</b>).
          Adjuntamos la copia de su Hoja de Reclamación en PDF como constancia.
        </p>
        <table width="100%" cellpadding="8" cellspacing="0" style="border:1px solid #E2E8F0; font-size:13px; color:#334155;">
          <tr style="background:#F8FAFC;"><td width="45%"><b>Número de Reclamo</b></td><td>{c['code']}</td></tr>
          <tr><td><b>Fecha y hora de recepción</b></td><td>{created_display} (hora de Perú)</td></tr>
          <tr style="background:#F8FAFC;"><td><b>Tipo de solicitud</b></td><td>{c['request_type']}</td></tr>
          <tr><td><b>Plazo máximo de respuesta</b></td><td>{c['due_date_display']} (15 días hábiles improrrogables)</td></tr>
        </table>
        <p style="color:#64748B; font-size:11px; line-height:1.6; margin:16px 0 0;">
          {LEGAL_NOTE}
        </p>
      </td></tr>
      <tr><td style="background:#F8FAFC; border-top:1px solid #E2E8F0; padding:16px 28px;">
        <p style="color:#94A3B8; font-size:10px; margin:0; line-height:1.5;">
          {PROVIDER['razon_social']} — RUC {PROVIDER['ruc']} — {PROVIDER['direccion']}.<br>
          Este es un mensaje automático generado desde {PROVIDER['web']}; por favor no responda a este correo.
        </p>
      </td></tr>
    </table>
  </td></tr>
</table>"""


def _admin_email_html(c: dict, created_display: str) -> str:
    return f"""
<table width="100%" cellpadding="0" cellspacing="0" style="font-family: Arial, sans-serif;">
  <tr><td>
    <h2 style="color:#0F172A; font-size:16px;">Nuevo {c['request_type'].lower()} en el Libro de Reclamaciones</h2>
    <p style="font-size:13px; color:#334155;"><b>Sitio web: {PROVIDER['marca']} ({PROVIDER['web']})</b></p>
    <table width="100%" cellpadding="8" cellspacing="0" style="border:1px solid #E2E8F0; font-size:13px; color:#334155; max-width:600px;">
      <tr style="background:#F8FAFC;"><td width="40%"><b>Número</b></td><td>{c['code']}</td></tr>
      <tr><td><b>Fecha</b></td><td>{created_display}</td></tr>
      <tr style="background:#F8FAFC;"><td><b>Consumidor</b></td><td>{c['consumer_name']} ({c['doc_type']} {c['doc_number']})</td></tr>
      <tr><td><b>Contacto</b></td><td>{c['email']} / {c['phone']}</td></tr>
      <tr style="background:#F8FAFC;"><td><b>Tipo</b></td><td>{c['request_type']}</td></tr>
      <tr><td><b>Monto reclamado</b></td><td>{f"S/ {c['amount']:,.2f}" if c.get('amount') else 'No precisado'}</td></tr>
      <tr style="background:#F8FAFC;"><td><b>Detalle</b></td><td>{c['detail']}</td></tr>
      <tr><td><b>Pedido</b></td><td>{c['consumer_request']}</td></tr>
      <tr style="background:#FEF2F2;"><td><b>Plazo legal de respuesta</b></td><td><b style="color:#DC2626;">{c['due_date_display']}</b> (15 días hábiles improrrogables)</td></tr>
    </table>
    <p style="font-size:12px; color:#64748B;">Gestiona este reclamo desde el panel de administración → pestaña Reclamos.</p>
  </td></tr>
</table>"""


async def _send_complaint_emails(c: dict):
    created_display = datetime.fromisoformat(c["created_at"]).astimezone(PERU_TZ).strftime("%d/%m/%Y %H:%M:%S")
    pdf_bytes = build_complaint_pdf(c)
    consumer_result = await send_email(
        to=c["email"],
        subject=f"Constancia de {c['request_type']} {c['code']} — {PROVIDER['marca']} ({PROVIDER['web']})",
        html=_consumer_email_html(c, created_display),
        pdf_bytes=pdf_bytes,
        pdf_filename=f"Hoja_Reclamacion_{c['code']}.pdf",
    )
    cfg = await get_app_settings()
    admin_result = await send_email(
        to=cfg["complaints_notify_email"],
        subject=f"[{PROVIDER['web']}] Nuevo {c['request_type']}: {c['code']} — {c['consumer_name']}",
        html=_admin_email_html(c, created_display),
        pdf_bytes=pdf_bytes,
        pdf_filename=f"Hoja_Reclamacion_{c['code']}.pdf",
    )
    await db.complaints.update_one(
        {"_id": ObjectId(c["id"])},
        {"$set": {"consumer_email_status": consumer_result, "admin_email_status": admin_result}},
    )


def _serialize(d: dict) -> dict:
    return {
        "id": str(d["_id"]),
        "code": d["code"],
        "website": d.get("website", PROVIDER["web"]),
        "consumer_name": d["consumer_name"],
        "doc_type": d["doc_type"],
        "doc_number": d["doc_number"],
        "address": d["address"],
        "phone": d["phone"],
        "email": d["email"],
        "item_type": d["item_type"],
        "amount": d.get("amount"),
        "service_description": d["service_description"],
        "request_type": d["request_type"],
        "detail": d["detail"],
        "consumer_request": d["consumer_request"],
        "status": d.get("status", "pendiente"),
        "response_note": d.get("response_note"),
        "responded_at": d.get("responded_at"),
        "due_date": d["due_date"],
        "due_date_display": d["due_date_display"],
        "created_at": d["created_at"],
        "consumer_email_status": d.get("consumer_email_status"),
        "admin_email_status": d.get("admin_email_status"),
    }


@router.post("/complaints")
async def create_complaint(data: ComplaintInput, background_tasks: BackgroundTasks):
    if not data.accepted_declaration:
        raise HTTPException(status_code=400, detail="Debes aceptar la declaración para registrar tu solicitud")
    if data.doc_type not in DOC_TYPES:
        raise HTTPException(status_code=400, detail="Tipo de documento inválido")
    if data.item_type not in ITEM_TYPES:
        raise HTTPException(status_code=400, detail="Tipo de bien inválido")
    if data.request_type not in REQUEST_TYPES:
        raise HTTPException(status_code=400, detail="Tipo de solicitud inválido")

    counter = await db.counters.find_one_and_update(
        {"_id": "complaints"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,
    )
    seq = counter["seq"] if counter else 1
    now = datetime.now(timezone.utc)
    year = now.astimezone(PERU_TZ).year
    code = f"LRV-{year}-{seq:05d}"
    due = add_business_days(now.astimezone(PERU_TZ), 15)

    doc = data.model_dump()
    doc.update({
        "code": code,
        "website": PROVIDER["web"],
        "status": "pendiente",
        "created_at": now.isoformat(),
        "due_date": due.isoformat(),
        "due_date_display": due.strftime("%d/%m/%Y"),
    })
    doc.pop("accepted_declaration", None)
    doc["declaration_accepted_at"] = now.isoformat()
    result = await db.complaints.insert_one(doc)
    complaint = _serialize(await db.complaints.find_one({"_id": result.inserted_id}))
    background_tasks.add_task(_send_complaint_emails, complaint)
    logger.info(f"Reclamo registrado: {code}")
    return {
        "id": complaint["id"],
        "code": code,
        "created_at": complaint["created_at"],
        "due_date_display": complaint["due_date_display"],
        "message": "Tu solicitud fue registrada. Te enviamos una copia a tu correo electrónico.",
    }


@router.get("/complaints/{complaint_id}/receipt")
async def download_complaint_receipt(complaint_id: str):
    try:
        doc = await db.complaints.find_one({"_id": ObjectId(complaint_id)})
    except Exception:
        doc = None
    if not doc:
        raise HTTPException(status_code=404, detail="Reclamo no encontrado")
    pdf_bytes = build_complaint_pdf(_serialize(doc))
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="Hoja_Reclamacion_{doc["code"]}.pdf"'},
    )


@router.get("/admin/complaints")
async def admin_list_complaints(user: dict = Depends(get_current_user)):
    require_admin(user)
    docs = await db.complaints.find({}).sort("created_at", -1).to_list(2000)
    return [_serialize(d) for d in docs]


@router.put("/admin/complaints/{complaint_id}/status")
async def admin_update_complaint(complaint_id: str, data: ComplaintStatusInput, user: dict = Depends(get_current_user)):
    require_admin(user)
    if data.status not in ("pendiente", "respondido"):
        raise HTTPException(status_code=400, detail="Estado inválido")
    updates = {"status": data.status}
    if data.status == "respondido":
        updates["responded_at"] = datetime.now(timezone.utc).isoformat()
        if data.response_note:
            updates["response_note"] = data.response_note.strip()
    else:
        updates["responded_at"] = None
    result = await db.complaints.update_one({"_id": ObjectId(complaint_id)}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Reclamo no encontrado")
    return {"message": "Reclamo marcado como respondido" if data.status == "respondido" else "Reclamo marcado como pendiente"}
