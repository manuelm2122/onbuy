"""Iteration 19: tests for /api/admin/mail* and /api/webhooks/resend (Resend)."""
import base64
import hashlib
import hmac
import json
import os
import time
import uuid

import pytest
import requests

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://proyecto-nuevo-10--3sst8oxb.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
INTERNAL = "http://localhost:8001/api"  # ingress blocks python-requests on webhook path for some flows

ADMIN_EMAIL = "admin@onbuysolutions.com"
ADMIN_PASS = "OnBuy2026!"

WEBHOOK_SECRET = "whsec_Y2xhdmUtZmljdGljaWEtZGUtcHJ1ZWJhLTEyMzQ1Ng=="
SEEDED_INBOUND_RESEND_ID = "test-inbound-001"


def _sign(secret: str, msg_id: str, timestamp: str, body: bytes) -> str:
    key = base64.b64decode(secret.split("_", 1)[1])
    signed = f"{msg_id}.{timestamp}.".encode() + body
    mac = base64.b64encode(hmac.new(key, signed, hashlib.sha256).digest()).decode()
    return f"v1,{mac}"


def _svix_headers(body: bytes, *, secret: str = WEBHOOK_SECRET, ts: int | None = None, msg_id: str | None = None,
                  signature: str | None = None):
    ts = ts if ts is not None else int(time.time())
    msg_id = msg_id or f"msg_{uuid.uuid4().hex[:12]}"
    sig = signature if signature is not None else _sign(secret, msg_id, str(ts), body)
    return {
        "svix-id": msg_id,
        "svix-timestamp": str(ts),
        "svix-signature": sig,
        "content-type": "application/json",
    }


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="module")
def created_mail_ids():
    return []


@pytest.fixture(scope="module", autouse=True)
def _cleanup(created_mail_ids):
    yield
    if not created_mail_ids:
        return
    s = requests.Session()
    s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
    for mid in created_mail_ids:
        s.delete(f"{API}/admin/mail/{mid}")


# ---------- webhook ----------
class TestWebhook:
    def _post(self, body: bytes, headers: dict):
        return requests.post(f"{INTERNAL}/webhooks/resend", data=body, headers=headers)

    def test_invalid_signature_returns_400(self):
        body = json.dumps({"type": "email.received", "data": {"email_id": "x"}}).encode()
        h = _svix_headers(body, signature="v1,bad")
        r = self._post(body, h)
        assert r.status_code == 400

    def test_old_timestamp_returns_400(self):
        body = json.dumps({"type": "email.received", "data": {"email_id": "x"}}).encode()
        h = _svix_headers(body, ts=int(time.time()) - 600)
        r = self._post(body, h)
        assert r.status_code == 400

    def test_missing_headers_returns_400(self):
        body = b"{}"
        r = self._post(body, {"content-type": "application/json"})
        assert r.status_code == 400

    def test_non_received_event_ok_no_insert(self, admin):
        rid = f"TEST_evt_{uuid.uuid4().hex[:8]}"
        body = json.dumps({"type": "email.delivered", "data": {"email_id": rid}}).encode()
        r = self._post(body, _svix_headers(body))
        assert r.status_code == 200
        # confirm no mail created
        lst = admin.get(f"{API}/admin/mail?folder=inbox").json()
        assert not any(m.get("resend_id") == rid for m in lst)

    def test_duplicate_email_id_not_duplicated(self, admin):
        # use seeded SEEDED_INBOUND_RESEND_ID -> should remain exactly 1
        body = json.dumps({
            "type": "email.received",
            "data": {"email_id": SEEDED_INBOUND_RESEND_ID, "from": "x@y.com", "to": ["contacto@onbuysolutions.com"],
                     "subject": "dup", "text": "dup"},
        }).encode()
        r = self._post(body, _svix_headers(body))
        assert r.status_code == 200
        time.sleep(1.5)
        lst = admin.get(f"{API}/admin/mail?folder=inbox").json()
        matches = [m for m in lst if m.get("resend_id") == SEEDED_INBOUND_RESEND_ID]
        assert len(matches) == 1

    def test_valid_received_creates_inbound_unread(self, admin, created_mail_ids):
        rid = f"TEST_inb_{uuid.uuid4().hex[:10]}"
        body = json.dumps({
            "type": "email.received",
            "data": {
                "email_id": rid,
                "from": "TEST_cliente@ejemplo.com",
                "to": ["contacto@onbuysolutions.com"],
                "subject": "TEST asunto webhook",
                "text": "hola, esto es prueba",
                "created_at": "2026-01-15T10:00:00Z",
            },
        }).encode()
        r = self._post(body, _svix_headers(body))
        assert r.status_code == 200
        time.sleep(1.5)
        lst = admin.get(f"{API}/admin/mail?folder=inbox").json()
        match = next((m for m in lst if m.get("resend_id") == rid), None)
        assert match is not None, "nuevo correo no fue creado"
        assert match["read"] is False
        assert match["subject"] == "TEST asunto webhook"
        # pending=True porque no hay API key de Resend
        assert match["content_pending"] is True
        created_mail_ids.append(match["id"])


# ---------- auth ----------
class TestMailAuth:
    def test_list_requires_session(self):
        r = requests.get(f"{API}/admin/mail")
        assert r.status_code == 401

    def test_meta_requires_session(self):
        r = requests.get(f"{API}/admin/mail/meta")
        assert r.status_code == 401

    def test_non_admin_forbidden(self):
        s = requests.Session()
        email = f"TEST_user_{uuid.uuid4().hex[:6]}@test.com"
        reg = s.post(f"{API}/auth/register",
                     json={"name": "User Test", "email": email, "password": "Pass123!", "accepted_terms": True})
        assert reg.status_code in (200, 201), reg.text
        # Force email verification via direct DB flip (new users need OTP otherwise)
        from pymongo import MongoClient
        mc = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
        users = mc[os.environ.get("DB_NAME", "onbuy_database")]["users"]
        res = users.update_one({"email": email.lower()}, {"$set": {"email_verified": True}})
        assert res.matched_count == 1
        lr = s.post(f"{API}/auth/login", json={"email": email, "password": "Pass123!"})
        assert lr.status_code == 200, lr.text
        r = s.get(f"{API}/admin/mail")
        assert r.status_code == 403
        r = s.get(f"{API}/admin/mail/meta")
        assert r.status_code == 403
        # cleanup
        users.delete_one({"email": email.lower()})


# ---------- meta / list / read / delete ----------
class TestMailCrud:
    def test_meta_returns_addresses_and_flags(self, admin):
        r = admin.get(f"{API}/admin/mail/meta")
        assert r.status_code == 200
        data = r.json()
        assert "contacto@onbuysolutions.com" in data["addresses"]
        assert "ventas@onbuysolutions.com" in data["addresses"]
        assert data["can_send"] is False  # no API key in this env
        assert data["can_receive"] is True
        assert data["unread"] >= 1

    def test_list_inbox_contains_seeded(self, admin):
        lst = admin.get(f"{API}/admin/mail?folder=inbox").json()
        assert any(m.get("resend_id") == SEEDED_INBOUND_RESEND_ID for m in lst)

    def test_open_marks_read_and_toggle_unread(self, admin):
        # create a fresh inbound through webhook
        rid = f"TEST_toggle_{uuid.uuid4().hex[:8]}"
        body = json.dumps({"type": "email.received", "data": {
            "email_id": rid, "from": "a@b.com", "to": ["contacto@onbuysolutions.com"],
            "subject": "toggle", "text": "x"}}).encode()
        requests.post(f"{INTERNAL}/webhooks/resend", data=body, headers=_svix_headers(body))
        time.sleep(1.2)
        lst = admin.get(f"{API}/admin/mail?folder=inbox").json()
        mid = next(m["id"] for m in lst if m.get("resend_id") == rid)

        got = admin.get(f"{API}/admin/mail/{mid}")
        assert got.status_code == 200
        assert got.json()["read"] is True

        r = admin.put(f"{API}/admin/mail/{mid}/read", json={"read": False})
        assert r.status_code == 200
        # verify DB state via list (GET /{id} would re-mark read=True)
        from pymongo import MongoClient
        from bson import ObjectId
        mc = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
        doc = mc[os.environ.get("DB_NAME", "onbuy_database")]["mail_messages"].find_one({"_id": ObjectId(mid)})
        assert doc["read"] is False

        # delete it (cleanup)
        d = admin.delete(f"{API}/admin/mail/{mid}")
        assert d.status_code == 200
        assert admin.get(f"{API}/admin/mail/{mid}").status_code == 404

    def test_get_mail_invalid_id_404(self, admin):
        assert admin.get(f"{API}/admin/mail/not-an-oid").status_code == 404


# ---------- send ----------
class TestMailSend:
    def test_send_without_api_key_returns_error(self, admin):
        r = admin.post(f"{API}/admin/mail/send", data={
            "from_address": "contacto@onbuysolutions.com",
            "to": "cliente@example.com",
            "subject": "TEST envío",
            "text": "hola",
        })
        assert r.status_code == 400
        assert "Resend" in r.json()["detail"]

    def test_send_from_not_in_list_returns_400(self, admin):
        r = admin.post(f"{API}/admin/mail/send", data={
            "from_address": "no-existe@onbuysolutions.com",
            "to": "cliente@example.com",
            "subject": "s",
            "text": "t",
        })
        assert r.status_code == 400
        assert "no está en la lista" in r.json()["detail"]

    def test_send_missing_to_returns_400(self, admin):
        r = admin.post(f"{API}/admin/mail/send", data={
            "from_address": "contacto@onbuysolutions.com",
            "to": "",
            "subject": "s",
            "text": "t",
        })
        # missing recipient OR empty recipient => 400 or 422 validation error
        assert r.status_code in (400, 422)

    def test_send_invalid_email_returns_400(self, admin):
        r = admin.post(f"{API}/admin/mail/send", data={
            "from_address": "contacto@onbuysolutions.com",
            "to": "no-es-un-email",
            "subject": "s",
            "text": "t",
        })
        assert r.status_code == 400
        assert "inválida" in r.json()["detail"].lower() or "invalida" in r.json()["detail"].lower()


# ---------- AI draft ----------
class TestAIDraft:
    def test_ai_draft_streams_text(self, admin):
        r = admin.post(f"{API}/admin/mail/ai-draft",
                       json={"instructions": "Propón una llamada breve esta semana para presentar menús QR"},
                       stream=True, timeout=60)
        assert r.status_code == 200
        chunks = []
        start = time.time()
        for chunk in r.iter_content(chunk_size=None):
            if chunk:
                chunks.append(chunk.decode("utf-8", errors="ignore"))
            if time.time() - start > 50:
                break
        text = "".join(chunks)
        assert len(text) > 20
        assert "[ERROR_IA]" not in text, f"IA devolvió error: {text[:400]}"


# ---------- settings ----------
class TestSettings:
    def test_settings_masks_secret(self, admin):
        r = admin.get(f"{API}/admin/settings")
        assert r.status_code == 200
        s = r.json()
        assert "resend_webhook_secret" not in s
        assert "resend_api_key" not in s
        assert "resend_webhook_secret_masked" in s
        # should not contain full base64 payload
        full = "Y2xhdmUtZmljdGljaWEtZGUtcHJ1ZWJhLTEyMzQ1Ng=="
        assert full not in (s.get("resend_webhook_secret_masked") or "")

    def test_mail_addresses_invalid_returns_400(self, admin):
        r = admin.put(f"{API}/admin/settings", json={"mail_addresses": "ok@a.com, no-es-un-email"})
        assert r.status_code == 400
        assert "inválida" in r.json()["detail"].lower() or "invalida" in r.json()["detail"].lower()

    def test_mail_addresses_valid_saved_and_preserved(self, admin):
        # get current then re-save identical to avoid touching real config
        current = admin.get(f"{API}/admin/settings").json()
        original = current.get("mail_addresses", "")
        r = admin.put(f"{API}/admin/settings", json={"mail_addresses": original})
        assert r.status_code == 200
        after = admin.get(f"{API}/admin/settings").json()
        assert after.get("mail_addresses") == original
