from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core import db
from models import BaseDocument
from security import get_current_user, require_admin

router = APIRouter(prefix="/admin/audit-clients")

STATUSES = ("prospecto", "en_proceso", "entregado", "cerrado")


class AuditClientInput(BaseModel):
    full_name: str = Field(min_length=2)
    dni: str = ""
    phone: str = ""
    email: str = ""
    position: str = ""
    company_name: str = ""
    company_ruc: str = ""
    company_address: str = ""
    status: str = "prospecto"
    notes: str = ""
    source: str = "manual"


class AuditClient(AuditClientInput, BaseDocument):
    case_id: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None


def _oid(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=404, detail="Cliente no encontrado")


def _case_title(c: AuditClientInput) -> str:
    return f"Expediente — {c.company_name or c.full_name}"


def _case_description(c: AuditClientInput) -> str:
    rows = [
        ("Cliente", c.full_name), ("DNI", c.dni), ("Teléfono", c.phone), ("Correo", c.email), ("Cargo", c.position),
        ("Empresa o condominio a auditar", c.company_name), ("RUC", c.company_ruc), ("Dirección", c.company_address),
        ("Notas", c.notes),
    ]
    data = "; ".join(f"{k}: {v}" for k, v in rows if v)
    return f"Expediente interno de un cliente del servicio de auditorías (lo usa el equipo de OnBuySolutions, no el cliente). {data}"


@router.get("")
async def list_clients(user: dict = Depends(get_current_user)):
    require_admin(user)
    docs = await db.audit_clients.find({}).sort("created_at", -1).to_list(1000)
    return [AuditClient.from_mongo(d).model_dump() for d in docs]


@router.post("")
async def create_client(data: AuditClientInput, user: dict = Depends(get_current_user)):
    require_admin(user)
    if data.status not in STATUSES:
        raise HTTPException(status_code=400, detail="Estado inválido")
    email = data.email.strip().lower()
    if email:
        existing = await db.audit_clients.find_one({"email": email})
        if existing:
            return {**AuditClient.from_mongo(existing).model_dump(), "already_existed": True}
    data.email = email
    now = datetime.now(timezone.utc).isoformat()
    case = await db.cases.insert_one({
        "title": _case_title(data),
        "description": _case_description(data),
        "status": "activo",
        "user_id": user["_id"],
        "owner_email": user["email"],
        "owner_role": "admin",
        "payment_status": "autorizada",
        "budget_usd": None,
        "spent_usd": 0.0,
        "created_at": now,
        "updated_at": now,
    })
    client = AuditClient(**data.model_dump(), case_id=str(case.inserted_id), created_at=now)
    result = await db.audit_clients.insert_one(client.to_mongo())
    client.id = str(result.inserted_id)
    await db.cases.update_one({"_id": case.inserted_id}, {"$set": {"client_id": client.id}})
    return {**client.model_dump(), "already_existed": False}


@router.get("/{client_id}")
async def get_client(client_id: str, user: dict = Depends(get_current_user)):
    require_admin(user)
    doc = await db.audit_clients.find_one({"_id": _oid(client_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    audits = await db.audits.find({"client_id": client_id}).sort("created_at", -1).to_list(200)
    return {
        "client": AuditClient.from_mongo(doc).model_dump(),
        "audits": [
            {"id": str(a["_id"]), "condominium_name": a["condominium_name"], "period": a["period"], "status": a.get("status"), "created_at": a["created_at"]}
            for a in audits
        ],
    }


@router.put("/{client_id}")
async def update_client(client_id: str, data: AuditClientInput, user: dict = Depends(get_current_user)):
    require_admin(user)
    if data.status not in STATUSES:
        raise HTTPException(status_code=400, detail="Estado inválido")
    data.email = data.email.strip().lower()
    now = datetime.now(timezone.utc).isoformat()
    updates = {**data.model_dump(exclude={"source"}), "updated_at": now}
    doc = await db.audit_clients.find_one_and_update({"_id": _oid(client_id)}, {"$set": updates})
    if not doc:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    if doc.get("case_id"):
        await db.cases.update_one(
            {"_id": ObjectId(doc["case_id"])},
            {"$set": {"title": _case_title(data), "description": _case_description(data)}},
        )
    doc.update(updates)
    return AuditClient.from_mongo(doc).model_dump()


@router.delete("/{client_id}")
async def delete_client(client_id: str, user: dict = Depends(get_current_user)):
    require_admin(user)
    result = await db.audit_clients.delete_one({"_id": _oid(client_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return {"message": "Ficha eliminada. El expediente y las auditorías se conservan."}
