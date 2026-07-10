import re
import uuid
import base64
import shutil
import logging
from io import BytesIO
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import StreamingResponse, FileResponse
from bson import ObjectId
from pydantic import BaseModel, Field

from emergentintegrations.llm.chat import LlmChat, UserMessage, FileContentWithMimeType, TextDelta, StreamDone

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors as rl_colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle

logger = logging.getLogger(__name__)

MAX_CASE_FILE_SIZE = 50 * 1024 * 1024
IMAGE_MODEL = "gemini-3.1-flash-image-preview"

CASE_EXT_MIME = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".csv": "text/csv",
    ".txt": "text/plain",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".webm": "video/webm",
    ".avi": "video/x-msvideo",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".ogg": "audio/ogg",
}

CONSULTING_SYSTEM_PROMPT = """Eres el Consultor Integral de OnBuySolutions: un profesional multidisciplinario de élite para casos de condominios, juntas de propietarios, administradoras y clientes en el Perú. Combinas tres especialidades con dominio profundo del marco normativo peruano:

1. ABOGADO CIVIL: Código Civil peruano, Ley N° 27157 y su Reglamento (D.S. N° 035-2006-VIVIENDA), contratos, obligaciones, propiedad horizontal, responsabilidad civil, cartas notariales, procesos civiles y arbitraje.
2. ABOGADO PENAL: Código Penal peruano, delitos patrimoniales (apropiación ilícita, estafa, administración fraudulenta, falsificación de documentos), denuncias ante la Fiscalía, proceso penal peruano (NCPP).
3. CONTADOR PÚBLICO COLEGIADO: NIIF, NIA, tributación SUNAT, peritajes contables, conciliaciones bancarias, auditoría financiera de juntas de propietarios.

Trabajas dentro de un CASO (expediente). Toda la conversación y los archivos aportados (texto, imágenes, PDFs, hojas de cálculo, audios, videos) forman parte del expediente y debes recordarlos y organizarlos mentalmente.

REGLAS:
- Redacta SIEMPRE en español formal profesional peruano.
- Organiza la información del caso: cuando recibas nuevos datos o archivos, intégralos con lo ya conocido y señala inconsistencias o vacíos.
- Si falta información clave para aconsejar bien, pídela explícitamente al final de tu respuesta.
- Tienes acceso a búsqueda de Google: úsala cuando necesites normativa vigente, jurisprudencia, tasas, plazos o datos actuales. Cita la fuente y la norma exacta.
- Cuando el usuario pida un documento (carta notarial, denuncia, contrato, informe pericial, requerimiento, acta), redáctalo COMPLETO y listo para usar, con estructura formal peruana y campos entre corchetes [ ] para datos faltantes. El documento se exportará a PDF tal cual lo escribas.
- Analiza a fondo cualquier archivo adjunto: extrae montos, fechas, nombres, cláusulas e irregularidades relevantes para el caso.
- Responde en Markdown (títulos ##, listas, tablas, negritas).
- En temas de alto riesgo legal, recuerda que tu consultoría no reemplaza el patrocinio de un abogado colegiado ni la firma de un contador público, e indícalo brevemente cuando corresponda."""


class CaseCreate(BaseModel):
    title: str = Field(min_length=2)
    description: Optional[str] = None


class CaseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class ImageGenInput(BaseModel):
    prompt: str = Field(min_length=3)


class ExportPdfInput(BaseModel):
    message_id: str


NAVY = rl_colors.HexColor("#0F172A")
SKY = rl_colors.HexColor("#0284C7")
GRAY = rl_colors.HexColor("#64748B")
LIGHT = rl_colors.HexColor("#F1F5F9")


def _md_inline(text: str) -> str:
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<i>\1</i>", text)
    return text


def _consulting_pdf(case_title: str, content: str, case_id: str) -> bytes:
    buf = BytesIO()
    styles = {
        "title": ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=20, textColor=NAVY, spaceAfter=6, leading=24),
        "subtitle": ParagraphStyle("subtitle", fontName="Helvetica", fontSize=10, textColor=GRAY, spaceAfter=4),
        "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=13, textColor=NAVY, spaceBefore=14, spaceAfter=7),
        "h3": ParagraphStyle("h3", fontName="Helvetica-Bold", fontSize=11, textColor=SKY, spaceBefore=10, spaceAfter=5),
        "body": ParagraphStyle("body", fontName="Helvetica", fontSize=9.5, textColor=rl_colors.HexColor("#1E293B"), alignment=TA_JUSTIFY, leading=14, spaceAfter=6),
        "bullet": ParagraphStyle("bullet", fontName="Helvetica", fontSize=9.5, textColor=rl_colors.HexColor("#1E293B"), leading=14, leftIndent=14, spaceAfter=4),
        "cell": ParagraphStyle("cell", fontName="Helvetica", fontSize=8, textColor=rl_colors.HexColor("#1E293B"), leading=11),
        "cellh": ParagraphStyle("cellh", fontName="Helvetica-Bold", fontSize=8, textColor=rl_colors.white, leading=11),
        "legal": ParagraphStyle("legal", fontName="Helvetica-Oblique", fontSize=8, textColor=GRAY, alignment=TA_JUSTIFY, leading=11),
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
        canvas.drawRightString(A4[0] - 2 * cm, A4[1] - 1.1 * cm, "Consultoría Legal y Contable")
        canvas.drawCentredString(A4[0] / 2, 1 * cm, f"OnBuySolutions — Documento de consultoría asistida por IA | Página {doc_.page}")
        canvas.restoreState()

    pdf = SimpleDocTemplate(buf, pagesize=A4, topMargin=2.2 * cm, bottomMargin=2 * cm, leftMargin=2 * cm, rightMargin=2 * cm)
    story = [
        Spacer(1, 8),
        Paragraph(_md_inline(case_title), styles["title"]),
        Paragraph(f"Documento de consultoría — Emitido el {datetime.now(timezone.utc).strftime('%d/%m/%Y')} — Expediente {case_id}", styles["subtitle"]),
        HRFlowable(width="100%", thickness=1, color=SKY, spaceAfter=12),
    ]

    lines = (content or "").split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line.strip():
            i += 1
            continue
        if line.strip().startswith("|"):
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
                    data.append([Paragraph(_md_inline(c), style) for c in r])
                t = Table(data, colWidths=[17.0 / ncols * cm] * ncols, repeatRows=1)
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
        s = line.strip()
        if s.startswith("### "):
            story.append(Paragraph(_md_inline(s[4:]), styles["h3"]))
        elif s.startswith("## "):
            story.append(Paragraph(_md_inline(s[3:]), styles["h2"]))
        elif s.startswith("# "):
            story.append(Paragraph(_md_inline(s[2:]), styles["h2"]))
        elif re.match(r"^[-*]\s+", s):
            story.append(Paragraph("•&nbsp;&nbsp;" + _md_inline(re.sub(r"^[-*]\s+", "", s)), styles["bullet"]))
        elif re.match(r"^\d+\.\s+", s):
            story.append(Paragraph(_md_inline(s), styles["bullet"]))
        else:
            story.append(Paragraph(_md_inline(s), styles["body"]))
        i += 1

    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY, spaceAfter=8))
    story.append(Paragraph(
        "Documento elaborado por el módulo de Consultoría de OnBuySolutions mediante Inteligencia Artificial (Google Gemini) con supervisión humana requerida "
        "(Ley N° 31814 y D.S. N° 115-2025-PCM). No sustituye el patrocinio de un abogado colegiado ni la firma de un contador público colegiado. "
        f"Expediente de referencia: {case_id}.",
        styles["legal"],
    ))
    pdf.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return buf.getvalue()


def create_consulting_router(db, get_current_user, get_app_settings, upload_dir: Path) -> APIRouter:
    router = APIRouter(prefix="/admin/cases")
    cases_dir = upload_dir / "cases"
    cases_dir.mkdir(exist_ok=True)

    def _require_admin(user: dict):
        if user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Solo el administrador puede acceder a Consultoría")

    async def _get_case(case_id: str) -> dict:
        try:
            oid = ObjectId(case_id)
        except Exception:
            raise HTTPException(status_code=404, detail="Caso no encontrado")
        case_doc = await db.cases.find_one({"_id": oid})
        if not case_doc:
            raise HTTPException(status_code=404, detail="Caso no encontrado")
        return case_doc

    def _serialize_message(m: dict) -> dict:
        return {
            "id": str(m["_id"]),
            "case_id": m["case_id"],
            "role": m["role"],
            "content": m.get("content", ""),
            "attachments": [
                {k: a.get(k) for k in ("filename", "stored_name", "mime_type", "size", "kind")}
                for a in m.get("attachments", [])
            ],
            "created_at": m["created_at"],
        }

    async def _serialize_case(c: dict) -> dict:
        cid = str(c["_id"])
        msgs = await db.case_messages.count_documents({"case_id": cid})
        files = await db.case_messages.count_documents({"case_id": cid, "attachments.0": {"$exists": True}})
        return {
            "id": cid,
            "title": c["title"],
            "description": c.get("description") or "",
            "status": c.get("status", "activo"),
            "created_at": c["created_at"],
            "updated_at": c.get("updated_at", c["created_at"]),
            "message_count": msgs,
            "messages_with_files": files,
        }

    @router.post("")
    async def create_case(data: CaseCreate, user: dict = Depends(get_current_user)):
        _require_admin(user)
        now = datetime.now(timezone.utc).isoformat()
        doc = {
            "title": data.title.strip(),
            "description": (data.description or "").strip(),
            "status": "activo",
            "created_at": now,
            "updated_at": now,
        }
        result = await db.cases.insert_one(doc)
        (cases_dir / str(result.inserted_id)).mkdir(exist_ok=True)
        doc["_id"] = result.inserted_id
        return await _serialize_case(doc)

    @router.get("")
    async def list_cases(user: dict = Depends(get_current_user)):
        _require_admin(user)
        docs = await db.cases.find({}).sort("updated_at", -1).to_list(500)
        return [await _serialize_case(c) for c in docs]

    @router.get("/{case_id}")
    async def get_case(case_id: str, user: dict = Depends(get_current_user)):
        _require_admin(user)
        case_doc = await _get_case(case_id)
        msgs = await db.case_messages.find({"case_id": case_id}).sort("created_at", 1).to_list(1000)
        return {"case": await _serialize_case(case_doc), "messages": [_serialize_message(m) for m in msgs]}

    @router.put("/{case_id}")
    async def update_case(case_id: str, data: CaseUpdate, user: dict = Depends(get_current_user)):
        _require_admin(user)
        await _get_case(case_id)
        updates = {}
        if data.title is not None and data.title.strip():
            updates["title"] = data.title.strip()
        if data.description is not None:
            updates["description"] = data.description.strip()
        if data.status is not None:
            if data.status not in ("activo", "archivado", "cerrado"):
                raise HTTPException(status_code=400, detail="Estado inválido")
            updates["status"] = data.status
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.cases.update_one({"_id": ObjectId(case_id)}, {"$set": updates})
        return await _serialize_case(await _get_case(case_id))

    @router.delete("/{case_id}")
    async def delete_case(case_id: str, user: dict = Depends(get_current_user)):
        _require_admin(user)
        await _get_case(case_id)
        shutil.rmtree(cases_dir / case_id, ignore_errors=True)
        deleted = await db.case_messages.delete_many({"case_id": case_id})
        await db.cases.delete_one({"_id": ObjectId(case_id)})
        return {"message": f"Caso eliminado por completo ({deleted.deleted_count} mensajes y sus archivos)"}

    async def _prepare_attachment_contents(attachments: List[dict], case_dir: Path) -> List[FileContentWithMimeType]:
        import pandas as pd
        contents = []
        for a in attachments:
            path = case_dir / a["stored_name"]
            if not path.exists():
                continue
            mime = a["mime_type"]
            if "spreadsheet" in mime or mime == "application/vnd.ms-excel":
                csv_path = path.with_suffix(".converted.csv")
                if not csv_path.exists():
                    sheets = pd.read_excel(path, sheet_name=None)
                    parts = [f"--- Hoja: {name} ---\n{df.to_csv(index=False)}" for name, df in sheets.items()]
                    csv_path.write_text("\n\n".join(parts), encoding="utf-8")
                contents.append(FileContentWithMimeType(file_path=str(csv_path), mime_type="text/csv"))
            else:
                contents.append(FileContentWithMimeType(file_path=str(path), mime_type=mime))
        return contents

    @router.post("/{case_id}/chat")
    async def case_chat(
        case_id: str,
        text: str = Form(...),
        files: List[UploadFile] = File(default=[]),
        user: dict = Depends(get_current_user),
    ):
        _require_admin(user)
        case_doc = await _get_case(case_id)
        if not text.strip() and not files:
            raise HTTPException(status_code=400, detail="Escribe un mensaje o adjunta un archivo")
        case_dir = cases_dir / case_id
        case_dir.mkdir(exist_ok=True)

        attachments = []
        for f in files or []:
            ext = Path(f.filename).suffix.lower()
            if ext not in CASE_EXT_MIME:
                raise HTTPException(status_code=400, detail=f"Formato no soportado: {ext}. Usa PDF, imágenes, Excel/CSV, audio o video.")
            content = await f.read()
            if len(content) > MAX_CASE_FILE_SIZE:
                raise HTTPException(status_code=400, detail=f"El archivo {f.filename} supera los 50MB")
            stored_name = f"{uuid.uuid4().hex}{ext}"
            (case_dir / stored_name).write_bytes(content)
            attachments.append({
                "filename": f.filename,
                "stored_name": stored_name,
                "mime_type": CASE_EXT_MIME[ext],
                "size": len(content),
                "kind": "upload",
            })

        now = datetime.now(timezone.utc).isoformat()
        user_msg = {"case_id": case_id, "role": "user", "content": text.strip(), "attachments": attachments, "created_at": now}
        await db.case_messages.insert_one(user_msg)

        prior = await db.case_messages.find({"case_id": case_id, "_id": {"$ne": user_msg["_id"]}}).sort("created_at", 1).to_list(1000)
        history = [{"role": "system", "content": CONSULTING_SYSTEM_PROMPT + f"\n\nCASO ACTUAL: {case_doc['title']}. {case_doc.get('description') or ''}"}]
        for m in prior:
            content = m.get("content", "")
            if m.get("attachments"):
                names = ", ".join(a["filename"] for a in m["attachments"])
                content = f"{content}\n[Archivos adjuntados en este mensaje: {names}]".strip()
            if content:
                history.append({"role": m["role"], "content": content})

        file_contents = await _prepare_attachment_contents(attachments, case_dir)
        prompt_text = text.strip() or "Analiza los archivos adjuntos e intégralos al expediente del caso."

        cfg = await get_app_settings()
        chat = LlmChat(
            api_key=cfg["llm_key"],
            session_id=f"case-{case_id}",
            system_message=CONSULTING_SYSTEM_PROMPT,
            initial_messages=history,
        ).with_model("gemini", cfg["ai_model"]).with_tools([{"googleSearch": {}}])

        async def generate():
            chunks = []
            try:
                msg = UserMessage(text=prompt_text, file_contents=file_contents or None)
                async for ev in chat.stream_message(msg):
                    if isinstance(ev, TextDelta):
                        chunks.append(ev.content)
                        yield ev.content
                    elif isinstance(ev, StreamDone):
                        break
                answer = "".join(chunks)
                await db.case_messages.insert_one({
                    "case_id": case_id,
                    "role": "assistant",
                    "content": answer,
                    "attachments": [],
                    "created_at": datetime.now(timezone.utc).isoformat(),
                })
                await db.cases.update_one({"_id": ObjectId(case_id)}, {"$set": {"updated_at": datetime.now(timezone.utc).isoformat()}})
            except Exception as e:
                logger.error(f"Error en chat de consultoría: {e}")
                yield f"\n\n[ERROR] No se pudo completar la respuesta: {str(e)}"

        return StreamingResponse(
            generate(),
            media_type="text/plain; charset=utf-8",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @router.post("/{case_id}/generate-image")
    async def generate_case_image(case_id: str, data: ImageGenInput, user: dict = Depends(get_current_user)):
        _require_admin(user)
        await _get_case(case_id)
        case_dir = cases_dir / case_id
        case_dir.mkdir(exist_ok=True)
        cfg = await get_app_settings()
        chat = LlmChat(
            api_key=cfg["llm_key"],
            session_id=f"caseimg-{case_id}-{uuid.uuid4().hex[:8]}",
            system_message="Eres un generador de imágenes profesionales para consultoría legal y contable en Perú.",
        ).with_model("gemini", IMAGE_MODEL).with_params(modalities=["image", "text"])
        try:
            text, images = await chat.send_message_multimodal_response(UserMessage(text=data.prompt))
        except Exception as e:
            logger.error(f"Error generando imagen: {e}")
            raise HTTPException(status_code=502, detail=f"No se pudo generar la imagen: {str(e)}")
        if not images:
            raise HTTPException(status_code=502, detail="El modelo no devolvió ninguna imagen. Reformula el prompt.")
        img = images[0]
        ext = ".png" if "png" in (img.get("mime_type") or "image/png") else ".jpg"
        stored_name = f"{uuid.uuid4().hex}{ext}"
        (case_dir / stored_name).write_bytes(base64.b64decode(img["data"]))
        now = datetime.now(timezone.utc).isoformat()
        await db.case_messages.insert_one({
            "case_id": case_id,
            "role": "user",
            "content": f"[Solicitud de imagen] {data.prompt}",
            "attachments": [],
            "created_at": now,
        })
        result = await db.case_messages.insert_one({
            "case_id": case_id,
            "role": "assistant",
            "content": (text or "").strip() or "Imagen generada según lo solicitado.",
            "attachments": [{
                "filename": f"imagen_generada{ext}",
                "stored_name": stored_name,
                "mime_type": img.get("mime_type") or "image/png",
                "size": (case_dir / stored_name).stat().st_size,
                "kind": "generated",
            }],
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        await db.cases.update_one({"_id": ObjectId(case_id)}, {"$set": {"updated_at": datetime.now(timezone.utc).isoformat()}})
        msg = await db.case_messages.find_one({"_id": result.inserted_id})
        return _serialize_message(msg)

    @router.get("/{case_id}/files/{stored_name}")
    async def download_case_file(case_id: str, stored_name: str, user: dict = Depends(get_current_user)):
        _require_admin(user)
        if "/" in stored_name or ".." in stored_name:
            raise HTTPException(status_code=400, detail="Nombre inválido")
        path = cases_dir / case_id / stored_name
        if not path.is_file():
            raise HTTPException(status_code=404, detail="Archivo no encontrado")
        meta = await db.case_messages.find_one({"case_id": case_id, "attachments.stored_name": stored_name})
        filename = stored_name
        if meta:
            for a in meta.get("attachments", []):
                if a["stored_name"] == stored_name:
                    filename = a["filename"]
        return FileResponse(path, filename=filename)

    @router.post("/{case_id}/export-pdf")
    async def export_case_pdf(case_id: str, data: ExportPdfInput, user: dict = Depends(get_current_user)):
        _require_admin(user)
        case_doc = await _get_case(case_id)
        try:
            msg = await db.case_messages.find_one({"_id": ObjectId(data.message_id), "case_id": case_id})
        except Exception:
            msg = None
        if not msg or not msg.get("content"):
            raise HTTPException(status_code=404, detail="Mensaje no encontrado")
        pdf_bytes = _consulting_pdf(case_doc["title"], msg["content"], case_id)
        safe = re.sub(r"[^\w\-]", "_", case_doc["title"])[:40]
        return StreamingResponse(
            BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="Consultoria_{safe}.pdf"'},
        )

    return router
