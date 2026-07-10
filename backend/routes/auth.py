from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request, Response

from core import db
from models import RegisterInput, LoginInput, ChangePasswordInput
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

router = APIRouter(prefix="/auth")


@router.post("/register")
async def register(data: RegisterInput, response: Response):
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
        "created_at": datetime.now(timezone.utc).isoformat(),
        "accepted_terms_at": datetime.now(timezone.utc).isoformat(),
    }
    result = await db.users.insert_one(doc)
    user_id = str(result.inserted_id)
    set_auth_cookies(response, create_access_token(user_id, email), create_refresh_token(user_id))
    return {"id": user_id, "email": email, "name": doc["name"], "role": "cliente"}


@router.post("/login")
async def login(data: LoginInput, request: Request, response: Response):
    email = data.email.lower().strip()
    ip = request.client.host if request.client else "unknown"
    identifier = f"{ip}:{email}"
    await check_brute_force(identifier)
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(data.password, user["password_hash"]):
        await record_failed_attempt(identifier)
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos")
    await db.login_attempts.delete_one({"identifier": identifier})
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
