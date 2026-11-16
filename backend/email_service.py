import base64
import asyncio

import resend

from core import get_app_settings, logger


async def send_email(to: str, subject: str, html: str, pdf_bytes: bytes = None, pdf_filename: str = None, reply_to: str = None) -> dict:
    cfg = await get_app_settings()
    api_key = cfg.get("resend_api_key")
    if not api_key:
        logger.warning("Resend API key no configurada; email no enviado")
        return {"status": "skipped", "reason": "sin_api_key"}
    resend.api_key = api_key
    params = {
        "from": f"OnBuySolutions <{cfg['resend_sender']}>",
        "to": [to],
        "subject": subject,
        "html": html,
    }
    if reply_to:
        params["reply_to"] = [reply_to]
    if pdf_bytes:
        params["attachments"] = [{
            "filename": pdf_filename or "documento.pdf",
            "content": base64.b64encode(pdf_bytes).decode("ascii"),
        }]
    try:
        result = await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"Email enviado a {to}: {result.get('id')}")
        return {"status": "sent", "email_id": result.get("id")}
    except Exception as e:
        logger.error(f"Error enviando email a {to}: {e}")
        return {"status": "failed", "reason": str(e)}
