from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import os
import re
import uuid
import logging
import bcrypt
import jwt
from io import BytesIO
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Annotated

from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response, UploadFile, File, Form
from fastapi.responses import StreamingResponse, FileResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from pydantic import BaseModel, Field, ConfigDict, BeforeValidator, EmailStr

from emergentintegrations.llm.chat import LlmChat, UserMessage, FileContentWithMimeType, TextDelta, StreamDone

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors as rl_colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI(title="OnBuySolutions API")
api_router = APIRouter(prefix="/api")

UPLOAD_DIR = ROOT_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

SAMPLES_DIR = ROOT_DIR / "sample_files"

SAMPLE_META = {
    "estado_cuenta_enero_2025.pdf": {"category": "estado_cuenta", "description": "Estado de cuenta bancario del condominio (Enero 2025) con todos los movimientos del mes."},
    "factura_limpieza_E001-1234.pdf": {"category": "factura", "description": "Factura del servicio de limpieza de áreas comunes por S/ 1,850."},
    "factura_ascensores_E001-0456.pdf": {"category": "factura", "description": "Factura de mantenimiento de ascensores por S/ 2,200."},
    "factura_jardineria_E001-0789.pdf": {"category": "factura", "description": "Factura de jardinería y áreas verdes por S/ 950."},
    "recibos_mantenimiento_enero_2025.csv": {"category": "recibo", "description": "Detalle de cuotas de mantenimiento cobradas a los 30 departamentos."},
    "presupuesto_anual_2025.xlsx": {"category": "presupuesto", "description": "Presupuesto anual 2025 del condominio (egresos e ingresos)."},
}

JWT_ALGORITHM = "HS256"
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
    "otro": "Otro documento",
}

PyObjectId = Annotated[str, BeforeValidator(str)]


class BaseDocument(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    id: Optional[PyObjectId] = Field(default=None, alias="_id")

    def to_mongo(self) -> dict:
        d = self.model_dump(by_alias=True, exclude_none=True)
        d.pop("_id", None)
        return d

    @classmethod
    def from_mongo(cls, doc):
        return cls.model_validate(doc) if doc else None


class UserPublic(BaseDocument):
    email: str
    name: str
    role: str = "cliente"
    created_at: str


class RegisterInput(BaseModel):
    name: str = Field(min_length=2)
    email: EmailStr
    password: str = Field(min_length=6)
    accepted_terms: bool = False


class LoginInput(BaseModel):
    email: EmailStr
    password: str


class Audit(BaseDocument):
    user_id: str
    condominium_name: str
    address: Optional[str] = None
    district: Optional[str] = None
    period: str
    purpose: Optional[str] = None
    notes: Optional[str] = None
    status: str = "pendiente"
    analysis: Optional[str] = None
    analysis_date: Optional[str] = None
    created_at: str
    document_count: int = 0


class AuditCreate(BaseModel):
    condominium_name: str = Field(min_length=2)
    address: Optional[str] = None
    district: Optional[str] = None
    period: str = Field(min_length=2)
    purpose: Optional[str] = None
    notes: Optional[str] = None


class DocumentOut(BaseDocument):
    audit_id: str
    filename: str
    category: str
    mime_type: str
    size: int
    created_at: str


class ContactInput(BaseModel):
    name: str = Field(min_length=2)
    email: EmailStr
    phone: Optional[str] = None
    message: str = Field(min_length=5)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def get_jwt_secret() -> str:
    return os.environ["JWT_SECRET"]


def create_access_token(user_id: str, email: str) -> str:
    payload = {"sub": user_id, "email": email, "exp": datetime.now(timezone.utc) + timedelta(days=1), "type": "access"}
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    payload = {"sub": user_id, "exp": datetime.now(timezone.utc) + timedelta(days=7), "type": "refresh"}
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)


def set_auth_cookies(response: Response, access: str, refresh: str):
    response.set_cookie("access_token", access, httponly=True, secure=True, samesite="lax", max_age=86400, path="/")
    response.set_cookie("refresh_token", refresh, httponly=True, secure=True, samesite="lax", max_age=604800, path="/")


async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if not token:
        raise HTTPException(status_code=401, detail="No autenticado")
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Tipo de token inválido")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="Usuario no encontrado")
        user["_id"] = str(user["_id"])
        user.pop("password_hash", None)
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Sesión expirada")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")


async def check_brute_force(identifier: str):
    rec = await db.login_attempts.find_one({"identifier": identifier})
    if rec and rec.get("count", 0) >= 5:
        locked_at = datetime.fromisoformat(rec["last_attempt"])
        if datetime.now(timezone.utc) - locked_at < timedelta(minutes=15):
            raise HTTPException(status_code=429, detail="Demasiados intentos fallidos. Intenta en 15 minutos.")
        await db.login_attempts.delete_one({"identifier": identifier})


async def record_failed_attempt(identifier: str):
    await db.login_attempts.update_one(
        {"identifier": identifier},
        {"$inc": {"count": 1}, "$set": {"last_attempt": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )


# ---------- AUTH ----------

@api_router.post("/auth/register")
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


@api_router.post("/auth/login")
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


@api_router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"message": "Sesión cerrada"}


@api_router.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return {"id": user["_id"], "email": user["email"], "name": user["name"], "role": user.get("role", "cliente")}


# ---------- AUDITS ----------

@api_router.post("/audits", response_model=Audit, response_model_by_alias=False)
async def create_audit(data: AuditCreate, user: dict = Depends(get_current_user)):
    audit = Audit(
        user_id=user["_id"],
        condominium_name=data.condominium_name.strip(),
        address=data.address,
        district=data.district,
        period=data.period.strip(),
        purpose=data.purpose,
        notes=data.notes,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    result = await db.audits.insert_one(audit.to_mongo())
    audit.id = str(result.inserted_id)
    return audit


@api_router.get("/audits", response_model=List[Audit], response_model_by_alias=False)
async def list_audits(user: dict = Depends(get_current_user)):
    docs = await db.audits.find({"user_id": user["_id"]}).sort("created_at", -1).to_list(200)
    audits = [Audit.from_mongo(d) for d in docs]
    for a in audits:
        a.document_count = await db.documents.count_documents({"audit_id": a.id})
    return audits


@api_router.get("/audits/{audit_id}", response_model=Audit, response_model_by_alias=False)
async def get_audit(audit_id: str, user: dict = Depends(get_current_user)):
    doc = await db.audits.find_one({"_id": ObjectId(audit_id), "user_id": user["_id"]})
    if not doc:
        raise HTTPException(status_code=404, detail="Auditoría no encontrada")
    audit = Audit.from_mongo(doc)
    audit.document_count = await db.documents.count_documents({"audit_id": audit_id})
    return audit


@api_router.delete("/audits/{audit_id}")
async def delete_audit(audit_id: str, user: dict = Depends(get_current_user)):
    doc = await db.audits.find_one({"_id": ObjectId(audit_id), "user_id": user["_id"]})
    if not doc:
        raise HTTPException(status_code=404, detail="Auditoría no encontrada")
    docs = await db.documents.find({"audit_id": audit_id}).to_list(500)
    for d in docs:
        p = Path(d["stored_path"])
        if p.exists():
            p.unlink()
    await db.documents.delete_many({"audit_id": audit_id})
    await db.audits.delete_one({"_id": ObjectId(audit_id)})
    return {"message": "Auditoría eliminada"}


# ---------- DOCUMENTS ----------

@api_router.post("/audits/{audit_id}/documents", response_model=List[DocumentOut], response_model_by_alias=False)
async def upload_documents(
    audit_id: str,
    files: List[UploadFile] = File(...),
    category: str = Form("otro"),
    user: dict = Depends(get_current_user),
):
    audit = await db.audits.find_one({"_id": ObjectId(audit_id), "user_id": user["_id"]})
    if not audit:
        raise HTTPException(status_code=404, detail="Auditoría no encontrada")
    if category not in CATEGORY_LABELS:
        category = "otro"
    audit_dir = UPLOAD_DIR / audit_id
    audit_dir.mkdir(exist_ok=True)
    saved = []
    for f in files:
        ext = Path(f.filename).suffix.lower()
        if ext not in EXT_MIME:
            raise HTTPException(status_code=400, detail=f"Formato no soportado: {ext}. Usa PDF, imágenes, Excel o CSV.")
        content = await f.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail=f"El archivo {f.filename} supera los 20MB")
        stored_name = f"{uuid.uuid4().hex}{ext}"
        stored_path = audit_dir / stored_name
        stored_path.write_bytes(content)
        meta = {
            "audit_id": audit_id,
            "user_id": user["_id"],
            "filename": f.filename,
            "stored_path": str(stored_path),
            "mime_type": EXT_MIME[ext],
            "category": category,
            "size": len(content),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        result = await db.documents.insert_one(meta)
        meta["_id"] = result.inserted_id
        saved.append(DocumentOut.from_mongo(meta))
    return saved


@api_router.get("/audits/{audit_id}/documents", response_model=List[DocumentOut], response_model_by_alias=False)
async def list_documents(audit_id: str, user: dict = Depends(get_current_user)):
    docs = await db.documents.find({"audit_id": audit_id, "user_id": user["_id"]}).sort("created_at", -1).to_list(500)
    return [DocumentOut.from_mongo(d) for d in docs]


@api_router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, user: dict = Depends(get_current_user)):
    doc = await db.documents.find_one({"_id": ObjectId(doc_id), "user_id": user["_id"]})
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    p = Path(doc["stored_path"])
    if p.exists():
        p.unlink()
    await db.documents.delete_one({"_id": ObjectId(doc_id)})
    return {"message": "Documento eliminado"}


# ---------- AI ANALYSIS ----------

AUDIT_SYSTEM_PROMPT = """Eres un auditor financiero senior colegiado, especializado en auditorías de condominios, edificios multifamiliares y juntas de propietarios en el Perú. Dominas el marco legal peruano aplicable: Ley N° 27157 (Ley de Regularización de Edificaciones, Propiedad Exclusiva y Propiedad Común), su Reglamento (TUO aprobado por D.S. N° 035-2006-VIVIENDA), el Código Civil peruano, las Normas Internacionales de Auditoría (NIA) y las buenas prácticas contables aplicables a juntas de propietarios.

Tu tarea es realizar una auditoría exhaustiva y profesional de los documentos financieros proporcionados (facturas, estados de cuenta bancarios, recibos, presupuestos, actas, contratos, etc.).

REGLAS ESTRICTAS:
- Redacta SIEMPRE en español formal profesional.
- Cita montos exactos en Soles (S/) o la moneda que aparezca en los documentos.
- Cruza información entre documentos: verifica que los egresos en estados de cuenta tengan sustento en facturas/recibos, detecta duplicados, montos inconsistentes, pagos sin sustento, retiros inusuales.
- Cada hallazgo debe indicar severidad: [ALTA], [MEDIA] o [BAJA], el documento fuente y el monto involucrado.
- Si no puedes verificar algo por falta de documentación, indícalo explícitamente como limitación al alcance.
- NO inventes datos que no estén en los documentos.

ESTRUCTURA EXACTA DEL INFORME (usa Markdown):

## 1. RESUMEN EJECUTIVO
Síntesis del resultado de la auditoría, principales cifras y conclusión general en 2-3 párrafos.

## 2. ALCANCE Y OBJETIVOS
Período auditado, objetivos, marco legal aplicado y limitaciones al alcance.

## 3. DOCUMENTOS REVISADOS
Tabla Markdown con: Documento | Tipo | Período/Fecha | Observación breve.

## 4. ANÁLISIS FINANCIERO DETALLADO
Análisis de ingresos, egresos, saldos bancarios, conciliaciones. Incluye tablas de montos cuando sea posible.

## 5. HALLAZGOS Y OBSERVACIONES
Lista numerada. Cada hallazgo: **Hallazgo N° X [SEVERIDAD]** — descripción, documento fuente, monto, criterio incumplido.

## 6. POSIBLES IRREGULARIDADES
Operaciones sospechosas, inconsistencias graves o indicios que ameriten investigación adicional. Si no hay, indícalo expresamente.

## 7. RECOMENDACIONES
Lista numerada de acciones correctivas concretas para la junta de propietarios / administración.

## 8. CONCLUSIÓN Y OPINIÓN DEL AUDITOR
Opinión profesional (limpia, con salvedades, adversa o abstención) debidamente fundamentada."""


async def _prepare_file_contents(docs: List[dict]) -> List[FileContentWithMimeType]:
    import pandas as pd
    contents = []
    for d in docs:
        path = Path(d["stored_path"])
        if not path.exists():
            continue
        mime = d["mime_type"]
        if "spreadsheet" in mime or mime == "application/vnd.ms-excel":
            csv_path = path.with_suffix(".converted.csv")
            if not csv_path.exists():
                sheets = pd.read_excel(path, sheet_name=None)
                parts = []
                for name, df in sheets.items():
                    parts.append(f"--- Hoja: {name} ---\n{df.to_csv(index=False)}")
                csv_path.write_text("\n\n".join(parts), encoding="utf-8")
            contents.append(FileContentWithMimeType(file_path=str(csv_path), mime_type="text/csv"))
        else:
            contents.append(FileContentWithMimeType(file_path=str(path), mime_type=mime))
    return contents


@api_router.post("/audits/{audit_id}/analyze")
async def analyze_audit(audit_id: str, user: dict = Depends(get_current_user)):
    audit = await db.audits.find_one({"_id": ObjectId(audit_id), "user_id": user["_id"]})
    if not audit:
        raise HTTPException(status_code=404, detail="Auditoría no encontrada")
    docs = await db.documents.find({"audit_id": audit_id}).to_list(500)
    if not docs:
        raise HTTPException(status_code=400, detail="Sube al menos un documento antes de iniciar la auditoría")

    file_contents = await _prepare_file_contents(docs)
    if not file_contents:
        raise HTTPException(status_code=400, detail="No se pudieron procesar los documentos")

    doc_list = "\n".join(
        f"- {d['filename']} (Categoría: {CATEGORY_LABELS.get(d['category'], 'Otro')})" for d in docs
    )
    prompt = f"""Realiza la auditoría completa del siguiente condominio con base en los documentos adjuntos.

DATOS DE LA AUDITORÍA:
- Condominio: {audit['condominium_name']}
- Dirección: {audit.get('address') or 'No especificada'}, {audit.get('district') or ''}
- Período auditado: {audit['period']}
- Finalidad del informe: {audit.get('purpose') or 'Uso general de la junta de propietarios'}
- Notas del cliente: {audit.get('notes') or 'Ninguna'}

DOCUMENTOS ADJUNTOS ({len(docs)}):
{doc_list}

Genera el informe completo siguiendo la estructura exacta indicada."""

    chat = LlmChat(
        api_key=os.environ["EMERGENT_LLM_KEY"],
        session_id=f"audit-{audit_id}-{uuid.uuid4().hex[:8]}",
        system_message=AUDIT_SYSTEM_PROMPT,
    ).with_model("gemini", "gemini-3.1-pro-preview")

    await db.audits.update_one({"_id": ObjectId(audit_id)}, {"$set": {"status": "analizando"}})

    async def generate():
        chunks = []
        try:
            async for ev in chat.stream_message(UserMessage(text=prompt, file_contents=file_contents)):
                if isinstance(ev, TextDelta):
                    chunks.append(ev.content)
                    yield ev.content
                elif isinstance(ev, StreamDone):
                    break
            analysis = "".join(chunks)
            await db.audits.update_one(
                {"_id": ObjectId(audit_id)},
                {"$set": {
                    "analysis": analysis,
                    "status": "completada",
                    "analysis_date": datetime.now(timezone.utc).isoformat(),
                }},
            )
        except Exception as e:
            logger.error(f"Error en análisis IA: {e}")
            await db.audits.update_one({"_id": ObjectId(audit_id)}, {"$set": {"status": "error"}})
            yield f"\n\n[ERROR] No se pudo completar el análisis: {str(e)}"

    return StreamingResponse(
        generate(),
        media_type="text/plain; charset=utf-8",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------- PDF REPORT ----------

NAVY = rl_colors.HexColor("#0F172A")
SKY = rl_colors.HexColor("#0284C7")
GRAY = rl_colors.HexColor("#64748B")
LIGHT = rl_colors.HexColor("#F1F5F9")


def _md_inline(text: str) -> str:
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<i>\1</i>", text)
    return text


def _build_pdf(audit: dict, doc_count: int) -> bytes:
    buf = BytesIO()

    styles = {
        "title": ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=22, textColor=NAVY, spaceAfter=6, leading=26),
        "subtitle": ParagraphStyle("subtitle", fontName="Helvetica", fontSize=11, textColor=GRAY, spaceAfter=4),
        "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=14, textColor=NAVY, spaceBefore=16, spaceAfter=8),
        "h3": ParagraphStyle("h3", fontName="Helvetica-Bold", fontSize=12, textColor=SKY, spaceBefore=12, spaceAfter=6),
        "body": ParagraphStyle("body", fontName="Helvetica", fontSize=9.5, textColor=rl_colors.HexColor("#1E293B"), alignment=TA_JUSTIFY, leading=14, spaceAfter=6),
        "bullet": ParagraphStyle("bullet", fontName="Helvetica", fontSize=9.5, textColor=rl_colors.HexColor("#1E293B"), leading=14, leftIndent=14, spaceAfter=4),
        "cell": ParagraphStyle("cell", fontName="Helvetica", fontSize=8, textColor=rl_colors.HexColor("#1E293B"), leading=11),
        "cellh": ParagraphStyle("cellh", fontName="Helvetica-Bold", fontSize=8, textColor=rl_colors.white, leading=11),
        "legal": ParagraphStyle("legal", fontName="Helvetica-Oblique", fontSize=8, textColor=GRAY, alignment=TA_JUSTIFY, leading=11),
        "center": ParagraphStyle("center", fontName="Helvetica", fontSize=10, textColor=GRAY, alignment=TA_CENTER),
    }

    def on_page(canvas, doc_):
        canvas.saveState()
        canvas.setStrokeColor(SKY)
        canvas.setLineWidth(2)
        canvas.line(2 * cm, A4[1] - 1.3 * cm, A4[0] - 2 * cm, A4[1] - 1.3 * cm)
        canvas.setFont("Helvetica-Bold", 8)
        canvas.setFillColor(NAVY)
        canvas.drawString(2 * cm, A4[1] - 1.1 * cm, "ONBUYSOLUTIONS")
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(GRAY)
        canvas.drawRightString(A4[0] - 2 * cm, A4[1] - 1.1 * cm, "Informe de Auditoría de Condominio")
        canvas.setFont("Helvetica", 7)
        canvas.drawCentredString(A4[0] / 2, 1 * cm, f"OnBuySolutions — Documento generado con análisis de IA | Página {doc_.page}")
        canvas.restoreState()

    pdf = SimpleDocTemplate(buf, pagesize=A4, topMargin=2.2 * cm, bottomMargin=2 * cm, leftMargin=2 * cm, rightMargin=2 * cm)
    story = []

    story.append(Spacer(1, 8))
    story.append(Paragraph("INFORME DE AUDITORÍA", styles["title"]))
    story.append(Paragraph("Auditoría financiera de condominio asistida por Inteligencia Artificial", styles["subtitle"]))
    story.append(HRFlowable(width="100%", thickness=1, color=SKY, spaceAfter=12))

    issue_date = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    info_data = [
        [Paragraph("<b>Condominio</b>", styles["cell"]), Paragraph(_md_inline(audit["condominium_name"]), styles["cell"])],
        [Paragraph("<b>Dirección</b>", styles["cell"]), Paragraph(_md_inline(f"{audit.get('address') or 'No especificada'} {('— ' + audit['district']) if audit.get('district') else ''}"), styles["cell"])],
        [Paragraph("<b>Período auditado</b>", styles["cell"]), Paragraph(_md_inline(audit["period"]), styles["cell"])],
        [Paragraph("<b>Finalidad</b>", styles["cell"]), Paragraph(_md_inline(audit.get("purpose") or "Uso general de la junta de propietarios"), styles["cell"])],
        [Paragraph("<b>Documentos analizados</b>", styles["cell"]), Paragraph(str(doc_count), styles["cell"])],
        [Paragraph("<b>Fecha de emisión</b>", styles["cell"]), Paragraph(issue_date, styles["cell"])],
        [Paragraph("<b>Código de verificación</b>", styles["cell"]), Paragraph(str(audit["_id"]), styles["cell"])],
    ]
    info_table = Table(info_data, colWidths=[4.5 * cm, 12.5 * cm])
    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), LIGHT),
        ("GRID", (0, 0), (-1, -1), 0.5, rl_colors.HexColor("#CBD5E1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 16))

    lines = (audit.get("analysis") or "").split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line.strip():
            i += 1
            continue
        if line.startswith("|"):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i].strip())
                i += 1
            rows = []
            for tl in table_lines:
                cells = [c.strip() for c in tl.strip("|").split("|")]
                if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                    continue
                rows.append(cells)
            if rows:
                ncols = max(len(r) for r in rows)
                data = []
                for ridx, r in enumerate(rows):
                    r = r + [""] * (ncols - len(r))
                    style = styles["cellh"] if ridx == 0 else styles["cell"]
                    data.append([Paragraph(_md_inline(c), style) for c in r])
                col_w = 17.0 / ncols
                t = Table(data, colWidths=[col_w * cm] * ncols, repeatRows=1)
                t.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                    ("GRID", (0, 0), (-1, -1), 0.5, rl_colors.HexColor("#CBD5E1")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [rl_colors.white, LIGHT]),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]))
                story.append(t)
                story.append(Spacer(1, 8))
            continue
        stripped = line.strip()
        if stripped.startswith("### "):
            story.append(Paragraph(_md_inline(stripped[4:]), styles["h3"]))
        elif stripped.startswith("## "):
            story.append(Paragraph(_md_inline(stripped[3:]), styles["h2"]))
        elif stripped.startswith("# "):
            story.append(Paragraph(_md_inline(stripped[2:]), styles["h2"]))
        elif re.match(r"^[-*]\s+", stripped):
            story.append(Paragraph("•&nbsp;&nbsp;" + _md_inline(re.sub(r"^[-*]\s+", "", stripped)), styles["bullet"]))
        elif re.match(r"^\d+\.\s+", stripped):
            story.append(Paragraph(_md_inline(stripped), styles["bullet"]))
        else:
            story.append(Paragraph(_md_inline(stripped), styles["body"]))
        i += 1

    story.append(Spacer(1, 24))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY, spaceAfter=8))
    story.append(Paragraph(
        "Este informe ha sido elaborado por OnBuySolutions mediante un proceso de auditoría asistida por Inteligencia Artificial "
        "(Google Gemini) sobre la documentación proporcionada voluntariamente por el cliente. El análisis se realizó conforme al marco legal peruano "
        "aplicable a condominios y juntas de propietarios (Ley N° 27157 y su Reglamento, D.S. N° 035-2006-VIVIENDA). "
        "AVISO DE TRANSPARENCIA ALGORÍTMICA (Ley N° 31814 y D.S. N° 115-2025-PCM): el presente informe fue generado mediante algoritmos "
        "automatizados; el usuario humano (la Junta de Propietarios o administración) debe mantener la supervisión final y validar su contenido "
        "antes de utilizarlo para formular denuncias formales o iniciar procedimientos legales. No constituye una auditoría oficial practicada por "
        "auditor colegiado ni asesoría legal, contable o financiera. El tratamiento de los datos personales contenidos en la documentación se rige "
        "por la Ley N° 29733 y su Reglamento (D.S. N° 016-2024-JUS), actuando OnBuySolutions como encargado de tratamiento. "
        "El presente documento puede ser utilizado por el cliente para los fines que estime pertinentes, recomendándose su validación complementaria "
        "por un auditor colegiado. Código de verificación: " + str(audit["_id"]) + ".",
        styles["legal"],
    ))

    pdf.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return buf.getvalue()


@api_router.get("/audits/{audit_id}/report")
async def download_report(audit_id: str, user: dict = Depends(get_current_user)):
    audit = await db.audits.find_one({"_id": ObjectId(audit_id), "user_id": user["_id"]})
    if not audit:
        raise HTTPException(status_code=404, detail="Auditoría no encontrada")
    if not audit.get("analysis"):
        raise HTTPException(status_code=400, detail="Primero debes ejecutar el análisis con IA")
    doc_count = await db.documents.count_documents({"audit_id": audit_id})
    pdf_bytes = _build_pdf(audit, doc_count)
    safe_name = re.sub(r"[^\w\-]", "_", audit["condominium_name"])[:40]
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="Informe_Auditoria_{safe_name}.pdf"'},
    )


# ---------- DASHBOARD & CONTACT ----------

@api_router.get("/dashboard/stats")
async def dashboard_stats(user: dict = Depends(get_current_user)):
    uid = user["_id"]
    total = await db.audits.count_documents({"user_id": uid})
    completed = await db.audits.count_documents({"user_id": uid, "status": "completada"})
    pending = await db.audits.count_documents({"user_id": uid, "status": {"$in": ["pendiente", "analizando"]}})
    documents = await db.documents.count_documents({"user_id": uid})
    return {"total_audits": total, "completed": completed, "pending": pending, "documents": documents}


@api_router.post("/contact")
async def contact(data: ContactInput):
    doc = data.model_dump()
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    await db.contacts.insert_one(doc)
    return {"message": "Mensaje recibido. Te contactaremos pronto."}


# ---------- SAMPLE FILES ----------

@api_router.get("/samples")
async def list_samples(user: dict = Depends(get_current_user)):
    files = []
    if SAMPLES_DIR.exists():
        for f in sorted(SAMPLES_DIR.iterdir()):
            if f.is_file():
                meta = SAMPLE_META.get(f.name, {})
                files.append({
                    "filename": f.name,
                    "size": f.stat().st_size,
                    "category": meta.get("category", "otro"),
                    "description": meta.get("description", ""),
                })
    return files


@api_router.get("/samples/{filename}")
async def download_sample(filename: str, user: dict = Depends(get_current_user)):
    if "/" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Nombre inválido")
    path = SAMPLES_DIR / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(path, filename=filename)


@api_router.get("/")
async def root():
    return {"message": "OnBuySolutions API", "status": "ok"}


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
    if not SAMPLES_DIR.exists() or not any(SAMPLES_DIR.iterdir()):
        from generate_samples import generate_all
        generate_all(SAMPLES_DIR)
        logger.info("Sample files generated")
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
    elif not verify_password(admin_password, existing["password_hash"]):
        await db.users.update_one({"email": admin_email}, {"$set": {"password_hash": hash_password(admin_password)}})


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
