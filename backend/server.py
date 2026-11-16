from core import ROOT_DIR, db, client, logger, SAMPLES_DIR, UPLOAD_DIR, get_app_settings

import os
from datetime import datetime, timezone

from fastapi import FastAPI, APIRouter
from starlette.middleware.cors import CORSMiddleware

from security import hash_password, verify_password, get_current_user
from consulting import create_consulting_router
from routes.auth import router as auth_router
from routes.audits import router as audits_router
from routes.admin import router as admin_router
from routes.backup import router as backup_router
from routes.public import router as public_router
from routes.complaints import router as complaints_router
from routes.payments import router as payments_router
from routes.blog import router as blog_router, seed_blog
from routes.mail import router as mail_router

app = FastAPI(title="OnBuySolutions API")

api_router = APIRouter(prefix="/api")
api_router.include_router(auth_router)
api_router.include_router(audits_router)
api_router.include_router(admin_router)
api_router.include_router(backup_router)
api_router.include_router(public_router)
api_router.include_router(complaints_router)
api_router.include_router(payments_router)
api_router.include_router(blog_router)
api_router.include_router(mail_router)
api_router.include_router(create_consulting_router(db, get_current_user, get_app_settings, UPLOAD_DIR))
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.login_attempts.create_index("identifier")
    await db.audits.create_index("user_id")
    await db.documents.create_index("audit_id")
    await db.case_messages.create_index("case_id")
    await db.blog_posts.create_index("slug", unique=True)
    await seed_blog()
    await db.mail_messages.create_index("resend_id", unique=True, sparse=True)
    await db.mail_messages.create_index([("direction", 1), ("created_at", -1)])
    if not SAMPLES_DIR.exists() or not any(SAMPLES_DIR.iterdir()):
        from generate_samples import generate_all
        generate_all(SAMPLES_DIR)
        logger.info("Sample files generated")
    await db.audits.update_many(
        {"payment_status": {"$exists": False}},
        {"$set": {"payment_status": "autorizada"}},
    )
    await db.users.update_many(
        {"email_verified": {"$exists": False}},
        {"$set": {"email_verified": True}},
    )
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@onbuysolutions.com")
    admin_password = os.environ.get("ADMIN_PASSWORD", "OnBuy2026!")
    existing = await db.users.find_one({"email": admin_email})
    if existing is None:
        await db.users.insert_one({
            "email": admin_email,
            "password_hash": hash_password(admin_password),
            "name": "Administrador OnBuySolutions",
            "role": "admin",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.info("Admin user seeded")
    elif not existing.get("password_changed_at") and not verify_password(admin_password, existing["password_hash"]):
        await db.users.update_one({"email": admin_email}, {"$set": {"password_hash": hash_password(admin_password)}})


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
