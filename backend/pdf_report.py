import re
from io import BytesIO
from datetime import datetime, timezone

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors as rl_colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle

NAVY = rl_colors.HexColor("#0F172A")
SKY = rl_colors.HexColor("#0284C7")
GRAY = rl_colors.HexColor("#64748B")
LIGHT = rl_colors.HexColor("#F1F5F9")


def md_inline(text: str) -> str:
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<i>\1</i>", text)
    return text


def build_audit_pdf(audit: dict, doc_count: int) -> bytes:
    buf = BytesIO()

    styles = {
        "title": ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=22, textColor=NAVY, spaceAfter=6, leading=26),
        "subtitle": ParagraphStyle("subtitle", fontName="Helvetica", fontSize=11, textColor=GRAY, spaceAfter=4),
        "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=14, textColor=NAVY, spaceBefore=16, spaceAfter=8),
        "h3": ParagraphStyle("h3", fontName="Helvetica-Bold", fontSize=12, textColor=SKY, spaceBefore=12, spaceAfter=6),
        "body": ParagraphStyle("body", fontName="Helvetica", fontSize=9.5, textColor=rl_colors.HexColor("#1E293B"), alignment=TA_JUSTIFY, leading=14, spaceAfter=6),
        "bullet": ParagraphStyle("bullet", fontName="Helvetica", fontSize=9.5, textColor=rl_colors.HexColor("#1E293B"), leading=14, leftIndent=14, spaceAfter=4),
        "cell": ParagraphStyle("cell", fontName="Helvetica", fontSize=8, textColor=rl_colors.HexColor("#1E293B"), leading=11),
        "cellh": ParagraphStyle("cellh", fontName="Helvetica-Bold", fontSize=8, textColor=rl_colors.white, leading=11),
        "legal": ParagraphStyle("legal", fontName="Helvetica-Oblique", fontSize=8, textColor=GRAY, alignment=TA_JUSTIFY, leading=11),
        "center": ParagraphStyle("center", fontName="Helvetica", fontSize=10, textColor=GRAY, alignment=TA_CENTER),
    }

    def on_page(canvas, doc_):
        canvas.saveState()
        canvas.setStrokeColor(SKY)
        canvas.setLineWidth(2)
        canvas.line(2 * cm, A4[1] - 1.3 * cm, A4[0] - 2 * cm, A4[1] - 1.3 * cm)
        canvas.setFont("Helvetica-Bold", 8)
        canvas.setFillColor(NAVY)
        canvas.drawString(2 * cm, A4[1] - 1.1 * cm, "ONBUYSOLUTIONS")
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(GRAY)
        canvas.drawRightString(A4[0] - 2 * cm, A4[1] - 1.1 * cm, "Informe de Auditoría de Condominio")
        canvas.setFont("Helvetica", 7)
        canvas.drawCentredString(A4[0] / 2, 1 * cm, f"OnBuySolutions — Documento generado con análisis de IA | Página {doc_.page}")
        canvas.restoreState()

    pdf = SimpleDocTemplate(buf, pagesize=A4, topMargin=2.2 * cm, bottomMargin=2 * cm, leftMargin=2 * cm, rightMargin=2 * cm)
    story = []

    story.append(Spacer(1, 8))
    story.append(Paragraph("INFORME DE AUDITORÍA", styles["title"]))
    story.append(Paragraph("Auditoría financiera de condominio asistida por Inteligencia Artificial", styles["subtitle"]))
    story.append(HRFlowable(width="100%", thickness=1, color=SKY, spaceAfter=12))

    issue_date = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    info_data = [
        [Paragraph("<b>Condominio</b>", styles["cell"]), Paragraph(md_inline(audit["condominium_name"]), styles["cell"])],
        [Paragraph("<b>Dirección</b>", styles["cell"]), Paragraph(md_inline(f"{audit.get('address') or 'No especificada'} {('— ' + audit['district']) if audit.get('district') else ''}"), styles["cell"])],
        [Paragraph("<b>Período auditado</b>", styles["cell"]), Paragraph(md_inline(audit["period"]), styles["cell"])],
        [Paragraph("<b>Finalidad</b>", styles["cell"]), Paragraph(md_inline(audit.get("purpose") or "Uso general de la junta de propietarios"), styles["cell"])],
        [Paragraph("<b>Documentos analizados</b>", styles["cell"]), Paragraph(str(doc_count), styles["cell"])],
        [Paragraph("<b>Fecha de emisión</b>", styles["cell"]), Paragraph(issue_date, styles["cell"])],
        [Paragraph("<b>Código de verificación</b>", styles["cell"]), Paragraph(str(audit["_id"]), styles["cell"])],
    ]
    info_table = Table(info_data, colWidths=[4.5 * cm, 12.5 * cm])
    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), LIGHT),
        ("GRID", (0, 0), (-1, -1), 0.5, rl_colors.HexColor("#CBD5E1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 16))

    lines = (audit.get("analysis") or "").split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line.strip():
            i += 1
            continue
        if line.startswith("|"):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i].strip())
                i += 1
            rows = []
            for tl in table_lines:
                cells = [c.strip() for c in tl.strip("|").split("|")]
                if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                    continue
                rows.append(cells)
            if rows:
                ncols = max(len(r) for r in rows)
                data = []
                for ridx, r in enumerate(rows):
                    r = r + [""] * (ncols - len(r))
                    style = styles["cellh"] if ridx == 0 else styles["cell"]
                    data.append([Paragraph(md_inline(c), style) for c in r])
                col_w = 17.0 / ncols
                t = Table(data, colWidths=[col_w * cm] * ncols, repeatRows=1)
                t.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                    ("GRID", (0, 0), (-1, -1), 0.5, rl_colors.HexColor("#CBD5E1")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [rl_colors.white, LIGHT]),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]))
                story.append(t)
                story.append(Spacer(1, 8))
            continue
        stripped = line.strip()
        if stripped.startswith("### "):
            story.append(Paragraph(md_inline(stripped[4:]), styles["h3"]))
        elif stripped.startswith("## "):
            story.append(Paragraph(md_inline(stripped[3:]), styles["h2"]))
        elif stripped.startswith("# "):
            story.append(Paragraph(md_inline(stripped[2:]), styles["h2"]))
        elif re.match(r"^[-*]\s+", stripped):
            story.append(Paragraph("•&nbsp;&nbsp;" + md_inline(re.sub(r"^[-*]\s+", "", stripped)), styles["bullet"]))
        elif re.match(r"^\d+\.\s+", stripped):
            story.append(Paragraph(md_inline(stripped), styles["bullet"]))
        else:
            story.append(Paragraph(md_inline(stripped), styles["body"]))
        i += 1

    story.append(Spacer(1, 24))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY, spaceAfter=8))
    story.append(Paragraph(
        "Este informe ha sido elaborado por OnBuySolutions mediante un proceso de auditoría asistida por Inteligencia Artificial "
        "(Google Gemini) sobre la documentación proporcionada voluntariamente por el cliente. El análisis se realizó conforme al marco legal peruano "
        "aplicable a condominios y juntas de propietarios (Ley N° 27157 y su Reglamento, D.S. N° 035-2006-VIVIENDA). "
        "AVISO DE TRANSPARENCIA ALGORÍTMICA (Ley N° 31814 y D.S. N° 115-2025-PCM): el presente informe fue generado mediante algoritmos "
        "automatizados; el usuario humano (la Junta de Propietarios o administración) debe mantener la supervisión final y validar su contenido "
        "antes de utilizarlo para formular denuncias formales o iniciar procedimientos legales. No constituye una auditoría oficial practicada por "
        "auditor colegiado ni asesoría legal, contable o financiera. El tratamiento de los datos personales contenidos en la documentación se rige "
        "por la Ley N° 29733 y su Reglamento vigente, aprobado por D.S. N° 016-2024-JUS (en vigor desde el 30 de marzo de 2025, norma que derogó el anterior D.S. N° 003-2013-JUS), actuando OnBuySolutions como encargado de tratamiento. "
        "El presente documento puede ser utilizado por el cliente para los fines que estime pertinentes, recomendándose su validación complementaria "
        "por un auditor colegiado. Código de verificación: " + str(audit["_id"]) + ".",
        styles["legal"],
    ))

    pdf.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return buf.getvalue()
