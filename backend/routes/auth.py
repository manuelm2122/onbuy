import secrets
from datetime import datetime, timezone, timedelta

from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response

from core import db, logger
from models import (
    RegisterInput,
    LoginInput,
    ChangePasswordInput,
    VerifyEmailInput,
    ResendCodeInput,
    ForgotPasswordInput,
    ResetPasswordInput,
)
from security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    set_auth_cookies,
    get_current_user,
    check_brute_force,
    record_failed_attempt,
)
from email_service import send_email

router = APIRouter(prefix="/auth")

CODE_TTL_MINUTES = 15
MAX_CODE_ATTEMPTS = 5
RESEND_COOLDOWN_SECONDS = 60


def _generate_code() -> str:
    return f"{secrets.randbelow(1000000):06d}"


def _email_shell(inner: str) -> str:
    return f"""
<table width="100%" cellpadding="0" cellspacing="0" style="font-family: Arial, sans-serif; background:#F1F5F9; padding:24px 0;">
  <tr><td align="center">
    <table width="560" cellpadding="0" cellspacing="0" style="background:#ffffff; border:1px solid #E2E8F0;">
      <tr><td style="background:#0F172A; padding:20px 28px;">
        <span style="color:#ffffff; font-size:18px; font-weight:bold;">OnBuy<span style="color:#0EA5E9;">Solutions</span></span>
        <span style="color:#94A3B8; font-size:11px; float:right; padding-top:6px;">onbuysolutions.com</span>
      </td></tr>
      <tr><td style="padding:28px;">{inner}</td></tr>
      <tr><td style="background:#F8FAFC; border-top:1px solid #E2E8F0; padding:16px 28px;">
        <p style="color:#94A3B8; font-size:10px; margin:0; line-height:1.5;">
          ONBUYSOLUTIONS S.A.C. — RUC 20606439327 — Parque Rospigliosi 153, Pueblo Libre, Lima, Perú.<br>
          Este es un mensaje automático de www.onbuysolutions.com; por favor no responda a este correo.
        </p>
      </td></tr>
    </table>
  </td></tr>
</table>"""


def _verification_email_html(name: str, code: str) -> str:
    return _email_shell(f"""
        <h2 style="color:#0F172A; font-size:17px; margin:0 0 12px;">Verifica tu correo electrónico</h2>
        <p style="color:#334155; font-size:13px; line-height:1.6; margin:0 0 20px;">
          Hola <b>{name}</b>: usa el siguiente código para confirmar tu cuenta en OnBuySolutions.
          El código vence en {CODE_TTL_MINUTES} minutos.
        </p>
        <div style="background:#F8FAFC; border:2px dashed #0284C7; padding:18px; text-align:center;">
          <span style="font-size:32px; font-weight:bold; letter-spacing:10px; color:#0F172A; font-family: monospace;">{code}</span>
        </div>
        <p style="color:#64748B; font-size:11px; line-height:1.6; margin:16px 0 0;">
          Si no creaste una cuenta en OnBuySolutions, puedes ignorar este mensaje.
        </p>""")


def _welcome_email_html(name: str) -> str:
    return _email_shell(f"""
        <h2 style="color:#0F172A; font-size:17px; margin:0 0 12px;">¡Bienvenido a OnBuySolutions, {name}!</h2>
        <p style="color:#334155; font-size:13px; line-height:1.6; margin:0 0 16px;">
          Tu cuenta fue verificada correctamente. Ya puedes empezar a auditar las finanzas de tu condominio
          con la IA más avanzada de Google:
        </p>
        <table cellpadding="6" cellspacing="0" style="font-size:13px; color:#334155;">
          <tr><td>1.</td><td>Crea tu primera auditoría desde el panel</td></tr>
          <tr><td>2.</td><td>Sube tus documentos (facturas, estados de cuenta, recibos)</td></tr>
          <tr><td>3.</td><td>Recibe tu informe profesional en PDF con valor legal</td></tr>
        </table>
        <p style="margin:20px 0 0;">
          <a href="https://www.onbuysolutions.com/panel" style="background:#0284C7; color:#ffffff; text-decoration:none; padding:12px 28px; border-radius:999px; font-size:13px; font-weight:bold;">Ir a mi panel</a>
        </p>
        <p style="color:#64748B; font-size:11px; line-height:1.6; margin:20px 0 0;">
          Recuerda: toda auditoría incluye 1 hora de consultoría legal-contable gratis por Zoom.
        </p>""")


async def _issue_verification_code(user_doc: dict, background_tasks: BackgroundTasks):
    code = _generate_code()
    now = datetime.now(timezone.utc)
    await db.users.update_one(
        {"_id": user_doc["_id"]},
        {"$set": {
            "verification_code": code,
            "verification_expires": (now + timedelta(minutes=CODE_TTL_MINUTES)).isoformat(),
            "verification_attempts": 0,
            "verification_last_sent": now.isoformat(),
        }},
    )
    background_tasks.add_task(
        send_email,
        user_doc["email"],
        f"Tu código de verificación: {code} — OnBuySolutions",
        _verification_email_html(user_doc.get("name", ""), code),
    )


@router.post("/register")
async def register(data: RegisterInput, background_tasks: BackgroundTasks):
    if not data.accepted_terms:
        raise HTTPException(status_code=400, detail="Debes aceptar los Términos y Condiciones y la Política de Privacidad")
    email = data.email.lower().strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Este correo ya está registrado")
    doc = {
        "email": email,
        "name": data.name.strip(),
        "password_hash": hash_password(data.password),
        "role": "cliente",
        "email_verified": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "accepted_terms_at": datetime.now(timezone.utc).isoformat(),
    }
    result = await db.users.insert_one(doc)
    doc["_id"] = result.inserted_id
    await _issue_verification_code(doc, background_tasks)
    return {
        "requires_verification": True,
        "email": email,
        "message": f"Te enviamos un código de verificación a {email}. Revisa tu bandeja de entrada y spam.",
    }


@router.post("/verify-email")
async def verify_email(data: VerifyEmailInput, response: Response, background_tasks: BackgroundTasks):
    email = data.email.lower().strip()
    user = await db.users.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if user.get("email_verified"):
        raise HTTPException(status_code=400, detail="Este correo ya está verificado. Inicia sesión.")
    if user.get("verification_attempts", 0) >= MAX_CODE_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Demasiados intentos fallidos. Solicita un nuevo código.")
    expires = user.get("verification_expires")
    if not expires or datetime.fromisoformat(expires) < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="El código expiró. Solicita un nuevo código.")
    if not secrets.compare_digest(str(user.get("verification_code", "")), data.code.strip()):
        await db.users.update_one({"_id": user["_id"]}, {"$inc": {"verification_attempts": 1}})
        raise HTTPException(status_code=400, detail="Código incorrecto. Verifica e intenta de nuevo.")

    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"email_verified": True, "email_verified_at": datetime.now(timezone.utc).isoformat()},
         "$unset": {"verification_code": "", "verification_expires": "", "verification_attempts": "", "verification_last_sent": ""}},
    )
    user_id = str(user["_id"])
    set_auth_cookies(response, create_access_token(user_id, email), create_refresh_token(user_id))
    background_tasks.add_task(
        send_email,
        email,
        "¡Bienvenido a OnBuySolutions! Tu cuenta está lista",
        _welcome_email_html(user.get("name", "")),
    )
    logger.info(f"Email verificado: {email}")
    return {"id": user_id, "email": email, "name": user["name"], "role": user.get("role", "cliente")}


@router.post("/resend-code")
async def resend_code(data: ResendCodeInput, background_tasks: BackgroundTasks):
    email = data.email.lower().strip()
    user = await db.users.find_one({"email": email})
    generic = {"message": "Si el correo está registrado y pendiente de verificación, enviamos un nuevo código."}
    if not user or user.get("email_verified"):
        return generic
    last_sent = user.get("verification_last_sent")
    if last_sent and (datetime.now(timezone.utc) - datetime.fromisoformat(last_sent)).total_seconds() < RESEND_COOLDOWN_SECONDS:
        raise HTTPException(status_code=429, detail="Espera un minuto antes de solicitar otro código.")
    await _issue_verification_code(user, background_tasks)
    return generic


@router.post("/login")
async def login(data: LoginInput, request: Request, response: Response, background_tasks: BackgroundTasks):
    email = data.email.lower().strip()
    ip = request.client.host if request.client else "unknown"
    identifier = f"{ip}:{email}"
    await check_brute_force(identifier)
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(data.password, user["password_hash"]):
        await record_failed_attempt(identifier)
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos")
    await db.login_attempts.delete_one({"identifier": identifier})
    if not user.get("email_verified", True):
        last_sent = user.get("verification_last_sent")
        if not last_sent or (datetime.now(timezone.utc) - datetime.fromisoformat(last_sent)).total_seconds() >= RESEND_COOLDOWN_SECONDS:
            await _issue_verification_code(user, background_tasks)
        raise HTTPException(
            status_code=403,
            detail={"error_code": "EMAIL_NOT_VERIFIED", "msg": "Tu correo aún no está verificado. Te enviamos un código de verificación."},
        )
    user_id = str(user["_id"])
    set_auth_cookies(response, create_access_token(user_id, email), create_refresh_token(user_id))
    return {"id": user_id, "email": email, "name": user["name"], "role": user.get("role", "cliente")}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"message": "Sesión cerrada"}


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return {"id": user["_id"], "email": user["email"], "name": user["name"], "role": user.get("role", "cliente")}


def _reset_email_html(name: str, code: str) -> str:
    return _email_shell(f"""
        <h2 style="color:#0F172A; font-size:17px; margin:0 0 12px;">Restablece tu contraseña</h2>
        <p style="color:#334155; font-size:13px; line-height:1.6; margin:0 0 20px;">
          Hola <b>{name}</b>: recibimos una solicitud para restablecer la contraseña de tu cuenta.
          Usa el siguiente código para continuar. El código vence en {CODE_TTL_MINUTES} minutos.
        </p>
        <div style="background:#F8FAFC; border:2px dashed #0284C7; padding:18px; text-align:center;">
          <span style="font-size:32px; font-weight:bold; letter-spacing:10px; color:#0F172A; font-family: monospace;">{code}</span>
        </div>
        <p style="color:#64748B; font-size:11px; line-height:1.6; margin:16px 0 0;">
          Si no solicitaste este cambio, ignora este mensaje: tu contraseña actual seguirá funcionando.
        </p>""")


@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordInput, background_tasks: BackgroundTasks):
    email = data.email.lower().strip()
    generic = {"message": "Si el correo está registrado, te enviamos un código para restablecer tu contraseña."}
    user = await db.users.find_one({"email": email})
    if not user:
        return generic
    last_sent = user.get("reset_last_sent")
    if last_sent and (datetime.now(timezone.utc) - datetime.fromisoformat(last_sent)).total_seconds() < RESEND_COOLDOWN_SECONDS:
        raise HTTPException(status_code=429, detail="Espera un minuto antes de solicitar otro código.")
    code = _generate_code()
    now = datetime.now(timezone.utc)
    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {
            "reset_code": code,
            "reset_expires": (now + timedelta(minutes=CODE_TTL_MINUTES)).isoformat(),
            "reset_attempts": 0,
            "reset_last_sent": now.isoformat(),
        }},
    )
    background_tasks.add_task(
        send_email,
        email,
        f"Código para restablecer tu contraseña: {code} — OnBuySolutions",
        _reset_email_html(user.get("name", ""), code),
    )
    return generic


@router.post("/reset-password")
async def reset_password(data: ResetPasswordInput):
    email = data.email.lower().strip()
    user = await db.users.find_one({"email": email})
    if not user or not user.get("reset_code"):
        raise HTTPException(status_code=400, detail="Código inválido o expirado. Solicita un nuevo código.")
    if user.get("reset_attempts", 0) >= MAX_CODE_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Demasiados intentos fallidos. Solicita un nuevo código.")
    expires = user.get("reset_expires")
    if not expires or datetime.fromisoformat(expires) < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="El código expiró. Solicita un nuevo código.")
    if not secrets.compare_digest(str(user["reset_code"]), data.code.strip()):
        await db.users.update_one({"_id": user["_id"]}, {"$inc": {"reset_attempts": 1}})
        raise HTTPException(status_code=400, detail="Código incorrecto. Verifica e intenta de nuevo.")

    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {
            "password_hash": hash_password(data.new_password),
            "password_changed_at": datetime.now(timezone.utc).isoformat(),
            "email_verified": True,
        },
         "$unset": {"reset_code": "", "reset_expires": "", "reset_attempts": "", "reset_last_sent": ""}},
    )
    await db.login_attempts.delete_many({"identifier": {"$regex": f":{email}$"}})
    logger.info(f"Contraseña restablecida: {email}")
    return {"message": "Contraseña actualizada correctamente. Ya puedes iniciar sesión."}


@router.post("/change-password")
async def change_password(data: ChangePasswordInput, user: dict = Depends(get_current_user)):
    full = await db.users.find_one({"_id": ObjectId(user["_id"])})
    if not verify_password(data.current_password, full["password_hash"]):
        raise HTTPException(status_code=401, detail="La contraseña actual es incorrecta")
    await db.users.update_one(
        {"_id": full["_id"]},
        {"$set": {
            "password_hash": hash_password(data.new_password),
            "password_changed_at": datetime.now(timezone.utc).isoformat(),
        }},
    )
    return {"message": "Contraseña actualizada correctamente"}
