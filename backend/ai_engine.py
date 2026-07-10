import re
import json
import uuid
from pathlib import Path
from typing import List

from bson import ObjectId

from emergentintegrations.llm.chat import LlmChat, UserMessage, FileContentWithMimeType, TextDelta, StreamDone

from core import db, get_app_settings, logger

VALID_CATEGORIES = {"factura", "estado_cuenta", "recibo", "contrato", "libro_actas", "presupuesto", "otro"}

AUDIT_SYSTEM_PROMPT = """Eres un auditor financiero senior colegiado, especializado en auditorías de condominios, edificios multifamiliares y juntas de propietarios en el Perú. Dominas el marco legal peruano aplicable: Ley N° 27157 (Ley de Regularización de Edificaciones, Propiedad Exclusiva y Propiedad Común), su Reglamento (TUO aprobado por D.S. N° 035-2006-VIVIENDA), el Código Civil peruano, las Normas Internacionales de Auditoría (NIA) y las buenas prácticas contables aplicables a juntas de propietarios.

Tu tarea es realizar una auditoría exhaustiva y profesional de los documentos financieros proporcionados (facturas, estados de cuenta bancarios, recibos, presupuestos, actas, contratos, etc.).

REGLAS ESTRICTAS:
- Redacta SIEMPRE en español formal profesional.
- Cita montos exactos en Soles (S/) o la moneda que aparezca en los documentos.
- Cruza información entre documentos: verifica que los egresos en estados de cuenta tengan sustento en facturas/recibos, detecta duplicados, montos inconsistentes, pagos sin sustento, retiros inusuales.
- Cada hallazgo debe indicar severidad: [ALTA], [MEDIA] o [BAJA], el documento fuente y el monto involucrado.
- Si no puedes verificar algo por falta de documentación, indícalo explícitamente como limitación al alcance.
- NO inventes datos que no estén en los documentos.
- Si citas el Reglamento de la Ley N° 29733, cita el D.S. N° 016-2024-JUS (vigente desde el 30 de marzo de 2025, que derogó el D.S. N° 003-2013-JUS).

ALERTAS AUTOMÁTICAS OBLIGATORIAS:
- Si en el cruce documentario NO encuentras recibos de servicios públicos regulados de las áreas comunes (luz, agua, gas) o detectas meses sin pago verificable de dichos servicios, incluye de forma explícita en la sección 5 (HALLAZGOS Y OBSERVACIONES) la siguiente alerta textual: "**ALERTA:** Se identificó un patrón de omisión en el cruce de recibos de servicios públicos regulados, lo que genera riesgo de cortes de agua/luz en el mes siguiente."
- Siempre que en la sección 7 (RECOMENDACIONES) sugieras configuraciones bancarias (bloqueo de retiros en cajeros ATM, token dual, doble firma mancomunada, cambio de firmantes o similares), añade inmediatamente después la siguiente nota textual: "**Nota:** Esta configuración bancaria requiere que la Junta Directiva cuente con Vigencia de Poder inscrita en Sunarp."

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
Opinión profesional (limpia, con salvedades, adversa o abstención) debidamente fundamentada.

INSTRUCCIÓN FINAL OBLIGATORIA:
Después de la sección 8, agrega como ÚLTIMA línea del informe, en texto plano y sin negritas ni formato, exactamente:
DOCUMENTOS_FALTANTES: documento 1; documento 2; documento 3
listando de forma breve y concreta los documentos que faltaron para un análisis completo (ej.: "Recibos de luz y agua de áreas comunes del período; Contratos con proveedores; Estados de cuenta de marzo a junio"). Si la documentación estuvo razonablemente completa, escribe exactamente: DOCUMENTOS_FALTANTES: NINGUNO"""


async def prepare_file_contents(docs: List[dict]) -> List[FileContentWithMimeType]:
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


async def classify_uploaded_documents(doc_ids: List[str]):
    obj_ids = [ObjectId(i) for i in doc_ids]
    try:
        docs = await db.documents.find({"_id": {"$in": obj_ids}}).to_list(100)
        if not docs:
            return
        file_contents = await prepare_file_contents(docs)
        names = "\n".join(f"- {d['filename']}" for d in docs)
        prompt = (
            "Clasifica cada uno de los archivos adjuntos en UNA de estas categorías exactas: "
            "factura, estado_cuenta, recibo, contrato, libro_actas, presupuesto, otro.\n\n"
            f"Archivos adjuntos:\n{names}\n\n"
            'Responde ÚNICAMENTE un objeto JSON válido con el formato {"nombre_del_archivo": "categoria"}, '
            "sin texto adicional ni bloques de código."
        )
        cfg = await get_app_settings()
        chat = LlmChat(
            api_key=cfg["llm_key"],
            session_id=f"classify-{uuid.uuid4().hex[:8]}",
            system_message="Eres un clasificador de documentos financieros de condominios en Perú. Respondes únicamente JSON válido.",
        ).with_model("gemini", cfg["ai_model"])
        chunks = []
        async for ev in chat.stream_message(UserMessage(text=prompt, file_contents=file_contents)):
            if isinstance(ev, TextDelta):
                chunks.append(ev.content)
            elif isinstance(ev, StreamDone):
                break
        raw = "".join(chunks).strip()
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw).strip()
        mapping = json.loads(raw)
        for d in docs:
            cat = str(mapping.get(d["filename"], "otro")).strip()
            if cat not in VALID_CATEGORIES:
                cat = "otro"
            await db.documents.update_one({"_id": d["_id"]}, {"$set": {"category": cat}})
        logger.info(f"Clasificados {len(docs)} documentos automáticamente")
    except Exception as e:
        logger.error(f"Error clasificando documentos: {e}")
        await db.documents.update_many(
            {"_id": {"$in": obj_ids}, "category": "clasificando"},
            {"$set": {"category": "otro"}},
        )
