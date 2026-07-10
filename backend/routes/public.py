from datetime import datetime, timezone

from fastapi import APIRouter

from core import db, get_app_settings
from models import ContactInput

router = APIRouter()


@router.post("/contact")
async def contact(data: ContactInput):
    doc = data.model_dump()
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    doc["read"] = False
    await db.contacts.insert_one(doc)
    return {"message": "Mensaje recibido. Te contactaremos pronto."}


@router.get("/public/settings")
async def public_settings():
    s = await get_app_settings()
    return {
        "price_small": s["price_small"],
        "price_medium": s["price_medium"],
        "contact_email": s["contact_email"],
    }


@router.get("/")
async def root():
    return {"message": "OnBuySolutions API", "status": "ok"}
