"""Backend tests for Libro de Reclamaciones Virtual (iteration 11)."""
import os
import re
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://onbuy-preview--2rpiwlk3.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = {"email": "admin@onbuysolutions.com", "password": "OnBuy2026!"}
CLIENT = {"email": "cliente@test.com", "password": "Cliente123!"}


def _valid_payload(**overrides):
    p = {
        "consumer_name": "TEST Juan Perez",
        "doc_type": "DNI",
        "doc_number": "12345678",
        "address": "Av. Test 123, Lima",
        "phone": "999888777",
        "email": "test@example.com",
        "item_type": "Servicio",
        "amount": 1500.50,
        "service_description": "Auditoría de condominio realizada en enero 2026",
        "request_type": "Reclamo",
        "detail": "El servicio no se entregó en el plazo pactado por más de 30 días.",
        "consumer_request": "Solicito reembolso completo o entrega inmediata.",
        "accepted_declaration": True,
    }
    p.update(overrides)
    return p


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=ADMIN, timeout=15)
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def client_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=CLIENT, timeout=15)
    if r.status_code != 200:
        # Try to register the cliente first
        s.post(f"{API}/auth/register", json={
            "name": "Cliente Test",
            "email": CLIENT["email"],
            "password": CLIENT["password"],
            "accepted_terms": True,
        }, timeout=15)
        r = s.post(f"{API}/auth/login", json=CLIENT, timeout=15)
    if r.status_code != 200:
        pytest.skip(f"Client login failed: {r.status_code}")
    return s


@pytest.fixture(scope="module")
def created_complaint():
    """Create a complaint and return the response for reuse."""
    r = requests.post(f"{API}/complaints", json=_valid_payload(), timeout=20)
    assert r.status_code == 200, f"{r.status_code} {r.text}"
    return r.json()


# ---------- POST /complaints ----------
class TestCreateComplaint:
    def test_create_success(self, created_complaint):
        d = created_complaint
        assert "id" in d and "code" in d
        assert re.match(r"^LRV-2026-\d{5}$", d["code"]), f"Bad code format: {d['code']}"
        seq = int(d["code"].split("-")[-1])
        assert seq >= 2, f"Expected correlativo >=2 (already 00001 exists), got {seq}"
        assert "created_at" in d and "due_date_display" in d

    def test_correlativo_increments(self, created_complaint):
        seq1 = int(created_complaint["code"].split("-")[-1])
        r = requests.post(f"{API}/complaints", json=_valid_payload(), timeout=20)
        assert r.status_code == 200
        seq2 = int(r.json()["code"].split("-")[-1])
        assert seq2 == seq1 + 1, f"Not correlative: {seq1} -> {seq2}"

    def test_reject_no_declaration(self):
        r = requests.post(f"{API}/complaints", json=_valid_payload(accepted_declaration=False), timeout=15)
        assert r.status_code == 400

    def test_reject_bad_doc_type(self):
        r = requests.post(f"{API}/complaints", json=_valid_payload(doc_type="INVALID"), timeout=15)
        assert r.status_code == 400

    def test_reject_bad_request_type(self):
        r = requests.post(f"{API}/complaints", json=_valid_payload(request_type="XYZ"), timeout=15)
        assert r.status_code == 400

    def test_reject_bad_email(self):
        r = requests.post(f"{API}/complaints", json=_valid_payload(email="notanemail"), timeout=15)
        assert r.status_code == 422

    def test_reject_short_detail(self):
        r = requests.post(f"{API}/complaints", json=_valid_payload(detail="corto"), timeout=15)
        assert r.status_code == 422


# ---------- GET /complaints/{id}/receipt ----------
class TestReceiptPDF:
    def test_receipt_is_pdf(self, created_complaint):
        cid = created_complaint["id"]
        r = requests.get(f"{API}/complaints/{cid}/receipt", timeout=30)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:4] == b"%PDF"
        # Extract text using pypdf (streams are FlateDecode-compressed)
        from pypdf import PdfReader
        from io import BytesIO
        reader = PdfReader(BytesIO(r.content))
        text = "\n".join(p.extract_text() or "" for p in reader.pages)
        for marker in ["HOJA DE RECLAMACI", "20606439327", created_complaint["code"], "INDECOPI", "15"]:
            assert marker in text, f"Marker missing in PDF: {marker}"

    def test_receipt_404(self):
        r = requests.get(f"{API}/complaints/000000000000000000000000/receipt", timeout=15)
        assert r.status_code == 404


# ---------- Admin endpoints ----------
class TestAdminComplaints:
    def test_client_forbidden(self, client_session):
        r = client_session.get(f"{API}/admin/complaints", timeout=15)
        assert r.status_code == 403

    def test_admin_list(self, admin_session, created_complaint):
        r = admin_session.get(f"{API}/admin/complaints", timeout=15)
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list) and len(items) >= 1
        first = items[0]
        for k in ("id", "code", "status", "due_date", "consumer_email_status", "admin_email_status"):
            assert k in first, f"Missing key {k}"

    def test_mark_responded_then_pending(self, admin_session, created_complaint):
        cid = created_complaint["id"]
        r = admin_session.put(f"{API}/admin/complaints/{cid}/status",
                              json={"status": "respondido", "response_note": "Se respondió al cliente"}, timeout=15)
        assert r.status_code == 200
        # verify
        lst = admin_session.get(f"{API}/admin/complaints", timeout=15).json()
        me = next((x for x in lst if x["id"] == cid), None)
        assert me and me["status"] == "respondido" and me.get("responded_at")
        # revert
        r = admin_session.put(f"{API}/admin/complaints/{cid}/status", json={"status": "pendiente"}, timeout=15)
        assert r.status_code == 200
        lst = admin_session.get(f"{API}/admin/complaints", timeout=15).json()
        me = next((x for x in lst if x["id"] == cid), None)
        assert me and me["status"] == "pendiente"

    def test_invalid_status(self, admin_session, created_complaint):
        cid = created_complaint["id"]
        r = admin_session.put(f"{API}/admin/complaints/{cid}/status", json={"status": "closed"}, timeout=15)
        assert r.status_code == 400

    def test_no_delete_endpoint(self, admin_session, created_complaint):
        cid = created_complaint["id"]
        r = admin_session.delete(f"{API}/admin/complaints/{cid}", timeout=15)
        assert r.status_code in (404, 405), f"Expected 404/405 (no DELETE), got {r.status_code}"


# ---------- Settings (Resend) ----------
class TestSettingsResend:
    def test_get_settings_masks_key(self, admin_session):
        r = admin_session.get(f"{API}/admin/settings", timeout=15)
        assert r.status_code == 200
        s = r.json()
        assert "resend_key_masked" in s
        assert "resend_api_key" not in s, "Full resend_api_key must not be exposed"
        assert "resend_sender" in s
        assert "complaints_notify_email" in s

    def test_put_empty_key_does_not_wipe(self, admin_session):
        # Get current mask
        before = admin_session.get(f"{API}/admin/settings", timeout=15).json()
        mask_before = before["resend_key_masked"]
        assert mask_before, "Resend key should already be configured"
        # PUT with empty resend_api_key should not clear the stored key
        r = admin_session.put(f"{API}/admin/settings", json={"resend_api_key": ""}, timeout=15)
        assert r.status_code == 200
        after = admin_session.get(f"{API}/admin/settings", timeout=15).json()
        assert after["resend_key_masked"] == mask_before, "Empty PUT wiped the resend_api_key!"


# ---------- Regression ----------
class TestRegression:
    def test_client_login(self, client_session):
        r = client_session.get(f"{API}/auth/me", timeout=15)
        assert r.status_code == 200

    def test_admin_tabs_endpoints(self, admin_session):
        # Just make sure common admin endpoints still respond
        for path in ("/admin/users", "/admin/settings"):
            r = admin_session.get(f"{API}{path}", timeout=15)
            assert r.status_code == 200, f"{path} -> {r.status_code}"

    def test_email_failure_does_not_break_creation(self):
        """Resend test-mode fails for non-onbuysolutions emails, but complaint should still be recorded."""
        r = requests.post(f"{API}/complaints", json=_valid_payload(email="test@example.com"), timeout=20)
        assert r.status_code == 200
        cid = r.json()["id"]
        # Wait for background task to complete
        time.sleep(6)
        # Verify still in DB (fetching PDF succeeds)
        rec = requests.get(f"{API}/complaints/{cid}/receipt", timeout=15)
        assert rec.status_code == 200
