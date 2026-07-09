# PRD — OnBuySolutions: Auditorías de Condominios con IA

## Problema original
Sistema de auditorías a condominios en Perú usando la IA de Google más avanzada (Gemini 3.1 Pro). Subida de documentos (facturas, estados de cuenta, etc.), auditoría automática por IA, landing page de la empresa OnBuySolutions y generación de reporte final con valor legal.

## Decisiones del usuario
- IA: Gemini 3.1 Pro (gemini-3.1-pro-preview) vía Emergent LLM Key (Clave Universal)
- Auth: JWT email + contraseña (cookies httpOnly)
- Reporte: PDF descargable profesional/legal
- Formatos de documentos: PDF, imágenes, Excel/CSV

## Arquitectura
- **Backend**: FastAPI + MongoDB (motor). `/app/backend/server.py`
  - Auth JWT (bcrypt, cookies httpOnly, brute-force lockout 5 intentos/15 min, admin seed)
  - CRUD de auditorías (por usuario), subida multi-archivo (PDF/imagen/Excel/CSV, máx 20MB, xlsx→CSV con pandas)
  - Análisis IA: streaming (StreamingResponse) con emergentintegrations, Gemini 3.1 Pro con file attachments; prompt de auditor peruano (Ley 27157, D.S. 035-2006-VIVIENDA, NIA); informe con 8 secciones
  - Reporte PDF: reportlab, membrete, tabla de datos, parser de Markdown (títulos, tablas, listas, negritas), código de verificación, disclaimer legal
  - Dashboard stats, formulario de contacto
- **Frontend**: React + Tailwind + shadcn. Fuentes Outfit/IBM Plex Sans, tema Swiss navy/sky (#020617/#0284C7)
  - `Landing.jsx` (hero, cómo funciona, servicios, marco legal Perú, CTA, contacto, footer)
  - `AuthPage.jsx` (login/registro), `Panel.jsx` (tabs Resumen/Auditorías), `AuditDetail.jsx` (tabs Documentos/Análisis IA/Reporte, streaming en vivo con react-markdown)

## Personas
- Residente/propietario que sospecha de las cuentas
- Administrador de condominio que necesita transparencia
- Junta de propietarios que requiere informe con sustento legal

## Implementado (2026-06)
- [x] Landing page completa en español (diseño Swiss & High-Contrast)
- [x] Auth JWT completa + admin seed (credenciales en /app/memory/test_credentials.md)
- [x] CRUD auditorías + subida/eliminación de documentos por categoría
- [x] Análisis IA con streaming en vivo (Gemini 3.1 Pro)
- [x] Reporte PDF profesional descargable
- [x] Dashboard con estadísticas + formulario de contacto
- [x] Pestaña "Archivos de ejemplo" en el panel (2026-06): 6 documentos ficticios generados con IA (estado de cuenta PDF, 3 facturas PDF, recibos CSV, presupuesto XLSX) del "Condominio Los Álamos, Enero 2025" con irregularidades plantadas (pago duplicado S/ 950, retiro ATM S/ 3,000 sin sustento, factura S/ 2,200 vs cargo S/ 2,400) para probar el flujo completo. Endpoints /api/samples y /api/samples/{filename}; generador en /app/backend/generate_samples.py (auto-genera en startup si el dir está vacío)
- [x] Cumplimiento legal peruano (2026-06): páginas /terminos, /privacidad y /uso-ia (LegalPage.jsx) basadas en investigación web — Ley 29733 + D.S. 016-2024-JUS (ARCO, ANPD, brechas 48h, flujo transfronterizo, encargado de tratamiento), Ley 31814 + D.S. 115-2025-PCM (riesgo aceptable, transparencia algorítmica, human in the loop), secreto bancario (no scraping, entrega voluntaria), no entidad financiera SBS/SMV. Checkbox de consentimiento obligatorio en registro (backend valida accepted_terms y guarda accepted_terms_at como evidencia demostrable), enlaces en footer, aviso de transparencia en pestaña Análisis IA, disclaimer legal ampliado en el PDF
- [x] Sección de precios en landing (2026-06): #precios con 2 planes — pequeño <50 dptos S/ 1,100/año auditado; mediano-grande 50-150 dptos S/ 2,100/año auditado (destacado); nota de cotización personalizada >150 dptos; enlace "Precios" en nav
- [x] Generador de documentos admin (2026-06): pestaña "Documentos" (solo rol admin) en el panel; formulario con datos de empresa/cliente/servicio y genera 6 PDFs listos para firmar: propuesta comercial, contrato de servicios, NDA, acuerdo de encargo de tratamiento de datos (Ley 29733), autorización de entrega de información bancaria (secreto bancario) y recibo de pago (con monto en letras). Backend: /app/backend/documents_generator.py + POST /api/admin/documents/generate (403 no-admin); frontend: AdminDocGenerator.jsx. Campos vacíos → líneas en blanco para llenar a mano
- [x] Testing e2e: iteration_1 (14/14), iteration_2 (24/24), iteration_3 (25/25), iteration_4 (38/38) — todo 100%

## Estado conocido
- ⚠️ La Emergent LLM Key tiene saldo 0: el análisis IA devuelve error controlado hasta que el usuario recargue (Perfil → Universal Key → Add Balance). Todo lo demás verificado.

## Backlog priorizado
- P0: Verificar análisis IA real end-to-end cuando haya saldo en la clave
- P1: Vista/descarga de documentos subidos; historial de análisis por auditoría; forgot/reset password UI
- P1: Panel admin (ver mensajes de contacto, todos los usuarios/auditorías)
- P2: Notificaciones por email al completar auditoría (Resend/SendGrid); firma digital del PDF; multi-idioma; pagos (suscripción por auditoría con Stripe/Culqi)
