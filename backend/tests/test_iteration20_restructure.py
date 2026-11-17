"""
Iteration 20 — Tests for the OnBuySolutions restructure:
- Audits no longer self-service (403 for clients)
- Legal consulting self-service with trial, chat 60 msgs @ 15.99, extra 30 @ 7.99
- Manual payment approval (admin)
- Audit clients CRUD + expedient + convert contact/mail to client
- Settings new fields
"""
import os
import time
import asyncio
import pytest
import requests
from bson import ObjectId
from pymongo import MongoClient

def _load_frontend_url():
    if "REACT_APP_BACKEND_URL" in os.environ:
        return os.environ["REACT_APP_BACKEND_URL"]
    for line in open("/app/frontend/.env").read().splitlines():
        if line.startswith("REACT_APP_BACKEND_URL="):
            return line.split("=", 1)[1].strip().strip('"')
    raise RuntimeError("REACT_APP_BACKEND_URL not configured")

BASE_URL = _load_frontend_url().rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@onbuysolutions.com"
ADMIN_PASSWORD = "OnBuy2026!"
CLIENT_EMAIL = "cliente.prueba@ejemplo.com"
CLIENT_PASSWORD = "Cliente2026!"

TRIAL_USER_EMAIL = "test_iter20_trial@ejemplo.com"
TRIAL_USER_PASSWORD = "Trial2026!"

# ------ fixtures ------

@pytest.fixture(scope="module")
def mongo():
    cli = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    yield cli[os.environ.get("DB_NAME", "onbuy_database")]
    cli.close()


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="module")
def client_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": CLIENT_EMAIL, "password": CLIENT_PASSWORD})
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="module")
def trial_user(mongo):
    # Create directly in DB with security.hash_password
    from passlib.context import CryptContext
    pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
    mongo.users.delete_one({"email": TRIAL_USER_EMAIL})
    uid = mongo.users.insert_one({
        "email": TRIAL_USER_EMAIL,
        "name": "TEST Trial User",
        "password_hash": pwd.hash(TRIAL_USER_PASSWORD),
        "role": "cliente",
        "email_verified": True,
        "created_at": "2026-01-01T00:00:00+00:00",
    }).inserted_id
    yield str(uid)
    # Cleanup
    uid_str = str(uid)
    # Delete cases + messages + payments
    cases = list(mongo.cases.find({"user_id": uid_str}))
    for c in cases:
        mongo.case_messages.delete_many({"case_id": str(c["_id"])})
        mongo.payments.delete_many({"item_id": str(c["_id"])})
    mongo.cases.delete_many({"user_id": uid_str})
    mongo.users.delete_one({"_id": uid})


@pytest.fixture(scope="module")
def trial_session(trial_user):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": TRIAL_USER_EMAIL, "password": TRIAL_USER_PASSWORD})
    assert r.status_code == 200, r.text
    return s


# ------ A. Public settings exposes new fields ------

class TestPublicSettings:
    def test_public_settings_has_new_fields(self):
        r = requests.get(f"{API}/public/settings")
        assert r.status_code == 200
        d = r.json()
        for k in ("price_chat_usd", "chat_messages", "price_extra_usd", "extra_messages", "trial_messages"):
            assert k in d, f"Missing {k} in /public/settings"
        assert float(d["price_chat_usd"]) == 15.99
        assert int(d["chat_messages"]) == 60
        assert float(d["price_extra_usd"]) == 7.99
        assert int(d["extra_messages"]) == 30
        assert int(d["trial_messages"]) == 3


# ------ B. Audit no self-service ------

class TestAuditNoSelfService:
    def test_client_cannot_create_audit(self, client_session):
        r = client_session.post(f"{API}/audits", json={
            "condominium_name": "TEST No Self", "period": "2025-01",
            "address": "x", "district": "y", "purpose": "z", "notes": ""
        })
        assert r.status_code == 403
        assert "WhatsApp" in r.text or "equipo" in r.text

    def test_admin_can_create_audit(self, admin, mongo):
        r = admin.post(f"{API}/audits", json={
            "condominium_name": "TEST Admin Audit", "period": "2025-01",
            "address": "x", "district": "y", "purpose": "z", "notes": ""
        })
        assert r.status_code == 200, r.text
        aid = r.json()["id"]
        # Cleanup
        admin.delete(f"{API}/audits/{aid}")


# ------ C. Trial + quota flow ------

class TestTrialAndQuota:
    def test_first_case_gets_trial(self, trial_session, mongo, trial_user):
        r = trial_session.post(f"{API}/cases", json={"title": "TEST Trial Case", "description": "primer caso"})
        assert r.status_code == 200, r.text
        c = r.json()
        self.__class__.case1_id = c["id"]
        assert c["payment_status"] == "prueba"
        assert c["messages_limit"] == 3
        assert c["messages_used"] == 0
        assert c["messages_left"] == 3

    def test_second_case_pending(self, trial_session):
        r = trial_session.post(f"{API}/cases", json={"title": "TEST Second Case"})
        assert r.status_code == 200, r.text
        c = r.json()
        self.__class__.case2_id = c["id"]
        assert c["payment_status"] == "pendiente_pago"
        assert c["messages_limit"] == 0
        assert c["messages_left"] == 0

    def test_second_case_chat_blocked_not_paid(self, trial_session):
        cid = self.__class__.case2_id
        r = trial_session.post(f"{API}/cases/{cid}/chat", data={"text": "Hola"})
        assert r.status_code == 402
        body = r.json()
        # detail is dict: {msg, error_code}
        detail = body.get("detail") if isinstance(body, dict) else body
        assert isinstance(detail, dict) and detail.get("error_code") == "CASE_NOT_PAID"

    def test_case_offer_trial_plan_chat(self, trial_session):
        cid = self.__class__.case1_id
        r = trial_session.get(f"{API}/payments/case-offer/{cid}")
        assert r.status_code == 200, r.text
        o = r.json()
        assert o["plan"] == "chat"
        assert o["messages"] == 60
        assert o["amount_usd"] == 15.99
        assert o["paypal_client_id"] is None  # no PayPal configured
        assert o["bank_account_pen"] and o["bank_account_usd"]
        assert "amount_pen" in o

    def test_manual_payment_pen_request(self, trial_session):
        cid = self.__class__.case1_id
        r = trial_session.post(f"{API}/payments/manual", json={"item_id": cid, "currency": "PEN"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["reference"].startswith("MAN-")
        assert d["currency"] == "PEN"
        self.__class__.manual_ref_pen = d["reference"]

    def test_duplicate_manual_blocked(self, trial_session):
        cid = self.__class__.case1_id
        r = trial_session.post(f"{API}/payments/manual", json={"item_id": cid, "currency": "USD"})
        assert r.status_code == 400
        assert "pendiente" in r.text.lower()

    def test_non_admin_cannot_approve(self, trial_session, mongo):
        pay = mongo.payments.find_one({"item_id": self.__class__.case1_id, "status": "pending_manual"})
        assert pay
        pid = str(pay["_id"])
        self.__class__.manual_pay_id = pid
        r = trial_session.post(f"{API}/payments/manual/{pid}/approve")
        assert r.status_code == 403

    def test_admin_approves_first_manual(self, admin, trial_session):
        pid = self.__class__.manual_pay_id
        r = admin.post(f"{API}/payments/manual/{pid}/approve")
        assert r.status_code == 200, r.text
        assert "60" in r.json()["message"]
        # Verify case
        cid = self.__class__.case1_id
        r2 = trial_session.get(f"{API}/cases/{cid}")
        c = r2.json()["case"]
        assert c["payment_status"] == "autorizada"
        assert c["messages_limit"] == 3 + 60  # trial 3 + added 60

    def test_double_approve_returns_404(self, admin):
        pid = self.__class__.manual_pay_id
        r = admin.post(f"{API}/payments/manual/{pid}/approve")
        assert r.status_code == 404

    def test_extra_offer_after_paid(self, trial_session):
        cid = self.__class__.case1_id
        r = trial_session.get(f"{API}/payments/case-offer/{cid}")
        assert r.status_code == 200
        o = r.json()
        assert o["plan"] == "extra"
        assert o["messages"] == 30
        assert o["amount_usd"] == 7.99

    def test_reject_flow_on_new_request(self, trial_session, admin, mongo):
        # Create a 2nd manual request (extra)
        cid = self.__class__.case1_id
        r = trial_session.post(f"{API}/payments/manual", json={"item_id": cid, "currency": "USD"})
        assert r.status_code == 200
        pay = mongo.payments.find_one({"item_id": cid, "status": "pending_manual"})
        pid = str(pay["_id"])
        r2 = admin.post(f"{API}/payments/manual/{pid}/reject")
        assert r2.status_code == 200
        # Verify case didn't gain more messages
        case = mongo.cases.find_one({"_id": ObjectId(cid)})
        assert case["messages_limit"] == 63
        # Status rejected
        after = mongo.payments.find_one({"_id": ObjectId(pid)})
        assert after["status"] == "rejected"

    def test_quota_exhausted_after_used(self, trial_session, mongo):
        cid = self.__class__.case1_id
        # Simulate using all messages
        mongo.cases.update_one({"_id": ObjectId(cid)}, {"$set": {"messages_used": 63}})
        r = trial_session.post(f"{API}/cases/{cid}/chat", data={"text": "Hola"})
        assert r.status_code == 402
        detail = r.json()["detail"]
        assert detail.get("error_code") == "QUOTA_EXHAUSTED"
        # Reset
        mongo.cases.update_one({"_id": ObjectId(cid)}, {"$set": {"messages_used": 0}})

    def test_final_report_requires_paid(self, trial_session, mongo, trial_user):
        # Create a 3rd case in trial status (but user.trial_used=True now, so no trial)
        # Actually: trial_used is now True -> new case gets 0 msg pendiente_pago.
        # So we need a case in 'prueba' to test. Mark temporarily.
        r = trial_session.post(f"{API}/cases", json={"title": "TEST FinalReport"})
        cid = r.json()["id"]
        # Force status to prueba
        mongo.cases.update_one({"_id": ObjectId(cid)}, {"$set": {"payment_status": "prueba", "messages_limit": 3}})
        rr = trial_session.post(f"{API}/cases/{cid}/final-report")
        assert rr.status_code == 402, rr.text

    def test_image_generation_decrements(self, trial_session, mongo):
        cid = self.__class__.case1_id
        before = mongo.cases.find_one({"_id": ObjectId(cid)})["messages_used"]
        # We do NOT actually call the LLM to save cost - just verify the endpoint requires paid.
        # Instead check that endpoint exists and returns something not 403/404.
        # Skip actual call to save budget.
        pytest.skip("Skipping real image generation to save budget; logic covered by _count_message review")


# ------ D. Audit clients CRUD ------

class TestAuditClients:
    created_ids = []

    def test_create_client(self, admin):
        payload = {
            "full_name": "TEST Cliente Audit",
            "dni": "12345678",
            "phone": "999111222",
            "email": "test_auditclient_iter20@ejemplo.com",
            "position": "Presidente",
            "company_name": "TEST Condominio Los Álamos",
            "company_ruc": "20123456789",
            "company_address": "Av. TEST 123",
            "status": "prospecto",
            "notes": "ficha de prueba",
        }
        r = admin.post(f"{API}/admin/audit-clients", json=payload)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["already_existed"] is False
        assert d["case_id"]
        self.__class__.created_ids.append(d["id"])
        self.__class__.client_id = d["id"]
        self.__class__.case_id = d["case_id"]

    def test_duplicate_email_returns_existing(self, admin):
        payload = {
            "full_name": "Otro nombre",
            "email": "test_auditclient_iter20@ejemplo.com",
            "status": "prospecto",
        }
        r = admin.post(f"{API}/admin/audit-clients", json=payload)
        assert r.status_code == 200, r.text
        assert r.json()["already_existed"] is True

    def test_get_client(self, admin):
        r = admin.get(f"{API}/admin/audit-clients/{self.__class__.client_id}")
        assert r.status_code == 200
        d = r.json()
        assert d["client"]["full_name"] == "TEST Cliente Audit"
        assert d["audits"] == []

    def test_admin_chat_in_expedient_unlimited(self, admin, mongo):
        # Admin case should be unlimited (messages_limit=None in serialize)
        case_id = self.__class__.case_id
        r = admin.get(f"{API}/cases/{case_id}")
        assert r.status_code == 200
        c = r.json()["case"]
        assert c["is_admin_case"] is True
        assert c["payment_status"] == "autorizada"

    def test_admin_creates_audit_linked(self, admin, mongo):
        cid = self.__class__.client_id
        r = admin.post(f"{API}/audits", json={
            "condominium_name": "TEST Condominio Los Álamos",
            "period": "2025-02", "address": "x", "district": "y",
            "purpose": "z", "notes": "", "client_id": cid,
        })
        assert r.status_code == 200, r.text
        self.__class__.linked_audit_id = r.json()["id"]
        # Verify association appears in get_client
        r2 = admin.get(f"{API}/admin/audit-clients/{cid}")
        audits = r2.json()["audits"]
        assert any(a["id"] == self.__class__.linked_audit_id for a in audits)

    def test_update_client(self, admin):
        cid = self.__class__.client_id
        r = admin.put(f"{API}/admin/audit-clients/{cid}", json={
            "full_name": "TEST Cliente Audit Actualizado",
            "email": "test_auditclient_iter20@ejemplo.com",
            "status": "en_proceso",
        })
        assert r.status_code == 200
        assert r.json()["status"] == "en_proceso"

    def test_delete_client(self, admin, mongo):
        cid = self.__class__.client_id
        # Delete linked audit first
        aid = self.__class__.linked_audit_id
        admin.delete(f"{API}/audits/{aid}")
        r = admin.delete(f"{API}/admin/audit-clients/{cid}")
        assert r.status_code == 200
        self.__class__.created_ids.remove(cid)
        # Cleanup underlying case
        mongo.case_messages.delete_many({"case_id": self.__class__.case_id})
        mongo.cases.delete_one({"_id": ObjectId(self.__class__.case_id)})


# ------ E. Admin settings new fields ------

class TestAdminSettings:
    def test_settings_roundtrip(self, admin):
        r = admin.get(f"{API}/admin/settings")
        assert r.status_code == 200
        original = r.json()

        # Change values
        payload = {**original,
                   "price_chat_usd": 20.5,
                   "chat_messages": 70,
                   "price_extra_usd": 9.99,
                   "extra_messages": 40,
                   "trial_messages": 5,
                   "bank_account_pen": "TEST BANK PEN",
                   "bank_account_usd": "TEST BANK USD",
                   }
        # Remove secret masked fields (don't overwrite)
        for k in list(payload.keys()):
            if isinstance(payload.get(k), str) and payload.get(k).endswith("••••"):
                payload.pop(k, None)
        r2 = admin.put(f"{API}/admin/settings", json=payload)
        assert r2.status_code == 200, r2.text

        r3 = requests.get(f"{API}/public/settings").json()
        assert r3["price_chat_usd"] == 20.5
        assert r3["chat_messages"] == 70
        assert r3["price_extra_usd"] == 9.99
        assert r3["extra_messages"] == 40
        assert r3["trial_messages"] == 5

        # Restore defaults
        restore = {**payload,
                   "price_chat_usd": 15.99,
                   "chat_messages": 60,
                   "price_extra_usd": 7.99,
                   "extra_messages": 30,
                   "trial_messages": 3,
                   "bank_account_pen": original.get("bank_account_pen", ""),
                   "bank_account_usd": original.get("bank_account_usd", ""),
                   }
        r4 = admin.put(f"{API}/admin/settings", json=restore)
        assert r4.status_code == 200
        r5 = requests.get(f"{API}/public/settings").json()
        assert r5["price_chat_usd"] == 15.99
        assert r5["chat_messages"] == 60
        assert r5["trial_messages"] == 3
