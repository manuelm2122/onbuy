import shutil
from io import BytesIO
from pathlib import Path
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from core import db, get_app_settings, UPLOAD_DIR
from models import SettingsInput, AdminDocInput, ContactReadInput
from security import get_current_user, require_admin
from documents_generator import build_document, ADMIN_DOC_TYPES

router = APIRouter(prefix="/admin")


# ---------- AUDIT AUTHORIZATIONS ----------

@router.get("/audits")
async def admin_list_audits(user: dict = Depends(get_current_user)):
    require_admin(user)
    docs = await db.audits.find({}).sort("created_at", -1).to_list(500)
    user_ids = list({d["user_id"] for d in docs})
    users = await db.users.find({"_id": {"$in": [ObjectId(u) for u in user_ids]}}).to_list(500)
    umap = {str(u["_id"]): u for u in users}
    out = []
    for d in docs:
        owner = umap.get(d["user_id"], {})
        out.append({
            "id": str(d["_id"]),
            "condominium_name": d["condominium_name"],
            "district": d.get("district"),
            "period": d["period"],
            "status": d.get("status", "pendiente"),
            "payment_status": d.get("payment_status", "pendiente_pago"),
            "authorized_at": d.get("authorized_at"),
            "created_at": d["created_at"],
            "document_count": await db.documents.count_documents({"audit_id": str(d["_id"])}),
            "owner_name": owner.get("name", "—"),
            "owner_email": owner.get("email", "—"),
        })
    return out


@router.post("/audits/{audit_id}/authorize")
async def admin_authorize_audit(audit_id: str, user: dict = Depends(get_current_user)):
    require_admin(user)
    result = await db.audits.update_one(
        {"_id": ObjectId(audit_id)},
        {"$set": {
            "payment_status": "autorizada",
            "authorized_at": datetime.now(timezone.utc).isoformat(),
            "authorized_by": user["email"],
        }},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Auditoría no encontrada")
    return {"message": "Auditoría autorizada. El cliente ya puede ejecutar el análisis con IA."}


@router.post("/audits/{audit_id}/revoke")
async def admin_revoke_audit(audit_id: str, user: dict = Depends(get_current_user)):
    require_admin(user)
    result = await db.audits.update_one(
        {"_id": ObjectId(audit_id)},
        {"$set": {"payment_status": "pendiente_pago"}, "$unset": {"authorized_at": "", "authorized_by": ""}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Auditoría no encontrada")
    return {"message": "Autorización revocada"}


# ---------- USERS ----------

@router.get("/users")
async def admin_list_users(user: dict = Depends(get_current_user)):
    require_admin(user)
    docs = await db.users.find({}).sort("created_at", -1).to_list(1000)
    out = []
    for d in docs:
        uid = str(d["_id"])
        out.append({
            "id": uid,
            "name": d.get("name", "—"),
            "email": d["email"],
            "role": d.get("role", "cliente"),
            "created_at": d.get("created_at"),
            "audit_count": await db.audits.count_documents({"user_id": uid}),
            "document_count": await db.documents.count_documents({"user_id": uid}),
        })
    return out


@router.delete("/users/{user_id}")
async def admin_delete_user(user_id: str, user: dict = Depends(get_current_user)):
    require_admin(user)
    target = await db.users.find_one({"_id": ObjectId(user_id)})
    if not target:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if target.get("role") == "admin":
        raise HTTPException(status_code=400, detail="No se puede eliminar una cuenta de administrador")
    docs = await db.documents.find({"user_id": user_id}).to_list(2000)
    for d in docs:
        p = Path(d["stored_path"])
        if p.exists():
            p.unlink()
    audits = await db.audits.find({"user_id": user_id}).to_list(1000)
    for a in audits:
        shutil.rmtree(UPLOAD_DIR / str(a["_id"]), ignore_errors=True)
    await db.documents.delete_many({"user_id": user_id})
    await db.audits.delete_many({"user_id": user_id})
    await db.users.delete_one({"_id": ObjectId(user_id)})
    return {"message": f"Cliente eliminado junto con {len(audits)} auditoría(s) y {len(docs)} documento(s)"}


# ---------- SETTINGS ----------

def _mask_key(key: str) -> str:
    if not key:
        return ""
    return f"{key[:12]}…{key[-4:]}" if len(key) > 16 else "•" * len(key)


@router.get("/settings")
async def admin_get_settings(user: dict = Depends(get_current_user)):
    require_admin(user)
    s = await get_app_settings()
    llm_key = s.pop("llm_key", "")
    s["llm_key_masked"] = _mask_key(llm_key)
    resend_key = s.pop("resend_api_key", "")
    s["resend_key_masked"] = _mask_key(resend_key)
    return s


@router.put("/settings")
async def admin_save_settings(data: SettingsInput, user: dict = Depends(get_current_user)):
    require_admin(user)
    updates = data.model_dump(exclude_none=True)
    for key_field in ("llm_key", "resend_api_key"):
        if key_field in updates and not str(updates[key_field]).strip():
            updates.pop(key_field)
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.settings.update_one({"_id": "app"}, {"$set": updates}, upsert=True)
    return {"message": "Configuración guardada. Los cambios se aplican de inmediato."}


# ---------- CONTACT INBOX ----------

@router.get("/contacts")
async def admin_list_contacts(user: dict = Depends(get_current_user)):
    require_admin(user)
    docs = await db.contacts.find({}).sort("created_at", -1).to_list(1000)
    return [
        {
            "id": str(d["_id"]),
            "name": d.get("name", "—"),
            "email": d.get("email", "—"),
            "phone": d.get("phone"),
            "message": d.get("message", ""),
            "read": bool(d.get("read", False)),
            "created_at": d.get("created_at"),
        }
        for d in docs
    ]


@router.put("/contacts/{contact_id}/read")
async def admin_mark_contact(contact_id: str, data: ContactReadInput, user: dict = Depends(get_current_user)):
    require_admin(user)
    result = await db.contacts.update_one({"_id": ObjectId(contact_id)}, {"$set": {"read": data.read}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Mensaje no encontrado")
    return {"message": "Mensaje marcado como leído" if data.read else "Mensaje marcado como no leído"}


@router.delete("/contacts/{contact_id}")
async def admin_delete_contact(contact_id: str, user: dict = Depends(get_current_user)):
    require_admin(user)
    result = await db.contacts.delete_one({"_id": ObjectId(contact_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Mensaje no encontrado")
    return {"message": "Mensaje eliminado"}


# ---------- DOCUMENT GENERATOR ----------

@router.post("/documents/generate")
async def generate_admin_document(data: AdminDocInput, user: dict = Depends(get_current_user)):
    require_admin(user)
    if data.doc_type not in ADMIN_DOC_TYPES:
        raise HTTPException(status_code=400, detail="Tipo de documento inválido")
    pdf_bytes, filename = build_document(data.doc_type, data.fields)
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
