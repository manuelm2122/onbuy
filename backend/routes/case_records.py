import os
import re
import csv
import uuid
import zipfile
import asyncio
import tempfile
import unicodedata
from io import BytesIO, StringIO
from pathlib import Path
from datetime import datetime, timezone, date
from typing import Optional, List

from bson import ObjectId
from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask

from core import db, UPLOAD_DIR
from security import get_current_user
from consulting import CASE_EXT_MIME, MAX_CASE_FILE_SIZE, DOC_BLOCK_RE, _consulting_pdf
from routes.case_tools import _get_case, _require_enabled, _valid_date
from case_bundle import build_bundle

router = APIRouter(prefix="/cases")
cases_dir = UPLOAD_DIR / "cases"

FILE_KEYS = ("filename", "stored_name", "mime_type", "size")
ORDINALS = [
    "PRIMERO", "SEGUNDO", "TERCERO", "CUARTO", "QUINTO", "SEXTO", "SÉPTIMO", "OCTAVO", "NOVENO", "DÉCIMO",
    "DÉCIMO PRIMERO", "DÉCIMO SEGUNDO", "DÉCIMO TERCERO", "DÉCIMO CUARTO", "DÉCIMO QUINTO",
    "DÉCIMO SEXTO", "DÉCIMO SÉPTIMO", "DÉCIMO OCTAVO", "DÉCIMO NOVENO", "VIGÉSIMO",
]

CHECKLISTS = {
    "desalojo": ("Desalojo de inquilino", [
        "Contrato de arrendamiento (original o copia legalizada)",
        "Copia del DNI del arrendador",
        "Documento que acredita tu derecho sobre el inmueble (partida registral de SUNARP o título)",
        "Recibos o estado de cuenta que muestren las rentas impagas",
        "Liquidación de rentas adeudadas (calculadora de alquileres impagos)",
        "Carta notarial de requerimiento de pago o de conclusión del contrato, con cargo de entrega",
        "Acta de conciliación extrajudicial o constancia de inasistencia, cuando corresponda",
        "Comprobantes de pago de tasas judiciales y cédulas de notificación",
        "Demanda de desalojo firmada por abogado colegiado",
    ]),
    "alimentos": ("Pensión de alimentos", [
        "Acta o partida de nacimiento del hijo o hija",
        "Copia del DNI del demandante y del menor",
        "Datos del demandado: nombre completo, DNI y domicilio donde notificarlo",
        "Pruebas de los gastos del menor (colegio, salud, alimentación, vivienda, vestido)",
        "Pruebas de los ingresos o capacidad económica del demandado (centro de trabajo, boletas, bienes)",
        "Constancia de estudios, si el hijo es mayor de edad y sigue estudiando",
        "Formulario de demanda de alimentos del Poder Judicial (no es obligatoria la firma de abogado)",
        "Si ya hay sentencia o acuerdo: copia certificada y liquidación de pensiones devengadas",
    ]),
    "indecopi": ("Reclamo de consumo ante Indecopi", [
        "Comprobante de pago, contrato u orden de compra",
        "Copia de tu DNI",
        "Datos del proveedor: razón social, RUC y domicilio",
        "Pruebas del problema (fotos, videos, correos, chats, publicidad ofrecida)",
        "Hoja del Libro de Reclamaciones presentada al proveedor y su respuesta, si la hubo",
        "Relación de hechos ordenada por fecha (cuaderno de hechos)",
        "Pedido concreto: reparación, cambio, devolución del dinero u otro",
        "Comprobante de pago de la tasa, si presentas denuncia (el reclamo ante el SAC es gratuito)",
    ]),
    "deuda": ("Cobro de deuda", [
        "Documento que acredita la deuda (contrato, pagaré, letra, factura o reconocimiento de deuda)",
        "Copia de tu DNI o ficha RUC",
        "Datos del deudor: nombre o razón social, documento y domicilio",
        "Constancias de los pagos parciales recibidos (registro de pagos y deudas)",
        "Carta notarial de requerimiento de pago, con cargo de entrega",
        "Liquidación de capital e intereses (calculadora de intereses legales)",
        "Acta de conciliación extrajudicial o constancia de inasistencia, si el documento no es título ejecutivo",
        "Comprobantes de pago de tasas judiciales y cédulas de notificación",
    ]),
    "laboral": ("Reclamo laboral (despido o beneficios impagos)", [
        "Contrato de trabajo o pruebas del vínculo laboral (boletas, correos, fotocheck, mensajes)",
        "Boletas de pago de los últimos meses",
        "Carta de despido, carta de renuncia o constancia de cese",
        "Copia de tu DNI",
        "Liquidación de beneficios sociales (calculadora de beneficios sociales)",
        "Constancias de depósitos de CTS",
        "Denuncia ante SUNAFIL o solicitud de conciliación administrativa (opcional)",
        "Registrar en Plazos el vencimiento para impugnar el despido (30 días hábiles desde el cese)",
    ]),
    "otro": ("Otro trámite (lista propia)", []),
}


class CurrencyInput(BaseModel):
    currency: str = Field(pattern=r"^(PEN|USD)$")


class ChecklistItem(BaseModel):
    text: str = Field(min_length=2, max_length=300)
    done: bool = False


class ChecklistInput(BaseModel):
    tramite: str
    items: Optional[List[ChecklistItem]] = Field(default=None, max_length=60)


class BundleInput(BaseModel):
    message_id: Optional[str] = None
    doc_index: Optional[int] = None
    include_facts: bool = False
    include_ledger: bool = False
    files: List[str] = Field(default_factory=list, max_length=60)


def _fmt(iso: str) -> str:
    return date.fromisoformat(iso).strftime("%d/%m/%Y")


def _cell(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").replace("|", "/")).strip()


def _safe(name: str, limit: int = 80) -> str:
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^\w.\- ]", "_", ascii_name).strip()[:limit] or "archivo"


def _symbol(case_doc: dict) -> str:
    return "US$" if case_doc.get("ledger_currency") == "USD" else "S/"


async def _evidence(case_id: str) -> list:
    out, seen = [], set()

    def add(f, origin):
        if f and f["stored_name"] not in seen and (cases_dir / case_id / f["stored_name"]).is_file():
            seen.add(f["stored_name"])
            out.append({**{k: f.get(k) for k in FILE_KEYS}, "origin": origin})

    async for m in db.case_messages.find({"case_id": case_id, "attachments.0": {"$exists": True}}).sort("created_at", 1):
        for a in m["attachments"]:
            add(a, "Chat" if a.get("kind") == "upload" else "Generado por IA")
    async for e in db.case_ledger.find({"case_id": case_id, "file": {"$ne": None}}).sort("date", 1):
        add(e["file"], "Pagos y deudas")
    async for e in db.case_facts.find({"case_id": case_id, "file": {"$ne": None}}).sort("date", 1):
        add(e["file"], "Cuaderno de hechos")
    return out


async def _store_file(case_id: str, file: Optional[UploadFile], stored_name: Optional[str]) -> Optional[dict]:
    if file and file.filename:
        ext = Path(file.filename).suffix.lower()
        if ext not in CASE_EXT_MIME:
            raise HTTPException(status_code=400, detail=f"Formato no soportado: {ext}. Usa PDF, imágenes, Excel/CSV, audio o video.")
        content = await file.read()
        if len(content) > MAX_CASE_FILE_SIZE:
            raise HTTPException(status_code=400, detail="El archivo supera los 50MB")
        name = f"{uuid.uuid4().hex}{ext}"
        (cases_dir / case_id).mkdir(exist_ok=True)
        (cases_dir / case_id / name).write_bytes(content)
        return {"filename": file.filename, "stored_name": name, "mime_type": CASE_EXT_MIME[ext], "size": len(content)}
    if stored_name:
        for f in await _evidence(case_id):
            if f["stored_name"] == stored_name:
                return {k: f[k] for k in FILE_KEYS}
        raise HTTPException(status_code=400, detail="El archivo seleccionado no pertenece a este caso")
    return None


async def _add_record_message(case_doc: dict, content: str) -> str:
    now = datetime.now(timezone.utc).isoformat()
    result = await db.case_messages.insert_one(
        {"case_id": str(case_doc["_id"]), "role": "assistant", "content": content, "attachments": [], "kind": "record", "created_at": now}
    )
    await db.cases.update_one({"_id": case_doc["_id"]}, {"$set": {"updated_at": now}})
    return str(result.inserted_id)


async def _delete_entry(collection, case_id: str, entry_id: str):
    try:
        oid = ObjectId(entry_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    result = await collection.delete_one({"_id": oid, "case_id": case_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    return {"message": "Registro eliminado"}


@router.get("/{case_id}/evidence")
async def list_evidence(case_id: str, user: dict = Depends(get_current_user)):
    await _get_case(case_id, user)
    return await _evidence(case_id)


# ---------- PAGOS Y DEUDAS ----------

async def _ledger(case_doc: dict) -> dict:
    docs = await db.case_ledger.find({"case_id": str(case_doc["_id"])}).sort([("date", 1), ("created_at", 1)]).to_list(2000)
    balance, cargos, pagos, entries = 0.0, 0.0, 0.0, []
    for e in docs:
        if e["type"] == "cargo":
            cargos += e["amount"]
            balance += e["amount"]
        else:
            pagos += e["amount"]
            balance -= e["amount"]
        entries.append({
            "id": str(e["_id"]), "type": e["type"], "date": e["date"], "amount": e["amount"],
            "concept": e["concept"], "file": e.get("file"), "balance": round(balance, 2),
        })
    return {
        "currency": case_doc.get("ledger_currency") or "PEN",
        "entries": entries,
        "total_cargos": round(cargos, 2),
        "total_pagos": round(pagos, 2),
        "saldo": round(balance, 2),
    }


def _ledger_markdown(ledger: dict, symbol: str) -> str:
    def money(v):
        return f"{symbol} {v:,.2f}"

    rows = "\n".join(
        f"| {_fmt(e['date'])} | {_cell(e['concept'])} | {money(e['amount']) if e['type'] == 'cargo' else ''} | "
        f"{money(e['amount']) if e['type'] == 'pago' else ''} | {money(e['balance'])} | {_cell((e['file'] or {}).get('filename', ''))} |"
        for e in ledger["entries"]
    )
    return (
        "### Resumen\n| Concepto | Monto |\n|---|---|\n"
        f"| Total adeudado (cargos) | {money(ledger['total_cargos'])} |\n| Total pagado | {money(ledger['total_pagos'])} |\n"
        f"| **Saldo pendiente** | **{money(ledger['saldo'])}** |\n\n"
        "### Detalle\n| Fecha | Concepto | Cargo | Pago | Saldo | Comprobante |\n|---|---|---|---|---|---|\n" + rows
    )


@router.get("/{case_id}/ledger")
async def get_ledger(case_id: str, user: dict = Depends(get_current_user)):
    return await _ledger(await _get_case(case_id, user))


@router.post("/{case_id}/ledger")
async def add_ledger_entry(
    case_id: str,
    type: str = Form(pattern=r"^(cargo|pago)$"),
    date_: str = Form(alias="date"),
    amount: float = Form(gt=0, le=1_000_000_000),
    concept: str = Form(min_length=2, max_length=200),
    repeat_until: Optional[str] = Form(None),
    stored_name: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    user: dict = Depends(get_current_user),
):
    case_doc = await _get_case(case_id, user)
    _require_enabled(case_doc, user)
    start = date.fromisoformat(_valid_date(date_))
    dates = [start]
    if repeat_until:
        try:
            year, month = repeat_until[:7].split("-")
            last = date(int(year), int(month), 28)
        except ValueError:
            raise HTTPException(status_code=400, detail="Mes final inválido")
        while (nxt := start + relativedelta(months=len(dates))).replace(day=1) <= last.replace(day=1):
            dates.append(nxt)
            if len(dates) > 120:
                raise HTTPException(status_code=400, detail="Máximo 120 meses por registro")
    stored = await _store_file(case_id, file, stored_name)
    now = datetime.now(timezone.utc).isoformat()
    await db.case_ledger.insert_many([
        {"case_id": case_id, "type": type, "date": d.isoformat(), "amount": round(amount, 2),
         "concept": concept.strip(), "file": stored if i == 0 else None, "created_at": now}
        for i, d in enumerate(dates)
    ])
    return await _ledger(case_doc)


@router.put("/{case_id}/ledger/currency")
async def set_ledger_currency(case_id: str, data: CurrencyInput, user: dict = Depends(get_current_user)):
    case_doc = await _get_case(case_id, user)
    await db.cases.update_one({"_id": case_doc["_id"]}, {"$set": {"ledger_currency": data.currency}})
    return await _ledger({**case_doc, "ledger_currency": data.currency})


@router.delete("/{case_id}/ledger/{entry_id}")
async def delete_ledger_entry(case_id: str, entry_id: str, user: dict = Depends(get_current_user)):
    await _get_case(case_id, user)
    return await _delete_entry(db.case_ledger, case_id, entry_id)


@router.post("/{case_id}/ledger/export")
async def export_ledger(case_id: str, user: dict = Depends(get_current_user)):
    case_doc = await _get_case(case_id, user)
    _require_enabled(case_doc, user)
    ledger = await _ledger(case_doc)
    if not ledger["entries"]:
        raise HTTPException(status_code=400, detail="Aún no hay cargos ni pagos registrados")
    content = (
        "## Estado de cuenta de pagos y deudas\n\n"
        f"*Elaborado con el registro de pagos y deudas del expediente al {datetime.now(timezone.utc).strftime('%d/%m/%Y')} "
        "(datos ingresados por el cliente, sumas exactas, no generado por IA).*\n\n" + _ledger_markdown(ledger, _symbol(case_doc))
    )
    return {"message_id": await _add_record_message(case_doc, content)}


# ---------- CUADERNO DE HECHOS ----------

async def _facts(case_id: str) -> list:
    docs = await db.case_facts.find({"case_id": case_id}).sort([("date", 1), ("created_at", 1)]).to_list(1000)
    return [{"id": str(f["_id"]), "date": f["date"], "text": f["text"], "file": f.get("file")} for f in docs]


def _facts_markdown(facts: list) -> str:
    lines = []
    for i, f in enumerate(facts):
        ordinal = ORDINALS[i] if i < len(ORDINALS) else f"{i + 1}"
        proof = f" *(Prueba: {_cell(f['file']['filename'])})*" if f.get("file") else ""
        lines.append(f"**{ordinal}.-** Con fecha {_fmt(f['date'])}: {_cell(f['text'])}{proof}")
    return "\n\n".join(lines)


@router.get("/{case_id}/facts")
async def list_facts(case_id: str, user: dict = Depends(get_current_user)):
    await _get_case(case_id, user)
    return await _facts(case_id)


@router.post("/{case_id}/facts")
async def add_fact(
    case_id: str,
    date_: str = Form(alias="date"),
    text: str = Form(min_length=3, max_length=2000),
    stored_name: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    user: dict = Depends(get_current_user),
):
    case_doc = await _get_case(case_id, user)
    _require_enabled(case_doc, user)
    doc = {
        "case_id": case_id,
        "date": _valid_date(date_),
        "text": text.strip(),
        "file": await _store_file(case_id, file, stored_name),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.case_facts.insert_one(doc)
    return await _facts(case_id)


@router.delete("/{case_id}/facts/{fact_id}")
async def delete_fact(case_id: str, fact_id: str, user: dict = Depends(get_current_user)):
    await _get_case(case_id, user)
    return await _delete_entry(db.case_facts, case_id, fact_id)


@router.post("/{case_id}/facts/export")
async def export_facts(case_id: str, user: dict = Depends(get_current_user)):
    case_doc = await _get_case(case_id, user)
    _require_enabled(case_doc, user)
    facts = await _facts(case_id)
    if not facts:
        raise HTTPException(status_code=400, detail="Aún no hay hechos registrados")
    content = (
        "## Relación de hechos\n\n*Cronología registrada por el cliente en el cuaderno de hechos del expediente, ordenada por fecha.*\n\n"
        + _facts_markdown(facts)
    )
    return {"message_id": await _add_record_message(case_doc, content)}


# ---------- CHECKLIST ----------

def _checklist_out(case_doc: dict) -> dict:
    saved = case_doc.get("checklist") or {"tramite": "", "items": []}
    return {**saved, "templates": [{"key": k, "label": v[0]} for k, v in CHECKLISTS.items()]}


@router.get("/{case_id}/checklist")
async def get_checklist(case_id: str, user: dict = Depends(get_current_user)):
    return _checklist_out(await _get_case(case_id, user))


@router.put("/{case_id}/checklist")
async def save_checklist(case_id: str, data: ChecklistInput, user: dict = Depends(get_current_user)):
    case_doc = await _get_case(case_id, user)
    _require_enabled(case_doc, user)
    if data.tramite not in CHECKLISTS:
        raise HTTPException(status_code=400, detail="Trámite no disponible")
    items = (
        [{"text": t, "done": False} for t in CHECKLISTS[data.tramite][1]]
        if data.items is None
        else [{"text": i.text.strip(), "done": i.done} for i in data.items]
    )
    checklist = {"tramite": data.tramite, "items": items}
    await db.cases.update_one({"_id": case_doc["_id"]}, {"$set": {"checklist": checklist}})
    return _checklist_out({"checklist": checklist})


# ---------- EXPEDIENTE PARA PRESENTAR ----------

@router.post("/{case_id}/bundle")
async def export_bundle(case_id: str, data: BundleInput, user: dict = Depends(get_current_user)):
    case_doc = await _get_case(case_id, user)
    _require_enabled(case_doc, user)
    sections = []
    if data.message_id:
        try:
            msg = await db.case_messages.find_one({"_id": ObjectId(data.message_id), "case_id": case_id, "role": "assistant"})
        except Exception:
            msg = None
        if not msg:
            raise HTTPException(status_code=404, detail="Documento no encontrado")
        blocks = DOC_BLOCK_RE.findall(msg["content"])
        if blocks and data.doc_index is not None and 0 <= data.doc_index < len(blocks):
            title, body = blocks[data.doc_index]
        else:
            title, body = case_doc["title"], DOC_BLOCK_RE.sub(lambda m: f"## {m.group(1).strip()}\n\n{m.group(2).strip()}", msg["content"])
        title = title.strip() or case_doc["title"]
        sections.append(("Escrito", title, _consulting_pdf(title, body.strip(), case_id)))
    if data.include_facts and (facts := await _facts(case_id)):
        sections.append(("Hechos", "Relación de hechos", _consulting_pdf("Relación de hechos", _facts_markdown(facts), case_id)))
    if data.include_ledger and (ledger := await _ledger(case_doc))["entries"]:
        md = _ledger_markdown(ledger, _symbol(case_doc))
        sections.append(("Cuenta", "Estado de cuenta de pagos y deudas", _consulting_pdf("Estado de cuenta de pagos y deudas", md, case_id)))
    by_name = {f["stored_name"]: f for f in await _evidence(case_id)}
    if any(name not in by_name for name in data.files):
        raise HTTPException(status_code=400, detail="Uno de los archivos seleccionados ya no existe en el caso")
    annexes = [(by_name[n]["filename"], by_name[n]["mime_type"], cases_dir / case_id / n) for n in dict.fromkeys(data.files)]
    if not sections and not annexes:
        raise HTTPException(status_code=400, detail="Selecciona al menos un documento o un anexo")
    pdf_bytes = await asyncio.to_thread(build_bundle, case_doc["title"], case_id, sections, annexes)
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="Expediente_{_safe(case_doc["title"], 40).replace(" ", "_")}.pdf"'},
    )


# ---------- DESCARGA COMPLETA ----------

def _csv(headers: list, rows: list) -> bytes:
    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8-sig")


def _build_zip(path: str, case_doc: dict, case_id: str, msgs: list, events: list, facts: list, ledger: dict, files: list):
    used = set()

    def unique(folder: str, name: str) -> str:
        base, ext = os.path.splitext(_safe(name))
        candidate, n = f"{folder}/{base}{ext}", 1
        while candidate in used:
            n += 1
            candidate = f"{folder}/{base}_{n}{ext}"
        used.add(candidate)
        return candidate

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        convo = [f"# {case_doc['title']}\n\n{case_doc.get('description') or ''}\n\nExpediente {case_id}\n"]
        for m in msgs:
            who = "Tú" if m["role"] == "user" else "Consultor OnBuySolutions"
            body = DOC_BLOCK_RE.sub(lambda mt: f"\n---\n### {mt.group(1).strip()}\n\n{mt.group(2).strip()}\n---\n", m.get("content", ""))
            attached = "".join(f"\n- Archivo: {a['filename']}" for a in m.get("attachments", []))
            convo.append(f"\n## {who} — {m['created_at'][:16].replace('T', ' ')} UTC\n\n{body}{attached}\n")
            if m["role"] != "assistant":
                continue
            for title, doc_body in DOC_BLOCK_RE.findall(m.get("content", "")):
                title = title.strip() or "Documento"
                z.writestr(unique("documentos", f"{title}.pdf"), _consulting_pdf(title, doc_body.strip(), case_id))
            if m.get("kind"):
                title = (re.search(r"^## (.+)$", m["content"], re.MULTILINE) or [None, "Registro"])[1]
                z.writestr(unique("calculos_y_registros", f"{title}.pdf"), _consulting_pdf(title, m["content"], case_id))
        z.writestr("conversacion.md", "".join(convo))
        for f in files:
            z.write(cases_dir / case_id / f["stored_name"], unique("archivos", f["filename"]), compress_type=zipfile.ZIP_STORED)
        report = case_doc.get("final_report") or {}
        if report.get("stored_name") and (cases_dir / case_id / report["stored_name"]).is_file():
            z.write(cases_dir / case_id / report["stored_name"], "informe_final.pdf")
        if events:
            z.writestr("plazos.csv", _csv(
                ["Fecha", "Tipo", "Título", "Nota", "Cumplido"],
                [[e["date"], e["kind"], e["title"], e.get("note", ""), "sí" if e.get("done") else "no"] for e in events],
            ))
        if facts:
            z.writestr("hechos.csv", _csv(
                ["Fecha", "Hecho", "Prueba"], [[f["date"], f["text"], (f["file"] or {}).get("filename", "")] for f in facts]
            ))
        if ledger["entries"]:
            z.writestr("pagos_y_deudas.csv", _csv(
                ["Fecha", "Tipo", "Concepto", "Monto", "Saldo", "Moneda", "Comprobante"],
                [[e["date"], e["type"], e["concept"], e["amount"], e["balance"], ledger["currency"], (e["file"] or {}).get("filename", "")] for e in ledger["entries"]],
            ))
        checklist = case_doc.get("checklist") or {}
        if checklist.get("items"):
            label = CHECKLISTS.get(checklist.get("tramite"), ("Checklist",))[0]
            z.writestr("checklist.txt", f"{label}\n\n" + "\n".join(f"[{'x' if i['done'] else ' '}] {i['text']}" for i in checklist["items"]))
        z.writestr(
            "LEEME.txt",
            f"Copia completa del caso \"{case_doc['title']}\" generada el {datetime.now(timezone.utc).strftime('%d/%m/%Y')}.\n\n"
            "conversacion.md: toda la conversación con el consultor.\ndocumentos/: documentos redactados, en PDF.\n"
            "calculos_y_registros/: liquidaciones, estados de cuenta y relaciones de hechos.\narchivos/: archivos que subiste o se generaron.\n"
            "plazos.csv, hechos.csv, pagos_y_deudas.csv y checklist.txt: tus registros (los CSV se abren con Excel).\n",
        )


@router.get("/{case_id}/download-zip")
async def download_zip(case_id: str, user: dict = Depends(get_current_user)):
    case_doc = await _get_case(case_id, user)
    _require_enabled(case_doc, user)
    msgs = await db.case_messages.find({"case_id": case_id}).sort("created_at", 1).to_list(5000)
    events = await db.case_events.find({"case_id": case_id}).sort("date", 1).to_list(500)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    tmp.close()
    try:
        await asyncio.to_thread(
            _build_zip, tmp.name, case_doc, case_id, msgs, events, await _facts(case_id), await _ledger(case_doc), await _evidence(case_id)
        )
    except Exception:
        os.unlink(tmp.name)
        raise
    return FileResponse(
        tmp.name,
        media_type="application/zip",
        filename=f"Caso_{_safe(case_doc['title'], 40).replace(' ', '_')}.zip",
        background=BackgroundTask(os.unlink, tmp.name),
    )
