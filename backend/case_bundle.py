from io import BytesIO
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageOps
from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

W, H = A4
NAVY = colors.HexColor("#0F172A")
SKY = colors.HexColor("#0284C7")
GRAY = colors.HexColor("#64748B")


def _esc(text: str) -> str:
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _annex_label(index: int) -> str:
    letters = ""
    n = index
    while True:
        letters = chr(65 + n % 26) + letters
        n = n // 26 - 1
        if n < 0:
            return f"Anexo 1-{letters}"


def _separator(label: str, filename: str, note: str = "") -> bytes:
    buf = BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=A4)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 30)
    c.drawCentredString(W / 2, H / 2 + 40, label.upper())
    c.setStrokeColor(SKY)
    c.setLineWidth(2)
    c.line(W / 2 - 3 * cm, H / 2 + 22, W / 2 + 3 * cm, H / 2 + 22)
    style = ParagraphStyle("sep", fontName="Helvetica", fontSize=12, textColor=NAVY, alignment=1, leading=16)
    p = Paragraph(_esc(filename), style)
    _, height = p.wrap(W - 6 * cm, 6 * cm)
    p.drawOn(c, 3 * cm, H / 2 - height)
    if note:
        n = Paragraph(_esc(note), ParagraphStyle("note", parent=style, fontSize=9.5, textColor=GRAY, leading=13))
        _, nh = n.wrap(W - 6 * cm, 6 * cm)
        n.drawOn(c, 3 * cm, H / 2 - height - nh - 24)
    c.save()
    return buf.getvalue()


def _image_pdf(path: Path) -> bytes:
    img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    img.thumbnail((2200, 2200))
    jpeg = BytesIO()
    img.save(jpeg, "JPEG", quality=85)
    jpeg.seek(0)
    margin = 1.5 * cm
    scale = min((W - 2 * margin) / img.width, (H - 2 * margin) / img.height)
    w, h = img.width * scale, img.height * scale
    buf = BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=A4)
    c.drawImage(ImageReader(jpeg), (W - w) / 2, (H - h) / 2, w, h)
    c.save()
    return buf.getvalue()


def _front(case_title: str, case_id: str, rows: list) -> bytes:
    buf = BytesIO()
    cell = ParagraphStyle("cell", fontName="Helvetica", fontSize=9, leading=12, textColor=NAVY)
    head = ParagraphStyle("head", parent=cell, fontName="Helvetica-Bold", textColor=colors.white)
    data = [[Paragraph(t, head) for t in ("Pieza", "Descripción", "Folios")]]
    data += [[Paragraph(_esc(a), cell), Paragraph(_esc(b), cell), Paragraph(_esc(c), cell)] for a, b, c in rows]
    table = Table(data, colWidths=[3 * cm, 11 * cm, 3 * cm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story = [
        Paragraph("EXPEDIENTE", ParagraphStyle("k", fontName="Helvetica-Bold", fontSize=9, textColor=SKY, spaceAfter=6)),
        Paragraph(_esc(case_title), ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=NAVY, spaceAfter=6)),
        Paragraph(
            f"Preparado el {datetime.now(timezone.utc).strftime('%d/%m/%Y')} — Referencia {case_id}",
            ParagraphStyle("s", fontName="Helvetica", fontSize=9.5, textColor=GRAY, spaceAfter=10),
        ),
        HRFlowable(width="100%", thickness=1, color=SKY, spaceAfter=16),
        Paragraph("Índice de piezas y anexos", ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=12, textColor=NAVY, spaceAfter=8)),
        table,
        Spacer(1, 14),
        Paragraph(
            "Los archivos que no pueden imprimirse (audio, video, hojas de cálculo) figuran en el índice con su carátula y se presentan en soporte digital.",
            ParagraphStyle("n", fontName="Helvetica-Oblique", fontSize=8, textColor=GRAY, leading=11),
        ),
    ]
    SimpleDocTemplate(buf, pagesize=A4, topMargin=2.2 * cm, bottomMargin=2 * cm, leftMargin=2 * cm, rightMargin=2 * cm).build(story)
    return buf.getvalue()


def _annex_pdf(label: str, filename: str, mime: str, path: Path) -> bytes:
    writer = PdfWriter()
    note, body = "", None
    try:
        if mime == "application/pdf":
            body = PdfReader(str(path))
            if body.is_encrypted:
                raise ValueError("pdf protegido")
            _ = len(body.pages)
        elif mime.startswith("image/"):
            body = PdfReader(BytesIO(_image_pdf(path)))
        else:
            note = "Archivo en formato digital: se presenta en soporte digital (USB o CD) junto con este expediente."
    except Exception:
        body, note = None, "No se pudo incorporar este archivo al PDF (protegido o dañado): preséntalo por separado."
    writer.append(PdfReader(BytesIO(_separator(label, filename, note))))
    if body:
        writer.append(body)
    out = BytesIO()
    writer.write(out)
    return out.getvalue()


def _foliate(pdf_bytes: bytes) -> bytes:
    reader = PdfReader(BytesIO(pdf_bytes))
    writer = PdfWriter()
    total = len(reader.pages)
    stamps_buf = BytesIO()
    c = rl_canvas.Canvas(stamps_buf)
    sizes = []
    for page in reader.pages:
        page.transfer_rotation_to_content()
        box = page.mediabox
        sizes.append((float(box.left), float(box.bottom), float(box.width), float(box.height)))
    for i, (left, bottom, w, h) in enumerate(sizes, start=1):
        c.setPageSize((w, h))
        text = f"Folio {i} de {total}"
        tw = c.stringWidth(text, "Helvetica-Bold", 8)
        c.setFillColor(colors.white)
        c.rect(w - tw - 28, 10, tw + 12, 14, stroke=0, fill=1)
        c.setFillColor(NAVY)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(w - tw - 22, 14, text)
        c.showPage()
    c.save()
    stamps = PdfReader(BytesIO(stamps_buf.getvalue()))
    for i, page in enumerate(reader.pages):
        left, bottom, _, _ = sizes[i]
        stamp = stamps.pages[i]
        if left or bottom:
            from pypdf import Transformation
            stamp.add_transformation(Transformation().translate(left, bottom))
        page.merge_page(stamp)
        writer.add_page(page)
    out = BytesIO()
    writer.write(out)
    return out.getvalue()


def build_bundle(case_title: str, case_id: str, sections: list, annexes: list) -> bytes:
    parts = [(label, title, pdf) for label, title, pdf in sections]
    for i, (filename, mime, path) in enumerate(annexes):
        label = _annex_label(i)
        parts.append((label, filename, _annex_pdf(label, filename, mime, path)))
    counts = [len(PdfReader(BytesIO(pdf)).pages) for _, _, pdf in parts]
    front_pages = len(PdfReader(BytesIO(_front(case_title, case_id, [(a, b, "000 - 000") for a, b, _ in parts]))).pages)
    rows, folio = [], front_pages + 1
    for (label, title, _), n in zip(parts, counts):
        rows.append((label, title, f"{folio}" if n == 1 else f"{folio} - {folio + n - 1}"))
        folio += n
    writer = PdfWriter()
    writer.append(PdfReader(BytesIO(_front(case_title, case_id, rows))))
    for _, _, pdf in parts:
        writer.append(PdfReader(BytesIO(pdf)))
    merged = BytesIO()
    writer.write(merged)
    return _foliate(merged.getvalue())
