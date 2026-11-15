import re
import uuid
import unicodedata
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from core import db, get_app_settings, logger
from models import BaseDocument
from security import get_current_user, require_admin
from ai_engine import build_chat
from gemini_chat import UserMessage, TextDelta, StreamDone

router = APIRouter()

BLOG_SERVICES = {
    "legal": {"name": "Asesoría legal y contable", "url": "/asesoria-legal"},
    "auditorias": {"name": "Auditorías con IA para condominios", "url": "/auditorias-condominios"},
    "restaurantes": {"name": "Menús digitales y páginas premium para restaurantes", "url": "https://www.gustoperuano.com"},
    "hoteles": {"name": "Menús digitales y páginas premium para hoteles", "url": "https://www.hotelesqr.com"},
    "tiendas": {"name": "Catálogos digitales QR para tiendas pequeñas", "url": "https://www.tiendafacilqr.com"},
}


class BlogPost(BaseDocument):
    title: str
    slug: str
    excerpt: str = ""
    content: str = ""
    service: str = "legal"
    cover_image: Optional[str] = None
    published: bool = False
    created_at: str
    updated_at: Optional[str] = None


class BlogInput(BaseModel):
    title: str = Field(min_length=3)
    excerpt: str = ""
    content: str = Field(min_length=10)
    service: str = "legal"
    cover_image: Optional[str] = None
    published: bool = False


class BlogGenerateInput(BaseModel):
    topic: str = Field(min_length=5)
    service: str = "legal"
    instructions: Optional[str] = None


def _slugify(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")[:80] or "articulo"


async def _unique_slug(title: str, exclude_id: Optional[str] = None) -> str:
    base = _slugify(title)
    slug, n = base, 2
    while True:
        found = await db.blog_posts.find_one({"slug": slug})
        if not found or str(found["_id"]) == exclude_id:
            return slug
        slug = f"{base}-{n}"
        n += 1


def _check_service(service: str):
    if service not in BLOG_SERVICES:
        raise HTTPException(status_code=400, detail="Servicio inválido")


def _summary(doc: dict) -> dict:
    post = BlogPost.from_mongo(doc).model_dump()
    post.pop("content")
    return post


@router.get("/blog")
async def list_published():
    docs = await db.blog_posts.find({"published": True}).sort("created_at", -1).to_list(200)
    return [_summary(d) for d in docs]


@router.get("/blog/{slug}")
async def get_post(slug: str):
    doc = await db.blog_posts.find_one({"slug": slug, "published": True})
    if not doc:
        raise HTTPException(status_code=404, detail="Artículo no encontrado")
    return BlogPost.from_mongo(doc).model_dump()


@router.get("/admin/blog")
async def admin_list(user: dict = Depends(get_current_user)):
    require_admin(user)
    docs = await db.blog_posts.find({}).sort("created_at", -1).to_list(500)
    return [BlogPost.from_mongo(d).model_dump() for d in docs]


@router.post("/admin/blog")
async def admin_create(data: BlogInput, user: dict = Depends(get_current_user)):
    require_admin(user)
    _check_service(data.service)
    post = BlogPost(
        **data.model_dump(),
        slug=await _unique_slug(data.title),
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    result = await db.blog_posts.insert_one(post.to_mongo())
    post.id = str(result.inserted_id)
    return post.model_dump()


@router.put("/admin/blog/{post_id}")
async def admin_update(post_id: str, data: BlogInput, user: dict = Depends(get_current_user)):
    require_admin(user)
    _check_service(data.service)
    updates = data.model_dump()
    updates["slug"] = await _unique_slug(data.title, exclude_id=post_id)
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.blog_posts.update_one({"_id": ObjectId(post_id)}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Artículo no encontrado")
    doc = await db.blog_posts.find_one({"_id": ObjectId(post_id)})
    return BlogPost.from_mongo(doc).model_dump()


@router.delete("/admin/blog/{post_id}")
async def admin_delete(post_id: str, user: dict = Depends(get_current_user)):
    require_admin(user)
    result = await db.blog_posts.delete_one({"_id": ObjectId(post_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Artículo no encontrado")
    return {"message": "Artículo eliminado"}


def _cta_block(service: str) -> str:
    svc = BLOG_SERVICES[service]
    return (
        "\n\n## Contrata este servicio hoy\n\n"
        f"¿Tienes un caso parecido? En OnBuySolutions podemos ayudarte ahora mismo. "
        f"**[Contrata {svc['name']} aquí]({svc['url']})** y empieza hoy.\n"
    )


def _blog_system_prompt(service: str) -> str:
    svc = BLOG_SERVICES[service]
    return f"""Eres el redactor de contenidos de OnBuySolutions, empresa peruana de servicios digitales. Escribes artículos de blog en español de Perú, cercanos, concretos y orientados a convertir lectores en clientes.

SERVICIO A PROMOCIONAR: {svc['name']}
ENLACE DIRECTO PARA CONTRATAR: {svc['url']}

REGLAS OBLIGATORIAS:
- El artículo SIEMPRE debe incluir al menos DOS enlaces Markdown directos al enlace para contratar ({svc['url']}): uno a mitad del artículo y otro en el cierre.
- Termina SIEMPRE con una sección "## Contrata este servicio hoy" con una llamada a la acción clara y el enlace Markdown a {svc['url']}.
- Usa exactamente esa URL en los enlaces, sin modificarla ni inventar otras URLs.
- Extensión: 600 a 900 palabras. Usa subtítulos (##), listas y párrafos cortos.
- Si relatas un caso, preséntalo como caso ilustrativo con nombres ficticios. No inventes cifras oficiales ni prometas resultados garantizados.
- Si mencionas normativa peruana, cítala con prudencia y aclara que la orientación es informativa.
- No uses emojis.

FORMATO DE SALIDA EXACTO (texto plano, sin bloques de código):
TITULO: <título atractivo del artículo>
RESUMEN: <resumen de 1 a 2 frases para la tarjeta del blog>

<contenido del artículo en Markdown, sin repetir el título>"""


@router.post("/admin/blog/generate")
async def admin_generate(data: BlogGenerateInput, user: dict = Depends(get_current_user)):
    require_admin(user)
    _check_service(data.service)
    cfg = await get_app_settings()
    chat = build_chat(cfg, session_id=f"blog-{uuid.uuid4().hex[:8]}", system_message=_blog_system_prompt(data.service))
    prompt = f"Escribe un artículo de blog sobre: {data.topic}"
    if data.instructions:
        prompt += f"\n\nIndicaciones adicionales: {data.instructions}"
    cta_url = BLOG_SERVICES[data.service]["url"]

    async def generate():
        chunks = []
        try:
            async for ev in chat.stream_message(UserMessage(text=prompt)):
                if isinstance(ev, TextDelta):
                    chunks.append(ev.content)
                    yield ev.content
                elif isinstance(ev, StreamDone):
                    break
        except Exception as e:
            logger.error(f"Error generando artículo: {e}")
            yield f"\n\n[ERROR_IA] {str(e)[:300]}"
            return
        if f"]({cta_url})" not in "".join(chunks):
            yield _cta_block(data.service)

    return StreamingResponse(generate(), media_type="text/plain; charset=utf-8", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


SAMPLE_POST = {
    "title": "Cómo pude desalojar inquilinos morosos con la ayuda de OnBuySolutions",
    "excerpt": "Caso ilustrativo: ocho meses sin cobrar el alquiler y un proceso que parecía imposible. Así se ordenó el expediente, se redactaron los documentos y se recuperó el departamento.",
    "service": "legal",
    "content": """> Artículo de ejemplo con datos ficticios. Los nombres y montos son ilustrativos.

Durante ocho meses, Rosa M. no recibió ni un sol por el departamento que alquilaba en Lima. Su inquilino dejó de pagar, dejó de contestar el teléfono y, cada vez que ella tocaba la puerta, la respuesta era la misma: "la próxima semana le deposito". La deuda ya superaba los S/ 14,000.

Rosa no sabía por dónde empezar. Tenía un contrato firmado, algunos vouchers y muchos mensajes de WhatsApp, pero ningún orden. Fue entonces cuando abrió su caso en [la asesoría legal y contable de OnBuySolutions](/asesoria-legal).

## El problema: tener la razón no basta

En un desalojo, el propietario casi siempre tiene la razón. Lo que suele faltar es **un expediente ordenado**:

- El contrato de arrendamiento y sus cláusulas clave (plazo, renta, cláusula de allanamiento futuro).
- La prueba de los meses impagos.
- Las comunicaciones formales de requerimiento de pago.
- Una estrategia clara: qué vía corresponde y qué documento se presenta primero.

Sin eso, los meses pasan y la deuda crece.

## Paso 1: subir los documentos y entender el caso

Rosa creó su cuenta, abrió un expediente y subió su contrato, los vouchers y las capturas de las conversaciones. En minutos recibió un análisis que le explicó, en lenguaje simple:

1. Qué cláusulas de su contrato la favorecían y cuáles tenían vacíos.
2. Cuánto se le debía exactamente, mes por mes.
3. Qué caminos existen en el Perú para recuperar un inmueble por falta de pago y qué requisitos pide cada uno.

## Paso 2: documentos listos para usar

Desde el mismo expediente se redactaron los documentos que necesitaba:

- **Carta notarial de requerimiento de pago y resolución de contrato**, lista para llevar a la notaría.
- **Liquidación de la deuda**, con el detalle de rentas impagas.
- **Borrador de la demanda de desalojo**, para que su abogado colegiado lo revise y presente.

Cada documento quedó guardado en la biblioteca del caso, descargable en PDF. Si tienes una situación parecida, puedes [abrir tu caso aquí](/asesoria-legal) y obtener los tuyos.

## Paso 3: seguimiento hasta el final

Lo que más valoró Rosa fue no perder el hilo. Cada novedad —la respuesta del inquilino, la constancia notarial, la fecha de la audiencia— se agregó al mismo expediente, y el sistema le indicaba el siguiente paso. Al cerrar el caso, descargó un informe final con todo lo actuado.

El resultado: el inquilino firmó un acuerdo de entrega del inmueble y un cronograma de pago antes de llegar a sentencia. Rosa recuperó su departamento.

## Lo que aprendimos de este caso

- **Actúa temprano.** Con dos meses impagos ya puedes enviar un requerimiento formal.
- **Documenta todo.** Vouchers, mensajes y cartas son tu prueba.
- **No improvises los escritos.** Un documento mal redactado puede costarte meses.

Esta orientación es informativa y no reemplaza el patrocinio de un abogado colegiado en un proceso judicial.

## Contrata este servicio hoy

¿Tienes un inquilino que no paga o un inmueble ocupado? No dejes que la deuda siga creciendo. **[Contrata la asesoría legal y contable de OnBuySolutions aquí](/asesoria-legal)** y empieza a ordenar tu caso hoy mismo.
""",
}


async def seed_blog():
    if await db.blog_posts.count_documents({}) > 0:
        return
    post = BlogPost(
        **SAMPLE_POST,
        slug=_slugify(SAMPLE_POST["title"]),
        published=True,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    await db.blog_posts.insert_one(post.to_mongo())
    logger.info("Artículo de ejemplo del blog creado")
