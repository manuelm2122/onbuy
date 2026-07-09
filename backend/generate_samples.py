from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
import pandas as pd

NAVY = colors.HexColor("#0F172A")
GRAY = colors.HexColor("#64748B")
DARK = colors.HexColor("#1E293B")

st_title = ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=15, textColor=NAVY, spaceAfter=2)
st_sub = ParagraphStyle("s", fontName="Helvetica", fontSize=9, textColor=GRAY, spaceAfter=2)
st_h = ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=10.5, textColor=NAVY, spaceBefore=10, spaceAfter=4)
st_b = ParagraphStyle("b", fontName="Helvetica", fontSize=9, textColor=DARK, leading=13)


def _table(data, widths, header=True, align_right_cols=None):
    t = Table(data, colWidths=widths)
    style = [
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    if header:
        style += [
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]
    for c in align_right_cols or []:
        style.append(("ALIGN", (c, 0), (c, -1), "RIGHT"))
    t.setStyle(TableStyle(style))
    return t


def build_estado_cuenta(path: Path):
    doc = SimpleDocTemplate(str(path), pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm, leftMargin=2 * cm, rightMargin=2 * cm)
    story = [
        Paragraph("BANCO CONTINENTAL DEL PERÚ", st_title),
        Paragraph("ESTADO DE CUENTA CORRIENTE — Moneda: Soles (S/)", st_sub),
        HRFlowable(width="100%", thickness=1, color=NAVY, spaceAfter=10),
        Paragraph("<b>Titular:</b> Junta de Propietarios Condominio Los Álamos — RUC 20601234567", st_b),
        Paragraph("<b>N° de cuenta:</b> 0011-0345-0100234567 &nbsp;&nbsp; <b>Período:</b> 01/01/2025 al 31/01/2025", st_b),
        Spacer(1, 12),
    ]
    movs = [
        ["Fecha", "Descripción de la operación", "Cargo (S/)", "Abono (S/)", "Saldo (S/)"],
        ["01/01/2025", "SALDO INICIAL", "", "", "12,500.00"],
        ["02/01/2025", "Transferencias recibidas - Cuotas mantenimiento", "", "4,750.00", "17,250.00"],
        ["05/01/2025", "Pago proveedor: LIMPIA PERU S.A.C. - Fact. E001-1234", "1,850.00", "", "15,400.00"],
        ["08/01/2025", "Pago proveedor: ASCENSORES ANDINOS S.A.C. - Fact. E001-0456", "2,400.00", "", "13,000.00"],
        ["12/01/2025", "Pago proveedor: JARDINES DEL SUR E.I.R.L. - Fact. E001-0789", "950.00", "", "12,050.00"],
        ["15/01/2025", "RETIRO EN EFECTIVO - CAJERO ATM AV. LARCO", "3,000.00", "", "9,050.00"],
        ["19/01/2025", "Pago proveedor: JARDINES DEL SUR E.I.R.L. - Fact. E001-0789", "950.00", "", "8,100.00"],
        ["22/01/2025", "Transferencias recibidas - Cuotas mantenimiento", "", "2,500.00", "10,600.00"],
        ["28/01/2025", "Comisión mantenimiento de cuenta", "35.00", "", "10,565.00"],
        ["31/01/2025", "SALDO FINAL", "", "", "10,565.00"],
    ]
    story.append(_table(movs, [2.2 * cm, 8.3 * cm, 2.2 * cm, 2.2 * cm, 2.1 * cm], align_right_cols=[2, 3, 4]))
    story.append(Spacer(1, 14))
    story.append(Paragraph("Documento informativo emitido por el banco. Documento ficticio de ejemplo generado con IA para fines de demostración.", st_sub))
    doc.build(story)


def build_factura(path: Path, empresa: str, ruc: str, numero: str, fecha: str, items, nota: str = ""):
    total = sum(q * p for _, q, p in items)
    subtotal = total / 1.18
    igv = total - subtotal
    doc = SimpleDocTemplate(str(path), pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm, leftMargin=2 * cm, rightMargin=2 * cm)
    story = [
        Paragraph(empresa, st_title),
        Paragraph(f"RUC: {ruc} — FACTURA ELECTRÓNICA <b>{numero}</b>", st_sub),
        HRFlowable(width="100%", thickness=1, color=NAVY, spaceAfter=10),
        Paragraph(f"<b>Fecha de emisión:</b> {fecha}", st_b),
        Paragraph("<b>Cliente:</b> Junta de Propietarios Condominio Los Álamos", st_b),
        Paragraph("<b>RUC Cliente:</b> 20601234567 — Av. Los Álamos 456, Miraflores, Lima", st_b),
        Spacer(1, 12),
    ]
    rows = [["Descripción", "Cant.", "P. Unit. (S/)", "Importe (S/)"]]
    for desc, q, p in items:
        rows.append([desc, str(q), f"{p:,.2f}", f"{q * p:,.2f}"])
    story.append(_table(rows, [9.5 * cm, 1.7 * cm, 2.9 * cm, 2.9 * cm], align_right_cols=[1, 2, 3]))
    story.append(Spacer(1, 10))
    tot = [
        ["Op. Gravada (S/)", f"{subtotal:,.2f}"],
        ["IGV 18% (S/)", f"{igv:,.2f}"],
        ["IMPORTE TOTAL (S/)", f"{total:,.2f}"],
    ]
    t = _table(tot, [4.5 * cm, 3 * cm], header=False, align_right_cols=[1])
    t.setStyle(TableStyle([("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold")]))
    story.append(t)
    if nota:
        story.append(Spacer(1, 10))
        story.append(Paragraph(f"<b>Nota:</b> {nota}", st_b))
    story.append(Spacer(1, 14))
    story.append(Paragraph("Representación impresa de la factura electrónica. Documento ficticio de ejemplo generado con IA para fines de demostración.", st_sub))
    doc.build(story)


def build_recibos_csv(path: Path):
    rows = []
    owners = [
        "García Torres", "Rodríguez Paz", "Fernández Luna", "López Quispe", "Martínez Silva",
        "Sánchez Rojas", "Pérez Huamán", "Gómez Castro", "Díaz Flores", "Vargas Mendoza",
        "Torres Ríos", "Ramírez Salas", "Flores Vega", "Castro Núñez", "Ortiz Paredes",
        "Morales Chávez", "Gutiérrez León", "Chávez Campos", "Rojas Medina", "Mendoza Aguilar",
        "Aguilar Ponce", "Vega Espinoza", "Ríos Cárdenas", "Campos Delgado", "Silva Guerrero",
        "Paredes Soto", "Medina Bravo", "León Palacios", "Núñez Cornejo", "Espinoza Valdez",
    ]
    piso = 1
    for i, owner in enumerate(owners):
        dpto = f"{piso}0{(i % 3) + 1}"
        pagado = not (dpto == "704" and False) and i != 21
        rows.append({
            "Departamento": dpto,
            "Propietario": owner,
            "Concepto": "Cuota de mantenimiento Enero 2025",
            "Monto (S/)": 250.00,
            "Fecha de pago": f"{(i % 20) + 2:02d}/01/2025" if pagado else "",
            "Estado": "Pagado" if pagado else "Pendiente",
        })
        if (i + 1) % 3 == 0:
            piso += 1
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")


def build_presupuesto_xlsx(path: Path):
    egresos = pd.DataFrame([
        {"Categoría": "Limpieza y conserjería", "Proveedor": "Limpia Perú S.A.C.", "Mensual (S/)": 1850, "Anual (S/)": 22200},
        {"Categoría": "Mantenimiento de ascensores", "Proveedor": "Ascensores Andinos S.A.C.", "Mensual (S/)": 2200, "Anual (S/)": 26400},
        {"Categoría": "Jardinería y áreas verdes", "Proveedor": "Jardines del Sur E.I.R.L.", "Mensual (S/)": 950, "Anual (S/)": 11400},
        {"Categoría": "Vigilancia y seguridad", "Proveedor": "Segurimax S.A.C.", "Mensual (S/)": 1800, "Anual (S/)": 21600},
        {"Categoría": "Administración", "Proveedor": "Administradora Lima Sur", "Mensual (S/)": 450, "Anual (S/)": 5400},
        {"Categoría": "Fondo de reserva", "Proveedor": "-", "Mensual (S/)": 250, "Anual (S/)": 3000},
    ])
    ingresos = pd.DataFrame([
        {"Concepto": "Cuotas de mantenimiento (30 dptos. x S/ 250)", "Mensual (S/)": 7500, "Anual (S/)": 90000},
        {"Concepto": "Alquiler de azotea (antena)", "Mensual (S/)": 0, "Anual (S/)": 0},
    ])
    with pd.ExcelWriter(path, engine="openpyxl") as w:
        egresos.to_excel(w, sheet_name="Egresos 2025", index=False)
        ingresos.to_excel(w, sheet_name="Ingresos 2025", index=False)


def generate_all(out_dir: Path):
    out_dir.mkdir(exist_ok=True)
    build_estado_cuenta(out_dir / "estado_cuenta_enero_2025.pdf")
    build_factura(
        out_dir / "factura_limpieza_E001-1234.pdf",
        "LIMPIA PERÚ S.A.C.", "20512345678", "E001-1234", "04/01/2025",
        [("Servicio de limpieza integral de áreas comunes - Enero 2025", 1, 1850.00)],
    )
    build_factura(
        out_dir / "factura_ascensores_E001-0456.pdf",
        "ASCENSORES ANDINOS S.A.C.", "20487654321", "E001-0456", "07/01/2025",
        [("Mantenimiento preventivo de 2 ascensores - Enero 2025", 1, 2200.00)],
        nota="Incluye repuestos menores y mano de obra.",
    )
    build_factura(
        out_dir / "factura_jardineria_E001-0789.pdf",
        "JARDINES DEL SUR E.I.R.L.", "20456789123", "E001-0789", "11/01/2025",
        [("Mantenimiento de jardines y áreas verdes - Enero 2025", 1, 950.00)],
    )
    build_recibos_csv(out_dir / "recibos_mantenimiento_enero_2025.csv")
    build_presupuesto_xlsx(out_dir / "presupuesto_anual_2025.xlsx")


if __name__ == "__main__":
    generate_all(Path(__file__).parent / "sample_files")
    print("Sample files generated")
