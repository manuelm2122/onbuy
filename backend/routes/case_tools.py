import re
import json
import html
import uuid
import asyncio
from datetime import datetime, timezone, timedelta, date
from typing import Optional

import httpx
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core import db, get_app_settings, logger
from security import get_current_user, rate_limit
from ai_engine import build_chat
from gemini_chat import UserMessage, TextDelta, StreamDone
from email_service import send_email
from calculators import CALCULATORS

router = APIRouter(prefix="/cases")

REMINDER_OFFSETS = (3, 1, 0)


class CalculationInput(BaseModel):
    type: str
    inputs: dict = Field(default_factory=dict)


class EventInput(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    kind: str = Field(default="plazo", pattern=r"^(plazo|etapa)$")
    note: str = Field(default="", max_length=500)
    source: str = Field(default="cliente", pattern=r"^(cliente|agente)$")


class EventUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=2, max_length=160)
    date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    note: Optional[str] = Field(default=None, max_length=500)
    done: Optional[bool] = None


class FailureReport(BaseModel):
    message: str = Field(default="", max_length=2000)
    error: str = Field(default="", max_length=1000)


async def _get_case(case_id: str, user: dict) -> dict:
    case_doc = await db.cases.find_one({"_id": ObjectId(case_id)}) if ObjectId.is_valid(case_id) else None
    if not case_doc or (user.get("role") != "admin" and case_doc.get("user_id") != user["_id"]):
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    return case_doc


def _require_enabled(case_doc: dict, user: dict):
    if user.get("role") != "admin" and case_doc.get("payment_status") not in ("autorizada", "prueba"):
        raise HTTPException(status_code=402, detail="Habilita este chat para usar las herramientas del expediente.")


def _valid_date(value: str) -> str:
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        raise HTTPException(status_code=400, detail="Fecha inválida")


def _event_out(e: dict) -> dict:
    return {
        "id": str(e["_id"]),
        "title": e["title"],
        "date": e["date"],
        "kind": e["kind"],
        "note": e.get("note", ""),
        "done": bool(e.get("done")),
        "source": e.get("source", "cliente"),
    }


async def _ask_json(cfg: dict, system: str, prompt: str, tools: list = None) -> list:
    chat = build_chat(cfg, session_id=f"tool-{uuid.uuid4().hex[:10]}", system_message=system, model=cfg["assistant_model"])
    if tools:
        chat = chat.with_tools(tools)
    chunks = []
    async for ev in chat.stream_message(UserMessage(text=prompt)):
        if isinstance(ev, TextDelta):
            chunks.append(ev.content)
        elif isinstance(ev, StreamDone):
            break
    raw = "".join(chunks)
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if not match:
        return []
    data = json.loads(match.group(0))
    return [x for x in data if isinstance(x, dict)]


# ---------- CALCULADORAS ----------

@router.post("/{case_id}/calculations")
async def run_calculation(case_id: str, data: CalculationInput, user: dict = Depends(get_current_user)):
    case_doc = await _get_case(case_id, user)
    _require_enabled(case_doc, user)
    calc = CALCULATORS.get(data.type)
    if not calc:
        raise HTTPException(status_code=400, detail="Calculadora no disponible")
    try:
        title, body = calc(data.inputs)
    except (ValueError, TypeError, OverflowError) as e:
        raise HTTPException(status_code=400, detail=str(e) or "Revisa los datos ingresados")
    now = datetime.now(timezone.utc).isoformat()
    content = (
        f"## {title}\n\n"
        "*Cálculo exacto por fórmula con la calculadora del expediente (no generado por IA). "
        "Verifica que los datos ingresados coincidan con tus documentos.*\n\n" + body
    )
    result = await db.case_messages.insert_one(
        {"case_id": case_id, "role": "assistant", "content": content, "attachments": [], "kind": "calculation", "created_at": now}
    )
    await db.cases.update_one({"_id": case_doc["_id"]}, {"$set": {"updated_at": now}})
    return {"message_id": str(result.inserted_id), "title": title}


# ---------- LÍNEA DE TIEMPO ----------

@router.get("/{case_id}/events")
async def list_events(case_id: str, user: dict = Depends(get_current_user)):
    await _get_case(case_id, user)
    docs = await db.case_events.find({"case_id": case_id}).sort("date", 1).to_list(500)
    return [_event_out(e) for e in docs]


@router.post("/{case_id}/events")
async def create_event(case_id: str, data: EventInput, user: dict = Depends(get_current_user)):
    case_doc = await _get_case(case_id, user)
    doc = data.model_dump()
    doc.update({
        "date": _valid_date(data.date),
        "title": data.title.strip(),
        "case_id": case_id,
        "done": False,
        "reminded": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    result = await db.case_events.insert_one(doc)
    doc["_id"] = result.inserted_id
    await db.cases.update_one({"_id": case_doc["_id"]}, {"$set": {"updated_at": doc["created_at"]}})
    return _event_out(doc)


@router.put("/{case_id}/events/{event_id}")
async def update_event(case_id: str, event_id: str, data: EventUpdate, user: dict = Depends(get_current_user)):
    await _get_case(case_id, user)
    updates = data.model_dump(exclude_none=True)
    if "date" in updates:
        updates["date"] = _valid_date(updates["date"])
        updates["reminded"] = []
    doc = await db.case_events.find_one_and_update(
        {"_id": ObjectId(event_id), "case_id": case_id}, {"$set": updates}, return_document=True
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    return _event_out(doc)


@router.delete("/{case_id}/events/{event_id}")
async def delete_event(case_id: str, event_id: str, user: dict = Depends(get_current_user)):
    await _get_case(case_id, user)
    result = await db.case_events.delete_one({"_id": ObjectId(event_id), "case_id": case_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    return {"message": "Evento eliminado"}


@router.post("/{case_id}/events/suggest", dependencies=[Depends(rate_limit("case-suggest", 10, 600))])
async def suggest_events(case_id: str, user: dict = Depends(get_current_user)):
    case_doc = await _get_case(case_id, user)
    _require_enabled(case_doc, user)
    memoria = (case_doc.get("memoria") or "")[-6000:]
    if not memoria.strip():
        raise HTTPException(status_code=400, detail="Primero conversa con el agente sobre tu caso para que pueda sugerir plazos.")
    existing = await db.case_events.find({"case_id": case_id}).to_list(200)
    ya = "\n".join(f"- {e['date']} {e['title']}" for e in existing) or "- ninguno"
    today = (datetime.now(timezone.utc) - timedelta(hours=5)).date().isoformat()
    system = (
        "Eres un asistente legal peruano que organiza expedientes. Propones las etapas del caso y los plazos legales o "
        "prácticos que el cliente debe vigilar, según el derecho peruano. Respondes ÚNICAMENTE un arreglo JSON válido."
    )
    prompt = (
        f"Hoy es {today}. Caso: {case_doc['title']}. {case_doc.get('description') or ''}\n\n"
        f"RESUMEN DE LA CONVERSACIÓN:\n{memoria}\n\nEVENTOS YA REGISTRADOS (no los repitas):\n{ya}\n\n"
        "Propón entre 3 y 6 eventos futuros (fecha igual o posterior a hoy), ordenados por fecha. Formato exacto:\n"
        '[{"title": "texto breve", "date": "AAAA-MM-DD", "kind": "plazo" o "etapa", "note": "por qué importa y base legal si la hay, máx. 200 caracteres"}]\n'
        'Usa "plazo" para fechas límite y "etapa" para hitos del proceso. Si una fecha depende de un hecho aún no ocurrido, estima una fecha razonable y dilo en la nota.'
    )
    try:
        items = await _ask_json(await get_app_settings(), system, prompt)
    except Exception as e:
        logger.error(f"Error sugiriendo plazos: {e}")
        raise HTTPException(status_code=502, detail="No se pudieron generar sugerencias. Inténtalo de nuevo.")
    out = []
    for it in items[:6]:
        try:
            out.append({
                "title": str(it["title"])[:160],
                "date": date.fromisoformat(str(it["date"])).isoformat(),
                "kind": it.get("kind") if it.get("kind") in ("plazo", "etapa") else "plazo",
                "note": str(it.get("note") or "")[:500],
            })
        except (KeyError, ValueError):
            continue
    return out


# ---------- VERIFICACIÓN DE CITAS ----------

async def _resolve_source(url: str) -> str:
    if "grounding-api-redirect" not in url:
        return url
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            res = await client.get(url, follow_redirects=False)
        return res.headers.get("location", "")
    except httpx.HTTPError:
        return ""


@router.post("/{case_id}/messages/{message_id}/verify-citations", dependencies=[Depends(rate_limit("case-verify", 15, 600))])
async def verify_citations(case_id: str, message_id: str, user: dict = Depends(get_current_user)):
    case_doc = await _get_case(case_id, user)
    _require_enabled(case_doc, user)
    msg = await db.case_messages.find_one({"_id": ObjectId(message_id), "case_id": case_id, "role": "assistant"})
    if not msg:
        raise HTTPException(status_code=404, detail="Mensaje no encontrado")
    if msg.get("citations"):
        return msg["citations"]
    system = (
        "Eres un verificador de citas legales del Perú. Usas la búsqueda de Google para comprobar en fuentes oficiales "
        "(SPIJ, El Peruano, gob.pe, Congreso, Tribunal Constitucional, Poder Judicial) que cada norma y artículo citado "
        "existe y dice lo que el texto afirma. Respondes ÚNICAMENTE un arreglo JSON válido."
    )
    prompt = (
        "Extrae del siguiente texto cada cita legal concreta (norma con su artículo, o norma sola si no cita artículo), máximo 12, sin repetir. "
        "Verifica cada una con la búsqueda. Formato exacto:\n"
        '[{"cita": "Código Civil, art. 1697", "estado": "verificada" | "dudosa" | "no_encontrada", '
        '"detalle": "qué dice realmente la norma o por qué es dudosa, máx. 220 caracteres", "fuente": "URL oficial encontrada en la búsqueda o cadena vacía"}]\n'
        '"verificada": la norma y el artículo existen y coinciden con lo afirmado. "dudosa": existe pero el contenido o el número no coincide del todo, o está derogada o modificada. '
        '"no_encontrada": no hallaste respaldo. No inventes URLs. Si el texto no tiene citas legales responde [].\n\nTEXTO:\n'
        + msg.get("content", "")[:14000]
    )
    try:
        items = await _ask_json(await get_app_settings(), system, prompt, tools=[{"googleSearch": {}}])
    except Exception as e:
        logger.error(f"Error verificando citas: {e}")
        raise HTTPException(status_code=502, detail="No se pudo completar la verificación. Inténtalo de nuevo.")
    clean = []
    for it in items[:12]:
        fuente = await _resolve_source(str(it.get("fuente") or ""))
        clean.append({
            "cita": str(it.get("cita") or "")[:200],
            "estado": it.get("estado") if it.get("estado") in ("verificada", "dudosa", "no_encontrada") else "dudosa",
            "detalle": str(it.get("detalle") or "")[:400],
            "fuente": fuente if fuente.startswith("https://") else "",
        })
    citations = {"checked_at": datetime.now(timezone.utc).isoformat(), "items": [c for c in clean if c["cita"]]}
    await db.case_messages.update_one({"_id": msg["_id"]}, {"$set": {"citations": citations}})
    return citations


# ---------- REPORTE DE FALLAS ----------

@router.post("/{case_id}/report-failure", dependencies=[Depends(rate_limit("case-report", 5, 600))])
async def report_failure(case_id: str, data: FailureReport, user: dict = Depends(get_current_user)):
    case_doc = await _get_case(case_id, user)
    now = datetime.now(timezone.utc)
    detail = (
        f"Falla al enviar un mensaje en el chat de asesoría.\nCaso: {case_doc['title']} ({case_id})\n"
        f"Fecha (UTC): {now.strftime('%Y-%m-%d %H:%M')}\nError: {data.error or 'sin detalle'}\n\nMensaje que intentó enviar:\n{data.message or '(solo archivos)'}"
    )
    await db.contacts.insert_one({
        "name": user.get("name") or user["email"],
        "email": user["email"],
        "message": detail,
        "service": "Falla en chat de asesoría",
        "read": False,
        "created_at": now.isoformat(),
    })
    cfg = await get_app_settings()
    await send_email(
        to=cfg["forward_email"] or cfg["complaints_notify_email"],
        subject=f"[onbuysolutions.com] Falla en el chat de asesoría — {user['email']}",
        html=f'<div style="font-family:Arial,sans-serif;font-size:13px;color:#334155;white-space:pre-wrap">{html.escape(detail)}</div>',
        reply_to=user["email"],
    )
    return {"message": "Reporte enviado. Nuestro equipo revisará la falla y te contactará."}


# ---------- RECORDATORIOS ----------

async def send_due_reminders():
    today = (datetime.now(timezone.utc) - timedelta(hours=5)).date()
    for offset in REMINDER_OFFSETS:
        target = (today + timedelta(days=offset)).isoformat()
        query = {"kind": "plazo", "done": {"$ne": True}, "date": target, "reminded": {"$ne": offset}}
        for ev in await db.case_events.find(query).to_list(500):
            claimed = await db.case_events.find_one_and_update(
                {"_id": ev["_id"], "reminded": {"$ne": offset}}, {"$addToSet": {"reminded": offset}}
            )
            case_doc = await db.cases.find_one({"_id": ObjectId(ev["case_id"])})
            if not claimed or not case_doc or not case_doc.get("owner_email"):
                continue
            when = "vence hoy" if offset == 0 else "vence mañana" if offset == 1 else f"vence en {offset} días"
            fecha = date.fromisoformat(ev["date"]).strftime("%d/%m/%Y")
            body = (
                '<div style="font-family:Arial,sans-serif;color:#334155;font-size:14px;max-width:560px">'
                f'<h2 style="color:#0F172A;font-size:17px">Recordatorio: un plazo de tu caso {when}</h2>'
                f"<p><b>{html.escape(ev['title'])}</b><br>Fecha límite: {fecha}</p>"
                f"<p>Caso: {html.escape(case_doc['title'])}</p>"
                + (f"<p style=\"color:#64748B\">{html.escape(ev['note'])}</p>" if ev.get("note") else "")
                + '<p style="font-size:12px;color:#64748B">Ingresa a tu panel de OnBuySolutions → Consultoría → Plazos para marcarlo como cumplido o pedir ayuda al agente.</p></div>'
            )
            sent = await send_email(to=case_doc["owner_email"], subject=f"Tu plazo {when}: {ev['title']}", html=body)
            if sent.get("status") != "sent":
                await db.case_events.update_one({"_id": ev["_id"]}, {"$pull": {"reminded": offset}})


async def reminder_loop():
    while True:
        try:
            await send_due_reminders()
        except Exception as e:
            logger.error(f"Error en recordatorios de plazos: {e}")
        await asyncio.sleep(3600)
