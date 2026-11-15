
class LlmChat:
    def __init__(self, *args, **kwargs):
        raise RuntimeError("IA emergent no disponible")
    async def send_message(self, *args, **kwargs):
        raise RuntimeError("IA emergent no disponible")
    def send_message_stream(self, *args, **kwargs):
        raise RuntimeError("IA emergent no disponible")
        yield None

class UserMessage:
    def __init__(self, *args, **kwargs):
        self.text = args[0] if args else kwargs.get("text")

class FileContentWithMimeType:
    def __init__(self, *args, **kwargs):
        pass

class TextDelta:
    def __init__(self, *args, **kwargs):
        self.content = kwargs.get("content", "")

class StreamDone:
    pass

import re
import uuid
import shutil
from io import BytesIO
from pathlib import Path
from datetime import datetime, timezone
from typing import List

from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse


from core import db, logger, get_app_settings, UPLOAD_DIR, SAMPLES_DIR, SAMPLE_META, MAX_FILE_SIZE, EXT_MIME, CATEGORY_LABELS
from models import Audit, AuditCreate, DocumentOut
from security import get_current_user
from ai_engine import AUDIT_SYSTEM_PROMPT, prepare_file_contents, classify_uploaded_documents, build_chat
from pdf_report import build_audit_pdf

router = APIRouter()


@router.post("/audits", response_model=Audit, response_model_by_alias=False)
async def create_audit(data: AuditCreate, user: dict = Depends(get_current_user)):
    is_admin = user.get("role") == "admin"
    audit = Audit(
        user_id=user["_id"],
        condominium_name=data.condominium_name.strip(),
        address=data.address,
        district=data.district,
        period=data.period.strip(),
        purpose=data.purpose,
        notes=data.notes,
        payment_status="autorizada" if is_admin else "pendiente_pago",
        authorized_at=datetime.now(timezone.utc).isoformat() if is_admin else None,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    result = await db.audits.insert_one(audit.to_mongo())
    audit.id = str(result.inserted_id)
    return audit


@router.get("/audits", response_model=List[Audit], response_model_by_alias=False)
async def list_audits(user: dict = Depends(get_current_user)):
    docs = await db.audits.find({"user_id": user["_id"]}).sort("created_at", -1).to_list(200)
    audits = [Audit.from_mongo(d) for d in docs]
    for a in audits:
        a.document_count = await db.documents.count_documents({"audit_id": a.id})
    return audits


@router.get("/audits/{audit_id}", response_model=Audit, response_model_by_alias=False)
async def get_audit(audit_id: str, user: dict = Depends(get_current_user)):
    doc = await db.audits.find_one({"_id": ObjectId(audit_id), "user_id": user["_id"]})
    if not doc:
        raise HTTPException(status_code=404, detail="Auditoría no encontrada")
    audit = Audit.from_mongo(doc)
    audit.document_count = await db.documents.count_documents({"audit_id": audit_id})
    return audit


@router.delete("/audits/{audit_id}")
async def delete_audit(audit_id: str, user: dict = Depends(get_current_user)):
    query = {"_id": ObjectId(audit_id)}
    if user.get("role") != "admin":
        query["user_id"] = user["_id"]
    doc = await db.audits.find_one(query)
    if not doc:
        raise HTTPException(status_code=404, detail="Auditoría no encontrada")
    docs = await db.documents.find({"audit_id": audit_id}).to_list(500)
    for d in docs:
        p = Path(d["stored_path"])
        if p.exists():
            p.unlink()
    shutil.rmtree(UPLOAD_DIR / audit_id, ignore_errors=True)
    await db.documents.delete_many({"audit_id": audit_id})
    await db.audits.delete_one({"_id": ObjectId(audit_id)})
    return {"message": "Auditoría eliminada por completo (documentos incluidos)"}


@router.post("/audits/{audit_id}/documents", response_model=List[DocumentOut], response_model_by_alias=False)
async def upload_documents(
    audit_id: str,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    user: dict = Depends(get_current_user),
):
    audit = await db.audits.find_one({"_id": ObjectId(audit_id), "user_id": user["_id"]})
    if not audit:
        raise HTTPException(status_code=404, detail="Auditoría no encontrada")
    audit_dir = UPLOAD_DIR / audit_id
    audit_dir.mkdir(exist_ok=True)
    saved = []
    for f in files:
        ext = Path(f.filename).suffix.lower()
        if ext not in EXT_MIME:
            raise HTTPException(status_code=400, detail=f"Formato no soportado: {ext}. Usa PDF, imágenes, Excel o CSV.")
        content = await f.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail=f"El archivo {f.filename} supera los 20MB")
        stored_name = f"{uuid.uuid4().hex}{ext}"
        stored_path = audit_dir / stored_name
        stored_path.write_bytes(content)
        meta = {
            "audit_id": audit_id,
            "user_id": user["_id"],
            "filename": f.filename,
            "stored_path": str(stored_path),
            "mime_type": EXT_MIME[ext],
            "category": "clasificando",
            "size": len(content),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        result = await db.documents.insert_one(meta)
        meta["_id"] = result.inserted_id
        saved.append(DocumentOut.from_mongo(meta))
    background_tasks.add_task(classify_uploaded_documents, [d.id for d in saved])
    return saved


@router.get("/audits/{audit_id}/documents", response_model=List[DocumentOut], response_model_by_alias=False)
async def list_documents(audit_id: str, user: dict = Depends(get_current_user)):
    docs = await db.documents.find({"audit_id": audit_id, "user_id": user["_id"]}).sort("created_at", -1).to_list(500)
    return [DocumentOut.from_mongo(d) for d in docs]


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, user: dict = Depends(get_current_user)):
    doc = await db.documents.find_one({"_id": ObjectId(doc_id), "user_id": user["_id"]})
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    p = Path(doc["stored_path"])
    if p.exists():
        p.unlink()
    await db.documents.delete_one({"_id": ObjectId(doc_id)})
    return {"message": "Documento eliminado"}


@router.post("/audits/{audit_id}/analyze")
async def analyze_audit(audit_id: str, user: dict = Depends(get_current_user)):
    audit = await db.audits.find_one({"_id": ObjectId(audit_id), "user_id": user["_id"]})
    if not audit:
        raise HTTPException(status_code=404, detail="Auditoría no encontrada")
    if audit.get("payment_status") != "autorizada":
        raise HTTPException(
            status_code=402,
            detail="Esta auditoría está pendiente de autorización. OnBuySolutions habilitará el análisis con IA al confirmar tu pago.",
        )
    docs = await db.documents.find({"audit_id": audit_id}).to_list(500)
    if not docs:
        raise HTTPException(status_code=400, detail="Sube al menos un documento antes de iniciar la auditoría")

    file_contents = await prepare_file_contents(docs)
    if not file_contents:
        raise HTTPException(status_code=400, detail="No se pudieron procesar los documentos")

    doc_list = "\n".join(
        f"- {d['filename']} (Categoría: {CATEGORY_LABELS.get(d['category'], 'Otro')})" for d in docs
    )
    prompt = f"""Realiza la auditoría completa del siguiente condominio con base en los documentos adjuntos.

DATOS DE LA AUDITORÍA:
- Condominio: {audit['condominium_name']}
- Dirección: {audit.get('address') or 'No especificada'}, {audit.get('district') or ''}
- Período auditado: {audit['period']}
- Finalidad del informe: {audit.get('purpose') or 'Uso general de la junta de propietarios'}
- Notas del cliente: {audit.get('notes') or 'Ninguna'}

DOCUMENTOS ADJUNTOS ({len(docs)}):
{doc_list}

Genera el informe completo siguiendo la estructura exacta indicada."""

    cfg = await get_app_settings()
    chat = build_chat(
        cfg,
        session_id=f"audit-{audit_id}-{uuid.uuid4().hex[:8]}",
        system_message=AUDIT_SYSTEM_PROMPT,
    )

    await db.audits.update_one({"_id": ObjectId(audit_id)}, {"$set": {"status": "analizando"}})

    async def generate():
        chunks = []
        try:
            async for ev in chat.stream_message(UserMessage(text=prompt, file_contents=file_contents)):
                if isinstance(ev, TextDelta):
                    chunks.append(ev.content)
                    yield ev.content
                elif isinstance(ev, StreamDone):
                    break
            analysis = "".join(chunks)
            missing = []
            found = re.findall(r"\**DOCUMENTOS_FALTANTES:?\**:?\s*(.+)", analysis)
            if found:
                val = found[-1].strip().strip("*").strip()
                analysis = re.sub(r"\n?\**DOCUMENTOS_FALTANTES.*", "", analysis).strip()
                if val and "NINGUNO" not in val.upper():
                    missing = [s.strip(" .*") for s in val.split(";") if s.strip(" .*")]
            await db.audits.update_one(
                {"_id": ObjectId(audit_id)},
                {"$set": {
                    "analysis": analysis,
                    "status": "completada",
                    "missing_documents": missing,
                    "analysis_date": datetime.now(timezone.utc).isoformat(),
                }},
            )
        except Exception as e:
            logger.error(f"Error en análisis IA: {e}")
            await db.audits.update_one({"_id": ObjectId(audit_id)}, {"$set": {"status": "error"}})
            yield f"\n\n[ERROR] No se pudo completar el análisis: {str(e)}"

    return StreamingResponse(
        generate(),
        media_type="text/plain; charset=utf-8",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/audits/{audit_id}/report")
async def download_report(audit_id: str, user: dict = Depends(get_current_user)):
    audit = await db.audits.find_one({"_id": ObjectId(audit_id), "user_id": user["_id"]})
    if not audit:
        raise HTTPException(status_code=404, detail="Auditoría no encontrada")
    if not audit.get("analysis"):
        raise HTTPException(status_code=400, detail="Primero debes ejecutar el análisis con IA")
    doc_count = await db.documents.count_documents({"audit_id": audit_id})
    pdf_bytes = build_audit_pdf(audit, doc_count)
    safe_name = re.sub(r"[^\w\-]", "_", audit["condominium_name"])[:40]
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="Informe_Auditoria_{safe_name}.pdf"'},
    )


@router.get("/dashboard/stats")
async def dashboard_stats(user: dict = Depends(get_current_user)):
    uid = user["_id"]
    total = await db.audits.count_documents({"user_id": uid})
    completed = await db.audits.count_documents({"user_id": uid, "status": "completada"})
    pending = await db.audits.count_documents({"user_id": uid, "status": {"$in": ["pendiente", "analizando"]}})
    documents = await db.documents.count_documents({"user_id": uid})
    return {"total_audits": total, "completed": completed, "pending": pending, "documents": documents}


@router.get("/samples")
async def list_samples(user: dict = Depends(get_current_user)):
    files = []
    if SAMPLES_DIR.exists():
        for f in sorted(SAMPLES_DIR.iterdir()):
            if f.is_file():
                meta = SAMPLE_META.get(f.name, {})
                files.append({
                    "filename": f.name,
                    "size": f.stat().st_size,
                    "category": meta.get("category", "otro"),
                    "description": meta.get("description", ""),
                })
    return files


@router.get("/samples/{filename}")
async def download_sample(filename: str, user: dict = Depends(get_current_user)):
    if "/" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Nombre inválido")
    path = SAMPLES_DIR / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(path, filename=filename)
