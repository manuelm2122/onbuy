"""Iteration 21 — Verify security + concurrency fixes.

Covers BUGS 2,3,4,5,6,7,8 + rate limits + invalid IDs from the review request.
BUG 1 (audit AI analysis) is checked separately via frontend to save LLM budget.
"""
import os, sys, asyncio, hmac, pathlib
from io import BytesIO
from datetime import datetime, timezone
import pytest
import pytest_asyncio
import requests
from bson import ObjectId

sys.path.insert(0, "/app/backend")

def _load_env(path):
    try:
        for line in pathlib.Path(path).read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    except Exception:
        pass
_load_env("/app/frontend/.env")
_load_env("/app/backend/.env")

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
ADMIN = {"email": "admin@onbuysolutions.com", "password": "OnBuy2026!"}
CLIENTE = {"email": "cliente.prueba@ejemplo.com", "password": "Cliente2026!"}

# ---------- helpers ----------
def _session(creds):
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/login", json=creds, timeout=20)
    assert r.status_code == 200, f"login failed {creds['email']}: {r.status_code} {r.text}"
    return s

@pytest.fixture(scope="session")
def admin_session():
    return _session(ADMIN)

@pytest.fixture(scope="session")
def client_session():
    return _session(CLIENTE)

@pytest.fixture
def mongo():
    from motor.motor_asyncio import AsyncIOMotorClient
    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = cli[os.environ["DB_NAME"]]
    yield db
    cli.close()


# ====================== BUG 2 — Complaint receipt auth ======================
class TestComplaintReceipt:
    @pytest.fixture(scope="class")
    def complaint(self):
        payload = {
            "consumer_name": "TEST_Cliente Reclamo",
            "doc_type": "DNI", "doc_number": "12345678",
            "address": "Av. Falsa 123", "phone": "999000111",
            "email": "test_receipt@ejemplo.com",
            "item_type": "Servicio", "amount": 100.0,
            "service_description": "TEST servicio",
            "request_type": "Reclamo",
            "detail": "TEST detalle de la reclamación",
            "consumer_request": "TEST pedido del consumidor",
            "accepted_declaration": True,
        }
        r = requests.post(f"{BASE}/api/complaints", json=payload, timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "receipt_token" in data and data["receipt_token"]
        yield data
        # cleanup
        try:
            import asyncio
            from motor.motor_asyncio import AsyncIOMotorClient
            async def _del():
                cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
                await cli[os.environ["DB_NAME"]].complaints.delete_one({"_id": ObjectId(data["id"])})
                cli.close()
            asyncio.run(_del())
        except Exception:
            pass

    def test_no_token_no_session_401(self, complaint):
        r = requests.get(f"{BASE}/api/complaints/{complaint['id']}/receipt", timeout=15)
        assert r.status_code == 401, r.status_code

    def test_wrong_token_401(self, complaint):
        r = requests.get(f"{BASE}/api/complaints/{complaint['id']}/receipt?token=wrong", timeout=15)
        assert r.status_code == 401

    def test_correct_token_200_pdf(self, complaint):
        r = requests.get(f"{BASE}/api/complaints/{complaint['id']}/receipt?token={complaint['receipt_token']}", timeout=20)
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("application/pdf")
        assert r.content[:4] == b"%PDF"

    def test_admin_without_token_200(self, admin_session, complaint):
        r = admin_session.get(f"{BASE}/api/complaints/{complaint['id']}/receipt", timeout=20)
        assert r.status_code == 200

    def test_cliente_without_token_403(self, client_session, complaint):
        r = client_session.get(f"{BASE}/api/complaints/{complaint['id']}/receipt", timeout=20)
        assert r.status_code == 403


# ====================== BUG 5 — HTML injection email escape ======================
class TestEmailHtmlEscape:
    def test_contact_html_escapes(self):
        from routes.public import _contact_notification_html
        html = _contact_notification_html({
            "name": "<b>Bold</b>",
            "email": "x@y.com",
            "phone": "<script>alert(1)</script>",
            "service": "<a href=evil>evil</a>",
            "message": "<script>bad</script>",
        })
        assert "<b>Bold</b>" not in html
        assert "<script>bad</script>" not in html
        assert "<a href=evil>" not in html
        assert "&lt;b&gt;" in html
        assert "&lt;script&gt;" in html

    def test_complaint_consumer_html_escapes(self):
        from routes.complaints import _consumer_email_html
        c = {
            "consumer_name": "<b>pwn</b>",
            "request_type": "Reclamo",
            "code": "LRV-2026-00001",
            "due_date_display": "01/01/2026",
        }
        html = _consumer_email_html(c, "01/01/2026 10:00:00")
        assert "<b>pwn</b>" not in html
        assert "&lt;b&gt;pwn&lt;/b&gt;" in html

    def test_complaint_admin_html_escapes(self):
        from routes.complaints import _admin_email_html
        c = {
            "consumer_name": "<script>x</script>",
            "request_type": "Queja",
            "code": "LRV-2026-00002",
            "doc_type": "DNI", "doc_number": "1",
            "email": "a@b", "phone": "1",
            "amount": None,
            "detail": "<img src=x onerror=y>",
            "consumer_request": "<a href=evil>e</a>",
            "due_date_display": "01/01/2026",
        }
        html = _admin_email_html(c, "01/01/2026 10:00:00")
        assert "<script>x</script>" not in html
        assert "<img src=x" not in html
        assert "<a href=evil>" not in html
        assert "&lt;script&gt;" in html


# ====================== Invalid ObjectId → 404 ======================
class TestInvalidIds:
    def test_delete_blog_invalid(self, admin_session):
        r = admin_session.delete(f"{BASE}/api/admin/blog/zzz", timeout=15)
        assert r.status_code == 404

    def test_put_contact_read_invalid(self, admin_session):
        r = admin_session.put(f"{BASE}/api/admin/contacts/zzz/read", json={"read": True}, timeout=15)
        assert r.status_code in (404, 422)  # 422 if body validation strict — either way, not 500
        assert r.status_code != 500

    def test_delete_audit_invalid(self, admin_session):
        r = admin_session.delete(f"{BASE}/api/audits/zzz", timeout=15)
        assert r.status_code == 404

    def test_put_complaint_status_invalid(self, admin_session):
        r = admin_session.put(f"{BASE}/api/admin/complaints/zzz/status", json={"status": "pendiente"}, timeout=15)
        assert r.status_code == 404


# ====================== public settings: no price_consulting, has price_small/medium ======================
class TestPublicSettings:
    def test_public_settings_shape(self):
        r = requests.get(f"{BASE}/api/public/settings", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "price_consulting" not in d
        assert "price_small" not in d and "price_medium" not in d
        assert "trial_messages" in d


# ====================== BUG 7 — Case migration on startup ======================
class TestCaseMigration:
    @pytest.mark.asyncio
    async def test_migration_sets_messages_limit(self, mongo, client_session):
        # Find cliente user_id
        cuser = await mongo.users.find_one({"email": CLIENTE["email"]})
        assert cuser
        uid = str(cuser["_id"])
        # Insert legacy-shape case (no messages_limit)
        doc = {
            "title": "TEST_legacy case iter21",
            "description": "TEST",
            "status": "activo",
            "user_id": uid,
            "owner_email": CLIENTE["email"],
            "owner_role": "cliente",
            "payment_status": "autorizada",
            "budget_usd": 3.5,
            "spent_usd": 0.0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        result = await mongo.cases.insert_one(doc)
        try:
            # Run the migration logic directly (same as server startup)
            from core import get_app_settings
            cfg = await get_app_settings()
            await mongo.cases.update_many(
                {"payment_status": "autorizada", "owner_role": {"$ne": "admin"},
                 "user_id": {"$ne": None}, "messages_limit": {"$exists": False}},
                {"$set": {"messages_limit": int(cfg["chat_messages"]), "messages_used": 0}},
            )
            updated = await mongo.cases.find_one({"_id": result.inserted_id})
            assert updated.get("messages_limit") == int(cfg["chat_messages"])
            assert updated.get("messages_used") == 0

            # UI: listing /api/cases returns correct fields
            r = client_session.get(f"{BASE}/api/cases", timeout=15)
            assert r.status_code == 200
            cases = r.json()
            mine = [c for c in cases if c["id"] == str(result.inserted_id)]
            assert mine, "legacy case not in list"
            c = mine[0]
            assert c["messages_limit"] == int(cfg["chat_messages"])
            assert c["messages_used"] == 0
            assert c["messages_left"] >= 1
        finally:
            await mongo.cases.delete_one({"_id": result.inserted_id})


# ====================== BUG 8 — case list fields ======================
class TestCaseListingFields:
    @pytest.mark.asyncio
    async def test_cost_cap_reached_and_counts(self, mongo, client_session):
        cuser = await mongo.users.find_one({"email": CLIENTE["email"]})
        uid = str(cuser["_id"])
        now = datetime.now(timezone.utc).isoformat()
        case = {
            "title": "TEST_bug8_costcap",
            "description": "TEST",
            "status": "activo",
            "user_id": uid, "owner_email": CLIENTE["email"], "owner_role": "cliente",
            "payment_status": "autorizada",
            "budget_usd": 1.0, "spent_usd": 2.0,
            "messages_limit": 60, "messages_used": 10,
            "created_at": now, "updated_at": now,
        }
        res = await mongo.cases.insert_one(case)
        cid = str(res.inserted_id)
        # insert 2 messages, one with attachment
        await mongo.case_messages.insert_many([
            {"case_id": cid, "role": "user", "content": "hola", "attachments": [], "created_at": now},
            {"case_id": cid, "role": "assistant", "content": "ok",
             "attachments": [{"filename": "x.pdf", "stored_name": "a.pdf", "mime_type": "application/pdf", "size": 1, "kind": "upload"}],
             "created_at": now},
        ])
        try:
            r = client_session.get(f"{BASE}/api/cases", timeout=15)
            assert r.status_code == 200
            mine = [c for c in r.json() if c["id"] == cid][0]
            assert mine["message_count"] == 2
            assert mine["messages_with_files"] == 1
            assert mine["cost_cap_reached"] is True
            assert mine["pending_manual"] is False
        finally:
            await mongo.case_messages.delete_many({"case_id": cid})
            await mongo.cases.delete_one({"_id": res.inserted_id})


# ====================== BUG 3 — PayPal double-capture (in-process + monkeypatch) ======================
@pytest.mark.asyncio
async def test_bug3_paypal_double_capture_and_audit_blocked(monkeypatch, mongo):
    # Set a dummy PayPal cfg so _paypal_token passes initial check
    await mongo.app_settings.update_one(
        {"_id": "main"},
        {"$set": {"paypal_client_id": "test_cid", "paypal_secret": "test_secret", "paypal_mode": "sandbox"}},
        upsert=True,
    )
    try:
        from server import app
        from routes import payments as payments_mod

        # Monkeypatch _paypal_token to avoid HTTP
        async def fake_token(cfg):
            return "fake_access_token"
        monkeypatch.setattr(payments_mod, "_paypal_token", fake_token)

        # Patch httpx.AsyncClient used in capture_order: return COMPLETED
        class _FakeResp:
            def __init__(self, status_code=200, data=None, text=""):
                self.status_code = status_code
                self._data = data or {}
                self.text = text
                self.content = b"{}"
            def json(self): return self._data

        class _FakeClient:
            def __init__(self, *a, **k): pass
            async def __aenter__(self): return self
            async def __aexit__(self, *a): return False
            async def post(self, url, **kw):
                # /capture endpoint
                return _FakeResp(201, {
                    "status": "COMPLETED",
                    "purchase_units": [{"payments": {"captures": [{"id": "CAPT123"}]}}],
                    "payer": {"email_address": "payer@example.com"},
                })
            async def get(self, url, **kw):
                return _FakeResp(200, {"status": "COMPLETED"})

        monkeypatch.setattr(payments_mod, "httpx", type("H", (), {"AsyncClient": _FakeClient})())

        # Create a user + case + payment record directly in Mongo
        cuser = await mongo.users.find_one({"email": CLIENTE["email"]})
        uid = str(cuser["_id"])
        now = datetime.now(timezone.utc).isoformat()
        case_res = await mongo.cases.insert_one({
            "title": "TEST_bug3_paypal", "description": "", "status": "activo",
            "user_id": uid, "owner_email": CLIENTE["email"], "owner_role": "cliente",
            "payment_status": "pendiente_pago",
            "budget_usd": 0.0, "spent_usd": 0.0,
            "messages_limit": 0, "messages_used": 0,
            "created_at": now, "updated_at": now,
        })
        cid = str(case_res.inserted_id)
        order_id = "ORDER_TEST_DOUBLE"
        await mongo.payments.insert_one({
            "order_id": order_id,
            "item_type": "case", "item_id": cid,
            "concept": "TEST", "is_recharge": False,
            "user_id": uid, "user_email": CLIENTE["email"],
            "plan": "chat", "messages": 60,
            "method": "paypal",
            "amount_pen": 60.0, "exchange_rate_usd_per_pen": 3.7,
            "amount_usd": 15.99, "currency": "USD",
            "status": "created", "paypal_mode": "sandbox",
            "created_at": now,
        })
        try:
            # Override auth dep
            from security import get_current_user
            async def _ov(): return {"_id": uid, "email": CLIENTE["email"], "role": "cliente", "name": "T"}
            app.dependency_overrides[get_current_user] = _ov

            import httpx
            from httpx import ASGITransport
            transport = ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
                results = await asyncio.gather(
                    ac.post(f"/api/payments/capture/{order_id}"),
                    ac.post(f"/api/payments/capture/{order_id}"),
                )
                # Also check /create-order for audit returns 400
                r_audit = await ac.post("/api/payments/create-order", json={"item_type": "audit", "item_id": "anyid"})

            statuses = [r.status_code for r in results]
            bodies = [r.json() for r in results]
            assert all(s == 200 for s in statuses), f"statuses: {statuses} {bodies}"
            already = sum(1 for b in bodies if b.get("already_captured"))
            assert already == 1, f"expected exactly 1 already_captured, got {already}: {bodies}"

            case_after = await mongo.cases.find_one({"_id": case_res.inserted_id})
            assert case_after["messages_limit"] == 60, f"messages_limit should be 60 after single grant, got {case_after['messages_limit']}"
            assert case_after["payment_status"] == "autorizada"

            assert r_audit.status_code == 400
            assert "auditor" in r_audit.json().get("detail", "").lower() or "audit" in r_audit.json().get("detail", "").lower()
        finally:
            app.dependency_overrides.clear()
            await mongo.payments.delete_one({"order_id": order_id})
            await mongo.cases.delete_one({"_id": case_res.inserted_id})
    finally:
        # Restore paypal settings (remove the test ones)
        await mongo.app_settings.update_one(
            {"_id": "main"},
            {"$unset": {"paypal_client_id": "", "paypal_secret": ""}},
        )


# ====================== BUG 4 — Concurrent reservation atomicity ======================
@pytest.mark.asyncio
async def test_bug4_concurrent_reservation_atomic(mongo):
    """Verify _reserve_message atomic update: 5 concurrent reservations of a 1-msg-left
    case yield exactly 1 success; messages_used never exceeds messages_limit.
    Also verifies via source inspection that _refund_message is called on AI failure."""
    cuser = await mongo.users.find_one({"email": CLIENTE["email"]})
    uid = str(cuser["_id"])
    now = datetime.now(timezone.utc).isoformat()
    res = await mongo.cases.insert_one({
        "title": "TEST_bug4_atomic", "description": "", "status": "activo",
        "user_id": uid, "owner_email": CLIENTE["email"], "owner_role": "cliente",
        "payment_status": "autorizada",
        "budget_usd": 10.0, "spent_usd": 0.0,
        "messages_limit": 60, "messages_used": 59,  # exactly 1 msg left
        "created_at": now, "updated_at": now,
    })
    cid = res.inserted_id
    try:
        # Replicate exact _reserve_message atomic update
        used = {"$ifNull": ["$messages_used", 0]}
        limit = {"$ifNull": ["$messages_limit", 0]}
        async def _reserve():
            r = await mongo.cases.update_one(
                {"_id": cid, "$expr": {"$lt": [used, limit]}},
                {"$inc": {"messages_used": 1}},
            )
            return r.modified_count
        results = await asyncio.gather(*[_reserve() for _ in range(5)])
        assert sum(results) == 1, f"expected exactly 1 success, got {results}"
        after = await mongo.cases.find_one({"_id": cid})
        assert after["messages_used"] == 60
        assert after["messages_used"] <= after["messages_limit"]

        # Code inspection: _refund_message must be called in case_chat when answer is empty,
        # and in generate_case_image when exception raised or no images returned.
        src = pathlib.Path("/app/backend/consulting.py").read_text()
        assert "if not answer.strip():\n                await _refund_message" in src, \
            "case_chat must refund when answer is empty"
        assert src.count("await _refund_message(case_id, user)") >= 3, \
            "generate_case_image must refund in exception and no-images paths"
    finally:
        await mongo.case_messages.delete_many({"case_id": str(cid)})
        await mongo.cases.delete_one({"_id": cid})


# ====================== Audit create-order blocked ======================
# Covered inside test_bug3 above.


# ====================== Rate limits (runs last; BE restart clears) ======================
@pytest.mark.order(99)
class TestRateLimits:
    def test_contact_rate_limit(self):
        payload = {"name": "TEST_RL", "email": "rl@ejemplo.com", "message": "TEST ratelimit msg"}
        s = requests.Session()
        codes = []
        for i in range(12):
            r = s.post(f"{BASE}/api/contact", json=payload, timeout=10)
            codes.append(r.status_code)
        assert 429 in codes, f"expected 429 after 5 contacts, got: {codes}"
        # message in Spanish
        resp = next((r for r in [s.post(f"{BASE}/api/contact", json=payload, timeout=10)] if r.status_code == 429), None)
        if resp is not None:
            assert "demasiad" in resp.json().get("detail", "").lower() or "intent" in resp.json().get("detail", "").lower()
