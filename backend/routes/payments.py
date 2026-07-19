import base64
from datetime import datetime, timezone, timedelta

import httpx
from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from core import db, logger, get_app_settings
from models import CreateOrderInput
from security import get_current_user
from email_service import send_email

router = APIRouter(prefix="/payments")

RATE_CACHE_HOURS = 6
PLAN_LABELS = {
    "small": "Condominio pequeño (menos de 50 dptos.)",
    "medium": "Condominio mediano-grande (50 a 150 dptos.)",
    "consulting": "Consulta legal-contable con IA",
}


def _paypal_base(mode: str) -> str:
    return "https://api-m.sandbox.paypal.com" if mode == "sandbox" else "https://api-m.paypal.com"


async def _paypal_token(cfg: dict) -> str:
    if not cfg.get("paypal_client_id") or not cfg.get("paypal_secret"):
        raise HTTPException(status_code=503, detail="Los pagos con PayPal no están configurados. Contacta a OnBuySolutions.")
    auth = base64.b64encode(f"{cfg['paypal_client_id']}:{cfg['paypal_secret']}".encode()).decode()
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{_paypal_base(cfg['paypal_mode'])}/v1/oauth2/token",
            headers={"Authorization": f"Basic {auth}"},
            data={"grant_type": "client_credentials"},
        )
    if r.status_code != 200:
        logger.error(f"PayPal token error {r.status_code}: {r.text[:300]}")
        raise HTTPException(status_code=502, detail="No se pudo conectar con PayPal. Verifica las credenciales en Configuración.")
    return r.json()["access_token"]


async def get_pen_usd_rate() -> float:
    now = datetime.now(timezone.utc)
    cached = await db.cache.find_one({"_id": "pen_usd"})
    if cached and datetime.fromisoformat(cached["fetched_at"]) > now - timedelta(hours=RATE_CACHE_HOURS):
        return cached["rate"]
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get("https://open.er-api.com/v6/latest/PEN")
            r.raise_for_status()
            rate = float(r.json()["rates"]["USD"])
        await db.cache.update_one({"_id": "pen_usd"}, {"$set": {"rate": rate, "fetched_at": now.isoformat()}}, upsert=True)
        return rate
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo tipo de cambio: {e}")
        if cached:
            return cached["rate"]
        raise HTTPException(status_code=503, detail="No se pudo obtener el tipo de cambio del día. Intenta nuevamente en unos minutos.")


def _plan_amount_pen(cfg: dict, plan: str) -> float:
    if plan == "consulting":
        return float(cfg["price_consulting"])
    return float(cfg["price_small"] if plan == "small" else cfg["price_medium"])


@router.get("/config")
async def payment_config(user: dict = Depends(get_current_user)):
    cfg = await get_app_settings()
    if not cfg.get("paypal_client_id"):
        raise HTTPException(status_code=503, detail="Los pagos con PayPal no están configurados.")
    return {"client_id": cfg["paypal_client_id"], "mode": cfg["paypal_mode"], "currency": "USD"}


@router.get("/quote")
async def payment_quote(plan: str, user: dict = Depends(get_current_user)):
    if plan not in PLAN_LABELS:
        raise HTTPException(status_code=400, detail="Plan inválido")
    cfg = await get_app_settings()
    rate = await get_pen_usd_rate()
    amount_pen = _plan_amount_pen(cfg, plan)
    amount_usd = round(amount_pen * rate, 2)
    return {
        "plan": plan,
        "plan_label": PLAN_LABELS[plan],
        "amount_pen": amount_pen,
        "amount_usd": amount_usd,
        "rate_pen_per_usd": round(1 / rate, 4) if rate else None,
    }


@router.post("/create-order")
async def create_order(data: CreateOrderInput, user: dict = Depends(get_current_user)):
    cfg = await get_app_settings()
    is_recharge = False

    if data.item_type == "audit":
        if data.plan not in ("small", "medium"):
            raise HTTPException(status_code=400, detail="Plan inválido")
        plan = data.plan
        audit = await db.audits.find_one({"_id": ObjectId(data.item_id), "user_id": user["_id"]})
        if not audit:
            raise HTTPException(status_code=404, detail="Auditoría no encontrada")
        if audit.get("payment_status") == "autorizada":
            raise HTTPException(status_code=400, detail="Esta auditoría ya está activada. No es necesario pagar de nuevo.")
        description = f"Auditoría IA — {audit['condominium_name']} ({audit['period']})"
        concept = audit["condominium_name"]
    elif data.item_type == "case":
        plan = "consulting"
        case = await db.cases.find_one({"_id": ObjectId(data.item_id), "user_id": user["_id"]})
        if not case:
            raise HTTPException(status_code=404, detail="Consulta no encontrada")
        if user.get("role") == "admin":
            raise HTTPException(status_code=400, detail="Los casos del administrador no requieren pago")
        is_recharge = case.get("payment_status") == "autorizada"
        description = f"Consultoría legal IA — {case['title']}" + (" (recarga)" if is_recharge else "")
        concept = case["title"]
    else:
        raise HTTPException(status_code=400, detail="Tipo de compra inválido")

    rate = await get_pen_usd_rate()
    amount_pen = _plan_amount_pen(cfg, plan)
    amount_usd = round(amount_pen * rate, 2)

    token = await _paypal_token(cfg)
    body = {
        "intent": "CAPTURE",
        "purchase_units": [{
            "reference_id": data.item_id,
            "description": description[:127],
            "amount": {"currency_code": "USD", "value": f"{amount_usd:.2f}"},
        }],
    }
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{_paypal_base(cfg['paypal_mode'])}/v2/checkout/orders",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=body,
        )
    if r.status_code not in (200, 201):
        logger.error(f"PayPal create order error {r.status_code}: {r.text[:300]}")
        raise HTTPException(status_code=502, detail="PayPal no pudo crear la orden de pago. Intenta nuevamente.")
    order = r.json()

    await db.payments.insert_one({
        "order_id": order["id"],
        "item_type": data.item_type,
        "item_id": data.item_id,
        "concept": concept,
        "is_recharge": is_recharge,
        "user_id": user["_id"],
        "user_email": user["email"],
        "plan": plan,
        "amount_pen": amount_pen,
        "exchange_rate_usd_per_pen": rate,
        "amount_usd": amount_usd,
        "currency": "USD",
        "status": "created",
        "paypal_mode": cfg["paypal_mode"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"order_id": order["id"], "amount_usd": amount_usd, "amount_pen": amount_pen}


def _payment_email_html(name: str, concept_rows: str, pay: dict, capture_id: str, intro: str) -> str:
    from routes.auth import _email_shell
    return _email_shell(f"""
        <h2 style="color:#0F172A; font-size:17px; margin:0 0 12px;">¡Pago confirmado!</h2>
        <p style="color:#334155; font-size:13px; line-height:1.6; margin:0 0 16px;">
          Hola <b>{name}</b>: {intro}
        </p>
        <table cellpadding="6" cellspacing="0" style="font-size:13px; color:#334155; border:1px solid #E2E8F0; width:100%;">
          {concept_rows}
          <tr><td><b>Monto</b></td><td>USD {pay['amount_usd']:.2f} (S/ {pay['amount_pen']:.2f})</td></tr>
          <tr style="background:#F8FAFC;"><td><b>ID de transacción</b></td><td style="font-family:monospace; font-size:11px;">{capture_id}</td></tr>
        </table>
        <p style="margin:20px 0 0;">
          <a href="https://www.onbuysolutions.com/panel" style="background:#0284C7; color:#ffffff; text-decoration:none; padding:12px 28px; border-radius:999px; font-size:13px; font-weight:bold;">Ir a mi panel</a>
        </p>""")


@router.post("/capture/{order_id}")
async def capture_order(order_id: str, background_tasks: BackgroundTasks, user: dict = Depends(get_current_user)):
    pay = await db.payments.find_one({"order_id": order_id, "user_id": user["_id"]})
    if not pay:
        raise HTTPException(status_code=404, detail="Orden de pago no encontrada")
    if pay.get("status") == "completed":
        return {"message": "El pago ya fue procesado y tu auditoría está activada.", "already_captured": True}

    cfg = await get_app_settings()
    token = await _paypal_token(cfg)
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{_paypal_base(cfg['paypal_mode'])}/v2/checkout/orders/{order_id}/capture",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        data = r.json() if r.content else {}
        if r.status_code == 422 and any(i.get("issue") == "ORDER_ALREADY_CAPTURED" for i in data.get("details", [])):
            r = await client.get(
                f"{_paypal_base(cfg['paypal_mode'])}/v2/checkout/orders/{order_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            data = r.json()

    if r.status_code not in (200, 201) or data.get("status") != "COMPLETED":
        logger.error(f"PayPal capture error {r.status_code}: {str(data)[:300]}")
        raise HTTPException(status_code=400, detail="El pago no pudo completarse. No se realizó ningún cobro; intenta nuevamente.")

    captures = data["purchase_units"][0].get("payments", {}).get("captures", [])
    capture_id = captures[0]["id"] if captures else order_id
    payer_email = data.get("payer", {}).get("email_address")
    now = datetime.now(timezone.utc).isoformat()

    await db.payments.update_one(
        {"_id": pay["_id"]},
        {"$set": {"status": "completed", "capture_id": capture_id, "payer_email": payer_email, "captured_at": now}},
    )

    item_type = pay.get("item_type", "audit")
    item_id = pay.get("item_id") or pay.get("audit_id")

    if item_type == "case":
        budget_added = float(cfg["consulting_budget_usd"])
        await db.cases.update_one(
            {"_id": ObjectId(item_id)},
            {"$set": {"payment_status": "autorizada", "updated_at": now},
             "$inc": {"budget_usd": budget_added}},
        )
        logger.info(f"Pago PayPal completado: {capture_id} — consulta {item_id} {'recargada' if pay.get('is_recharge') else 'activada'}")
        case = await db.cases.find_one({"_id": ObjectId(item_id)})
        if case:
            intro = (
                "recibimos tu pago vía PayPal y tu consulta fue <b>recargada</b>: ya puedes seguir trabajando en el mismo caso."
                if pay.get("is_recharge")
                else "recibimos tu pago vía PayPal y tu consulta legal-contable quedó <b>activada automáticamente</b>. Ya puedes chatear con el consultor IA desde tu panel."
            )
            rows = f'<tr style="background:#F8FAFC;"><td><b>Consulta</b></td><td>{case["title"]}</td></tr>'
            background_tasks.add_task(
                send_email,
                user["email"],
                f"Pago confirmado — Consulta '{case['title']}' {'recargada' if pay.get('is_recharge') else 'activada'}",
                _payment_email_html(user.get("name", ""), rows, pay, capture_id, intro),
            )
        msg = "¡Pago exitoso! Tu consulta fue recargada." if pay.get("is_recharge") else "¡Pago exitoso! Tu consulta fue activada automáticamente."
        return {"message": msg, "capture_id": capture_id}

    await db.audits.update_one(
        {"_id": ObjectId(item_id)},
        {"$set": {
            "payment_status": "autorizada",
            "authorized_at": now,
            "authorized_by": f"PayPal ({capture_id})",
        }},
    )
    logger.info(f"Pago PayPal completado: {capture_id} — auditoría {item_id} activada")

    audit = await db.audits.find_one({"_id": ObjectId(item_id)})
    if audit:
        intro = "recibimos tu pago vía PayPal y tu auditoría quedó <b>activada automáticamente</b>. Ya puedes ejecutar el análisis con IA desde tu panel."
        rows = (
            f'<tr style="background:#F8FAFC;"><td><b>Condominio</b></td><td>{audit["condominium_name"]}</td></tr>'
            f'<tr><td><b>Período</b></td><td>{audit["period"]}</td></tr>'
            f'<tr style="background:#F8FAFC;"><td><b>Plan</b></td><td>{PLAN_LABELS.get(pay["plan"], pay["plan"])}</td></tr>'
        )
        background_tasks.add_task(
            send_email,
            user["email"],
            f"Pago confirmado — Auditoría {audit['condominium_name']} activada",
            _payment_email_html(user.get("name", ""), rows, pay, capture_id, intro),
        )
    return {"message": "¡Pago exitoso! Tu auditoría fue activada automáticamente.", "capture_id": capture_id}
