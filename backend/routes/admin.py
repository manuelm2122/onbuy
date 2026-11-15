import json
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
    paypal_secret = s.pop("paypal_secret", "")
    s["paypal_secret_masked"] = _mask_key(paypal_secret)
    google_key = s.pop("google_api_key", "")
    s["google_key_masked"] = _mask_key(google_key)
    vertex_json = s.pop("vertex_service_account_json", "")
    s["vertex_json_saved"] = bool(vertex_json)
    s["vertex_client_email"] = ""
    if vertex_json:
        try:
            s["vertex_client_email"] = json.loads(vertex_json).get("client_email", "")
        except ValueError:
            pass
    s.pop("active_llm_key", None)
    return s


@router.put("/settings")
async def admin_save_settings(data: SettingsInput, user: dict = Depends(get_current_user)):
    require_admin(user)
    updates = data.model_dump(exclude_none=True)
    if updates.get("paypal_mode") not in (None, "sandbox", "live"):
        raise HTTPException(status_code=400, detail="Modo PayPal inválido: usa 'sandbox' o 'live'")
    if updates.get("llm_provider") not in (None, "google", "vertex"):
        raise HTTPException(status_code=400, detail="Proveedor de IA inválido: usa 'google' o 'vertex'")
    if "vertex_service_account_json" in updates:
        raw = str(updates["vertex_service_account_json"]).strip()
        if not raw:
            updates.pop("vertex_service_account_json")
        else:
            try:
                parsed = json.loads(raw)
            except ValueError:
                raise HTTPException(status_code=400, detail="El JSON de la cuenta de servicio no es válido. Pega el contenido completo del archivo descargado de Google Cloud.")
            if not parsed.get("client_email") or not parsed.get("private_key"):
                raise HTTPException(status_code=400, detail="El JSON no parece una clave de cuenta de servicio: debe contener 'client_email' y 'private_key'")
            updates["vertex_service_account_json"] = raw
            if not updates.get("vertex_project") and parsed.get("project_id"):
                updates["vertex_project"] = parsed["project_id"]
    if updates.get("llm_provider") == "google":
        current = await get_app_settings()
        if not updates.get("google_api_key") and not current.get("google_api_key"):
            raise HTTPException(status_code=400, detail="Configura primero tu API Key de Google antes de activarla como proveedor")
    if updates.get("llm_provider") == "vertex":
        current = await get_app_settings()
        if not updates.get("vertex_service_account_json") and not current.get("vertex_service_account_json"):
            raise HTTPException(status_code=400, detail="Pega primero el JSON de la cuenta de servicio de Google Cloud antes de activar Vertex AI")
    for key_field in ("llm_key", "resend_api_key", "paypal_secret", "google_api_key"):
        if key_field in updates and not str(updates[key_field]).strip():
            updates.pop(key_field)
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.settings.update_one({"_id": "app"}, {"$set": updates}, upsert=True)
    return {"message": "Configuración guardada. Los cambios se aplican de inmediato."}


# ---------- PAYMENTS HISTORY ----------

@router.get("/payments")
async def admin_list_payments(user: dict = Depends(get_current_user)):
    require_admin(user)
    docs = await db.payments.find({}).sort("created_at", -1).to_list(500)
    audit_ids = [d.get("item_id") or d.get("audit_id") for d in docs if d.get("item_type", "audit") == "audit"]
    audits = await db.audits.find({"_id": {"$in": [ObjectId(a) for a in set(audit_ids)]}}).to_list(500)
    amap = {str(a["_id"]): a for a in audits}
    out = []
    for d in docs:
        item_type = d.get("item_type", "audit")
        item_id = d.get("item_id") or d.get("audit_id")
        if item_type == "case":
            concept = d.get("concept", "Consulta")
        else:
            concept = d.get("concept") or amap.get(item_id, {}).get("condominium_name", "—")
        out.append({
            "id": str(d["_id"]),
            "order_id": d["order_id"],
            "capture_id": d.get("capture_id"),
            "item_type": item_type,
            "item_id": item_id,
            "concept": concept,
            "is_recharge": d.get("is_recharge", False),
            "user_email": d.get("user_email", "—"),
            "plan": d.get("plan"),
            "amount_pen": d.get("amount_pen"),
            "amount_usd": d.get("amount_usd"),
            "exchange_rate": d.get("exchange_rate_usd_per_pen"),
            "status": d.get("status"),
            "paypal_mode": d.get("paypal_mode"),
            "payer_email": d.get("payer_email"),
            "created_at": d.get("created_at"),
            "captured_at": d.get("captured_at"),
        })
    return out


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
