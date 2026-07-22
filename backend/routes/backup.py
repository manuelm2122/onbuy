import os
import re
import json
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from bson import json_util
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from pydantic import BaseModel

from core import db, logger, UPLOAD_DIR
from security import get_current_user, require_admin

router = APIRouter(prefix="/admin/backup")

BACKUP_VERSION = 1
CHUNKS_DIR = Path(tempfile.gettempdir()) / "onbuy_backup_chunks"
MAX_CHUNK_SIZE = 10 * 1024 * 1024
UPLOAD_ID_RE = re.compile(r"^[a-f0-9]{32}$")


@router.get("/export")
async def export_backup(user: dict = Depends(get_current_user)):
    require_admin(user)
    dump = {}
    counts = {}
    for name in await db.list_collection_names():
        docs = await db[name].find({}).to_list(100000)
        dump[name] = docs
        counts[name] = len(docs)
    file_count = 0
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    tmp.close()
    try:
        with zipfile.ZipFile(tmp.name, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("database.json", json_util.dumps(dump))
            if UPLOAD_DIR.exists():
                for path in UPLOAD_DIR.rglob("*"):
                    if path.is_file():
                        zf.write(path, f"uploads/{path.relative_to(UPLOAD_DIR)}")
                        file_count += 1
            zf.writestr("meta.json", json.dumps({
                "app": "onbuysolutions",
                "backup_version": BACKUP_VERSION,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "collections": counts,
                "upload_files": file_count,
            }))
    except Exception as e:
        os.remove(tmp.name)
        logger.error(f"Error generando backup: {e}")
        raise HTTPException(status_code=500, detail=f"No se pudo generar el backup: {str(e)}")
    fname = f"onbuysolutions-backup-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M')}.zip"
    logger.info(f"Backup exportado: {sum(counts.values())} documentos, {file_count} archivos")
    return FileResponse(tmp.name, filename=fname, media_type="application/zip", background=BackgroundTask(os.remove, tmp.name))


@router.post("/import/chunk")
async def import_chunk(
    upload_id: str = Form(...),
    chunk_index: int = Form(...),
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    require_admin(user)
    if not UPLOAD_ID_RE.match(upload_id):
        raise HTTPException(status_code=400, detail="upload_id inválido")
    data = await file.read()
    if len(data) > MAX_CHUNK_SIZE:
        raise HTTPException(status_code=400, detail="Fragmento demasiado grande (máx 10MB)")
    part_dir = CHUNKS_DIR / upload_id
    part_dir.mkdir(parents=True, exist_ok=True)
    (part_dir / f"{chunk_index:05d}.part").write_bytes(data)
    return {"received": chunk_index}


class ImportCompleteInput(BaseModel):
    upload_id: str
    total_chunks: int
    confirm: str


@router.post("/import/complete")
async def import_complete(data: ImportCompleteInput, user: dict = Depends(get_current_user)):
    require_admin(user)
    if data.confirm.strip().upper() != "RESTAURAR":
        raise HTTPException(status_code=400, detail='Debes escribir "RESTAURAR" para confirmar la importación')
    if not UPLOAD_ID_RE.match(data.upload_id):
        raise HTTPException(status_code=400, detail="upload_id inválido")
    part_dir = CHUNKS_DIR / data.upload_id
    parts = sorted(part_dir.glob("*.part")) if part_dir.exists() else []
    if len(parts) != data.total_chunks or data.total_chunks < 1:
        shutil.rmtree(part_dir, ignore_errors=True)
        raise HTTPException(status_code=400, detail=f"Faltan fragmentos del archivo ({len(parts)}/{data.total_chunks}). Vuelve a subir el backup.")
    zip_path = part_dir / "backup.zip"
    with open(zip_path, "wb") as out:
        for p in parts:
            out.write(p.read_bytes())
    try:
        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
            if "database.json" not in names or "meta.json" not in names:
                raise HTTPException(status_code=400, detail="El archivo no es un backup válido de OnBuySolutions (faltan database.json / meta.json)")
            meta = json.loads(zf.read("meta.json").decode("utf-8"))
            if meta.get("app") != "onbuysolutions":
                raise HTTPException(status_code=400, detail="El archivo no es un backup de OnBuySolutions")
            dump = json_util.loads(zf.read("database.json").decode("utf-8"))
            if not isinstance(dump, dict) or "users" not in dump:
                raise HTTPException(status_code=400, detail="El backup no contiene datos de usuarios: importación cancelada")

            for name in await db.list_collection_names():
                await db[name].drop()
            restored = {}
            for name, docs in dump.items():
                if docs:
                    await db[name].insert_many(docs)
                restored[name] = len(docs)

            shutil.rmtree(UPLOAD_DIR, ignore_errors=True)
            UPLOAD_DIR.mkdir(exist_ok=True)
            base = str(UPLOAD_DIR.resolve())
            file_count = 0
            for member in zf.infolist():
                if member.is_dir() or not member.filename.startswith("uploads/"):
                    continue
                rel = member.filename[len("uploads/"):]
                if not rel:
                    continue
                target = (UPLOAD_DIR / rel).resolve()
                if not str(target).startswith(base):
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(member) as src, open(target, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                file_count += 1
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="El archivo está dañado o no es un .zip válido")
    finally:
        shutil.rmtree(part_dir, ignore_errors=True)
    total_docs = sum(restored.values())
    logger.info(f"Backup restaurado: {total_docs} documentos en {len(restored)} colecciones, {file_count} archivos")
    return {
        "message": f"Backup restaurado: {total_docs} registros en {len(restored)} colecciones y {file_count} archivos. Si el usuario administrador cambió, vuelve a iniciar sesión.",
        "collections": restored,
        "upload_files": file_count,
        "backup_created_at": meta.get("created_at"),
    }
