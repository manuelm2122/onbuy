"""
Iteration 15 — Paid consulting cases (client-owned) + PayPal recharge tests.
Constraints:
- Do NOT execute /chat with real text (LLM budget). Only test 402 gating.
- Do NOT delete existing case 6a5c91fe... or audit 6a57731f...
- Restore spent_usd=0.004054 at teardown if we set BUDGET_EXHAUSTED.
"""
import os
import io
import pytest
import requests
from pymongo import MongoClient
from bson import ObjectId

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")

ADMIN_EMAIL = "admin@onbuysolutions.com"
ADMIN_PASSWORD = "OnBuy2026!"
CLIENT_EMAIL = "otptest@test.com"
CLIENT_PASSWORD = "nuevapass456"

PAID_CASE_ID = "6a5c91fed9399e87ed31f537"          # Revisión contrato arrendamiento (paid, owned by client)
PENDING_AUDIT_ID = "6a57731f1ba8274ddfe93fd6"      # Condominio Test PayPal (pendiente_pago, client)
ORIGINAL_SPENT = 0.004054


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"login {email} failed: {r.status_code} {r.text[:200]}"
    return s


@pytest.fixture(scope="module")
def client_s():
    return _login(CLIENT_EMAIL, CLIENT_PASSWORD)


@pytest.fixture(scope="module")
def admin_s():
    return _login(ADMIN_EMAIL, ADMIN_PASSWORD)


@pytest.fixture(scope="module")
def mongo():
    c = MongoClient(MONGO_URL)
    yield c[DB_NAME]
    c.close()


CREATED_CLIENT_CASES = []
CREATED_ADMIN_CASES = []


@pytest.fixture(scope="module", autouse=True)
def _teardown(client_s, admin_s, mongo):
    yield
    for cid in CREATED_CLIENT_CASES:
        try:
            client_s.delete(f"{BASE_URL}/api/cases/{cid}", timeout=15)
        except Exception:
            pass
    for cid in CREATED_ADMIN_CASES:
        try:
            admin_s.delete(f"{BASE_URL}/api/cases/{cid}", timeout=15)
        except Exception:
            pass
    # Ensure spent restored
    mongo.cases.update_one({"_id": ObjectId(PAID_CASE_ID)}, {"$set": {"spent_usd": ORIGINAL_SPENT}})


# ============================================================
# CLIENT case creation & ownership
# ============================================================
class TestClientCases:
    def test_client_creates_case_pendiente(self, client_s):
        r = client_s.post(f"{BASE_URL}/api/cases",
                          json={"title": "TEST_iter15_client_case", "description": "prueba iter15"}, timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["payment_status"] == "pendiente_pago"
        assert d["budget_usd"] == 0.0
        assert d["spent_usd"] == 0.0
        assert d["owner_email"] == CLIENT_EMAIL
        assert d["is_admin_case"] is False
        CREATED_CLIENT_CASES.append(d["id"])

    def test_client_list_only_own(self, client_s):
        r = client_s.get(f"{BASE_URL}/api/cases", timeout=15)
        assert r.status_code == 200
        cases = r.json()
        assert isinstance(cases, list)
        # Every returned case must be owned by client and NOT be admin cases
        for c in cases:
            assert c["is_admin_case"] is False
            assert c["owner_email"] == CLIENT_EMAIL

    def test_client_cannot_get_foreign_case(self, client_s, admin_s):
        # create an admin case and try to fetch it as client → 404
        r = admin_s.post(f"{BASE_URL}/api/cases",
                         json={"title": "TEST_iter15_admin_case"}, timeout=15)
        assert r.status_code == 200, r.text
        admin_case_id = r.json()["id"]
        CREATED_ADMIN_CASES.append(admin_case_id)
        rr = client_s.get(f"{BASE_URL}/api/cases/{admin_case_id}", timeout=15)
        assert rr.status_code == 404

    def test_chat_on_unpaid_returns_402(self, client_s):
        cid = CREATED_CLIENT_CASES[0]
        r = client_s.post(f"{BASE_URL}/api/cases/{cid}/chat",
                          data={"text": "hola"}, timeout=20)
        assert r.status_code == 402, f"expected 402, got {r.status_code}: {r.text[:200]}"
        body = r.json()
        assert body["detail"]["error_code"] == "CASE_NOT_PAID"

    def test_generate_image_on_unpaid_returns_402(self, client_s):
        cid = CREATED_CLIENT_CASES[0]
        r = client_s.post(f"{BASE_URL}/api/cases/{cid}/generate-image",
                          json={"prompt": "diagrama"}, timeout=20)
        assert r.status_code == 402
        assert r.json()["detail"]["error_code"] == "CASE_NOT_PAID"

    def test_final_report_on_unpaid_returns_402(self, client_s):
        cid = CREATED_CLIENT_CASES[0]
        r = client_s.post(f"{BASE_URL}/api/cases/{cid}/final-report", timeout=20)
        assert r.status_code == 402
        assert r.json()["detail"]["error_code"] == "CASE_NOT_PAID"


# ============================================================
# BUDGET exhaustion 402
# ============================================================
class TestBudgetExhaustion:
    def test_budget_exhausted_402(self, client_s, mongo):
        # set spent above budget
        mongo.cases.update_one({"_id": ObjectId(PAID_CASE_ID)}, {"$set": {"spent_usd": 3.6}})
        try:
            r = client_s.post(f"{BASE_URL}/api/cases/{PAID_CASE_ID}/chat",
                              data={"text": "hola"}, timeout=20)
            assert r.status_code == 402
            assert r.json()["detail"]["error_code"] == "BUDGET_EXHAUSTED"
        finally:
            mongo.cases.update_one({"_id": ObjectId(PAID_CASE_ID)}, {"$set": {"spent_usd": ORIGINAL_SPENT}})


# ============================================================
# PAYMENTS: consulting quote + create-order (case) + regression audit
# ============================================================
class TestPayments:
    def test_quote_consulting(self, client_s):
        r = client_s.get(f"{BASE_URL}/api/payments/quote?plan=consulting", timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["plan"] == "consulting"
        assert d["amount_pen"] == 30
        # USD 8.83 ± 0.5 tolerance
        assert 7.5 < d["amount_usd"] < 10.5, f"amount_usd={d['amount_usd']} out of expected range"

    def test_create_order_case_pending(self, client_s):
        # create fresh pending case
        rc = client_s.post(f"{BASE_URL}/api/cases",
                           json={"title": "TEST_iter15_paycase"}, timeout=15)
        assert rc.status_code == 200
        cid = rc.json()["id"]
        CREATED_CLIENT_CASES.append(cid)
        r = client_s.post(f"{BASE_URL}/api/payments/create-order",
                          json={"item_type": "case", "item_id": cid, "plan": "consulting"}, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "order_id" in d and d["order_id"]
        assert d["amount_pen"] == 30

    def test_create_order_case_recharge_on_paid(self, client_s):
        r = client_s.post(f"{BASE_URL}/api/payments/create-order",
                          json={"item_type": "case", "item_id": PAID_CASE_ID, "plan": "consulting"}, timeout=30)
        assert r.status_code == 200, r.text
        assert r.json().get("order_id")

    def test_create_order_case_foreign_404(self, client_s, admin_s):
        # create admin case, then client tries to pay for it
        ra = admin_s.post(f"{BASE_URL}/api/cases", json={"title": "TEST_iter15_admin_foreign"}, timeout=15)
        assert ra.status_code == 200
        acid = ra.json()["id"]
        CREATED_ADMIN_CASES.append(acid)
        r = client_s.post(f"{BASE_URL}/api/payments/create-order",
                          json={"item_type": "case", "item_id": acid, "plan": "consulting"}, timeout=15)
        assert r.status_code == 404

    def test_create_order_invalid_item_type(self, client_s):
        r = client_s.post(f"{BASE_URL}/api/payments/create-order",
                          json={"item_type": "foo", "item_id": PAID_CASE_ID, "plan": "consulting"}, timeout=15)
        assert r.status_code in (400, 422), r.text

    def test_create_order_audit_regression(self, client_s):
        r = client_s.post(f"{BASE_URL}/api/payments/create-order",
                          json={"item_type": "audit", "item_id": PENDING_AUDIT_ID, "plan": "small"}, timeout=30)
        assert r.status_code == 200, r.text
        assert r.json().get("order_id")


# ============================================================
# ADMIN behaviours
# ============================================================
class TestAdmin:
    def test_admin_lists_all_cases(self, admin_s):
        r = admin_s.get(f"{BASE_URL}/api/cases", timeout=15)
        assert r.status_code == 200
        cases = r.json()
        emails = {c.get("owner_email") for c in cases}
        # Should see client's case AND admin cases
        assert CLIENT_EMAIL in emails, f"admin does not see client case; emails={emails}"
        # Ensure at least one admin case flagged
        assert any(c.get("is_admin_case") for c in cases) or len(CREATED_ADMIN_CASES) == 0

    def test_admin_creates_case_authorized_unlimited(self, admin_s):
        r = admin_s.post(f"{BASE_URL}/api/cases", json={"title": "TEST_iter15_admin_authorized"}, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["payment_status"] == "autorizada"
        assert d["budget_usd"] is None
        assert d["is_admin_case"] is True
        CREATED_ADMIN_CASES.append(d["id"])

    def test_admin_chat_not_gated_by_402(self, admin_s):
        # Create admin case inline to make this test independent
        rc = admin_s.post(f"{BASE_URL}/api/cases", json={"title": "TEST_iter15_admin_chat_gate"}, timeout=15)
        assert rc.status_code == 200
        cid = rc.json()["id"]
        CREATED_ADMIN_CASES.append(cid)
        r = admin_s.post(f"{BASE_URL}/api/cases/{cid}/chat", data={"text": "   "}, timeout=15)
        # 402 would mean gating fired incorrectly for admin. We expect the
        # "empty message" 400 (whitespace-only text and no files).
        assert r.status_code != 402, f"admin got 402 unexpectedly: {r.text[:200]}"
        assert r.status_code == 400, f"expected 400 empty-message, got {r.status_code}: {r.text[:200]}"

    def test_admin_payments_has_concept_and_item_type(self, admin_s):
        r = admin_s.get(f"{BASE_URL}/api/admin/payments", timeout=15)
        assert r.status_code == 200, r.text
        payments = r.json()
        assert isinstance(payments, list)
        if payments:
            # Ensure fields present on at least one record
            assert any("concept" in p for p in payments), "no payment has concept field"
            assert any("item_type" in p for p in payments), "no payment has item_type field"
