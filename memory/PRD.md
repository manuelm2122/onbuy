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
- [x] Testing e2e: 14/14 backend, frontend 100% (iteration_1.json)

## Estado conocido
- ⚠️ La Emergent LLM Key tiene saldo 0: el análisis IA devuelve error controlado hasta que el usuario recargue (Perfil → Universal Key → Add Balance). Todo lo demás verificado.

## Backlog priorizado
- P0: Verificar análisis IA real end-to-end cuando haya saldo en la clave
- P1: Vista/descarga de documentos subidos; historial de análisis por auditoría; forgot/reset password UI
- P1: Panel admin (ver mensajes de contacto, todos los usuarios/auditorías)
- P2: Notificaciones por email al completar auditoría (Resend/SendGrid); firma digital del PDF; multi-idioma; pagos (suscripción por auditoría con Stripe/Culqi)
