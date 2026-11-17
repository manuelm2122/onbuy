from datetime import datetime, timezone

import html

from fastapi import APIRouter, BackgroundTasks, Depends
from security import rate_limit

from core import db, get_app_settings
from models import ContactInput
from email_service import send_email

router = APIRouter()


def _contact_notification_html(doc: dict) -> str:
    doc = {k: html.escape(v) if isinstance(v, str) else v for k, v in doc.items()}
    return f"""
<div style="font-family: Arial, sans-serif;">
  <h2 style="color:#0F172A; font-size:16px;">Nuevo mensaje de contacto</h2>
  <p style="font-size:13px; color:#334155;"><b>Sitio web: OnBuySolutions (onbuysolutions.com)</b></p>
  <table width="100%" cellpadding="8" cellspacing="0" style="border:1px solid #E2E8F0; font-size:13px; color:#334155; max-width:600px;">
    <tr style="background:#F8FAFC;"><td width="30%"><b>Nombre</b></td><td>{doc['name']}</td></tr>
    <tr><td><b>Email</b></td><td>{doc['email']}</td></tr>
    <tr style="background:#F8FAFC;"><td><b>Teléfono</b></td><td>{doc.get('phone') or '—'}</td></tr>
    <tr><td><b>Servicio</b></td><td>{doc.get('service') or '—'}</td></tr>
    <tr><td><b>Mensaje</b></td><td>{doc['message']}</td></tr>
  </table>
  <p style="font-size:12px; color:#64748B;">Gestiónalo desde el panel de administración → pestaña Mensajes.</p>
</div>"""


async def _notify_contact(doc: dict):
    cfg = await get_app_settings()
    await send_email(
        to=cfg["forward_email"] or cfg["complaints_notify_email"],
        subject=f"[onbuysolutions.com] Nuevo mensaje de contacto de {doc['name']}",
        html=_contact_notification_html(doc),
        reply_to=doc["email"],
    )


@router.post("/contact", dependencies=[Depends(rate_limit("contact", 5, 600))])
async def contact(data: ContactInput, background_tasks: BackgroundTasks):
    doc = data.model_dump()
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    doc["read"] = False
    await db.contacts.insert_one(doc)
    background_tasks.add_task(_notify_contact, doc)
    return {"message": "Mensaje recibido. Te contactaremos pronto."}


@router.get("/public/settings")
async def public_settings():
    s = await get_app_settings()
    return {
        "contact_email": s["contact_email"],
        "assistant_enabled": bool(s["assistant_enabled"]),
        "price_chat_usd": s["price_chat_usd"],
        "chat_messages": s["chat_messages"],
        "price_extra_usd": s["price_extra_usd"],
        "extra_messages": s["extra_messages"],
        "trial_messages": s["trial_messages"],
        "whatsapp_enabled": bool(s["whatsapp_enabled"]),
        "whatsapp_number": s["whatsapp_number"],
        "whatsapp_message": s["whatsapp_message"],
    }


@router.get("/")
async def root():
    return {"message": "OnBuySolutions API", "status": "ok"}
