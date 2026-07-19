from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import os
import logging

from motor.motor_asyncio import AsyncIOMotorClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("onbuysolutions")

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

UPLOAD_DIR = ROOT_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

SAMPLES_DIR = ROOT_DIR / "sample_files"

MAX_FILE_SIZE = 20 * 1024 * 1024

EXT_MIME = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".csv": "text/csv",
    ".txt": "text/plain",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
}

CATEGORY_LABELS = {
    "factura": "Factura / Comprobante de pago",
    "estado_cuenta": "Estado de cuenta bancario",
    "recibo": "Recibo de mantenimiento / cuotas",
    "contrato": "Contrato de servicios",
    "libro_actas": "Libro de actas / Acta de asamblea",
    "presupuesto": "Presupuesto / Balance",
    "clasificando": "Pendiente de clasificación",
    "otro": "Otro documento",
}

SAMPLE_META = {
    "estado_cuenta_enero_2025.pdf": {"category": "estado_cuenta", "description": "Estado de cuenta bancario del condominio (Enero 2025) con todos los movimientos del mes."},
    "factura_limpieza_E001-1234.pdf": {"category": "factura", "description": "Factura del servicio de limpieza de áreas comunes por S/ 1,850."},
    "factura_ascensores_E001-0456.pdf": {"category": "factura", "description": "Factura de mantenimiento de ascensores por S/ 2,200."},
    "factura_jardineria_E001-0789.pdf": {"category": "factura", "description": "Factura de jardinería y áreas verdes por S/ 950."},
    "recibos_mantenimiento_enero_2025.csv": {"category": "recibo", "description": "Detalle de cuotas de mantenimiento cobradas a los 30 departamentos."},
    "presupuesto_anual_2025.xlsx": {"category": "presupuesto", "description": "Presupuesto anual 2025 del condominio (egresos e ingresos)."},
}

SETTINGS_DEFAULTS = {
    "ai_model": "gemini-3.1-pro-preview",
    "price_small": 1100.0,
    "price_medium": 2100.0,
    "contact_email": "contacto@onbuysolutions.com",
    "empresa_razon_social": "OnBuySolutions S.A.C.",
    "empresa_ruc": "",
    "empresa_representante": "",
    "empresa_dni": "",
    "empresa_direccion": "",
    "empresa_ciudad": "Lima",
    "resend_sender": "onboarding@resend.dev",
    "complaints_notify_email": "onbuysolutions@gmail.com",
    "paypal_mode": "sandbox",
    "price_consulting": 30.0,
    "consulting_budget_usd": 3.5,
}


async def get_app_settings() -> dict:
    doc = await db.settings.find_one({"_id": "app"}) or {}
    merged = {**SETTINGS_DEFAULTS, **{k: v for k, v in doc.items() if k != "_id" and v not in (None, "")}}
    merged["llm_key"] = doc.get("llm_key") or os.environ.get("EMERGENT_LLM_KEY", "")
    merged["resend_api_key"] = doc.get("resend_api_key") or os.environ.get("RESEND_API_KEY", "")
    if not doc.get("resend_sender"):
        merged["resend_sender"] = os.environ.get("SENDER_EMAIL", SETTINGS_DEFAULTS["resend_sender"])
    if not doc.get("complaints_notify_email"):
        merged["complaints_notify_email"] = os.environ.get("COMPLAINTS_NOTIFY_EMAIL", SETTINGS_DEFAULTS["complaints_notify_email"])
    merged["paypal_client_id"] = doc.get("paypal_client_id") or os.environ.get("PAYPAL_CLIENT_ID", "")
    merged["paypal_secret"] = doc.get("paypal_secret") or os.environ.get("PAYPAL_SECRET", "")
    if not doc.get("paypal_mode"):
        merged["paypal_mode"] = os.environ.get("PAYPAL_MODE", SETTINGS_DEFAULTS["paypal_mode"])
    return merged
