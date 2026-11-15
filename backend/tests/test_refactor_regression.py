"""Regression + Contact Inbox (iteration 10) tests after backend refactor."""
import os
import io
import time
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://proyecto-nuevo-10--3sst8oxb.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"

ADMIN_EMAIL = "admin@onbuysolutions.com"
ADMIN_PASS = "OnBuy2026!"
CLIENT_EMAIL = "cliente@test.com"
CLIENT_PASS = "Cliente123!"


def _session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _login(s, email, password):
    r = s.post(f"{API}/auth/login", json={"email": email, "password": password})
    return r


@pytest.fixture(scope="module")
def admin():
    s = _session()
    r = _login(s, ADMIN_EMAIL, ADMIN_PASS)
    if r.status_code != 200:
        pytest.skip(f"Admin login failed: {r.status_code} {r.text}")
    return s


@pytest.fixture(scope="module")
def client():
    s = _session()
    r = _login(s, CLIENT_EMAIL, CLIENT_PASS)
    if r.status_code != 200:
        # try to register
        r = s.post(f"{API}/auth/register", json={
            "name": "Cliente Test", "email": CLIENT_EMAIL,
            "password": CLIENT_PASS, "accepted_terms": True
        })
        if r.status_code not in (200, 201, 400):
            pytest.skip(f"Client register failed: {r.status_code} {r.text}")
        s = _session()
        r = _login(s, CLIENT_EMAIL, CLIENT_PASS)
        assert r.status_code == 200, r.text
    return s


# ------------------ AUTH ------------------

class TestAuth:
    def test_root(self):
        r = requests.get(f"{API}/")
        assert r.status_code == 200
        assert r.json().get("status") == "ok"

    def test_me_admin(self, admin):
        r = admin.get(f"{API}/auth/me")
        assert r.status_code == 200
        assert r.json()["role"] == "admin"

    def test_me_client(self, client):
        r = client.get(f"{API}/auth/me")
        assert r.status_code == 200
        assert r.json()["role"] == "cliente"

    def test_register_requires_terms(self):
        s = _session()
        r = s.post(f"{API}/auth/register", json={
            "name": "Sin Terms", "email": f"noterm_{int(time.time())}@x.com",
            "password": "Pass1234!", "accepted_terms": False
        })
        assert r.status_code == 400

    def test_register_new_user(self):
        s = _session()
        email = f"regtest_{int(time.time())}@x.com"
        r = s.post(f"{API}/auth/register", json={
            "name": "Reg Test", "email": email, "password": "Pass1234!", "accepted_terms": True
        })
        assert r.status_code == 200
        assert r.json()["email"] == email
        # cleanup via admin
        adm = _session()
        _login(adm, ADMIN_EMAIL, ADMIN_PASS)
        users = adm.get(f"{API}/admin/users").json()
        uid = next((u["id"] for u in users if u["email"] == email), None)
        if uid:
            adm.delete(f"{API}/admin/users/{uid}")

    def test_change_password_wrong(self, admin):
        r = admin.post(f"{API}/auth/change-password", json={
            "current_password": "WRONG_PASS", "new_password": "Whatever123!"
        })
        assert r.status_code == 401

    def test_change_password_and_restore(self):
        # separate session to not clobber module-level admin fixture cookies
        s = _session()
        assert _login(s, ADMIN_EMAIL, ADMIN_PASS).status_code == 200
        new_pw = "TempPwd_9987!"
        r = s.post(f"{API}/auth/change-password", json={
            "current_password": ADMIN_PASS, "new_password": new_pw
        })
        assert r.status_code == 200
        # login with new
        s2 = _session()
        assert _login(s2, ADMIN_EMAIL, new_pw).status_code == 200
        # restore
        r = s2.post(f"{API}/auth/change-password", json={
            "current_password": new_pw, "new_password": ADMIN_PASS
        })
        assert r.status_code == 200
        s3 = _session()
        assert _login(s3, ADMIN_EMAIL, ADMIN_PASS).status_code == 200

    def test_brute_force_lockout(self):
        # unique email so we don't lock real accounts
        email = f"brute_{int(time.time())}@x.com"
        codes = []
        for _ in range(10):
            s = _session()
            r = s.post(f"{API}/auth/login", json={"email": email, "password": "wrong"})
            codes.append(r.status_code)
        assert 429 in codes, f"Expected 429 in {codes}"


# ------------------ AUDITS ------------------

class TestAudits:
    def test_create_and_list_audit_client(self, client):
        r = client.post(f"{API}/audits", json={
            "condominium_name": "TEST_Refactor_Cond",
            "period": "2024",
            "district": "Miraflores"
        })
        assert r.status_code == 200, r.text
        audit = r.json()
        assert audit["payment_status"] == "pendiente_pago"
        aid = audit["id"]
        pytest.audit_id = aid  # stash

        # list
        r = client.get(f"{API}/audits")
        assert r.status_code == 200
        assert any(a["id"] == aid for a in r.json())

        # detail
        r = client.get(f"{API}/audits/{aid}")
        assert r.status_code == 200

    def test_analyze_pendiente_pago_402(self, client):
        aid = getattr(pytest, "audit_id", None)
        assert aid
        r = client.post(f"{API}/audits/{aid}/analyze")
        assert r.status_code == 402

    def test_upload_and_list_documents(self, client):
        aid = getattr(pytest, "audit_id", None)
        assert aid
        pdf_bytes = b"%PDF-1.4\n%TEST\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
        s = requests.Session()
        s.cookies = client.cookies
        files = {"files": ("test.pdf", pdf_bytes, "application/pdf")}
        r = s.post(f"{API}/audits/{aid}/documents", files=files)
        assert r.status_code == 200, r.text
        docs = r.json()
        assert len(docs) == 1
        pytest.doc_id = docs[0]["id"]

        r = client.get(f"{API}/audits/{aid}/documents")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_delete_document(self, client):
        did = getattr(pytest, "doc_id", None)
        assert did
        r = client.delete(f"{API}/documents/{did}")
        assert r.status_code == 200

    def test_delete_audit(self, client):
        aid = getattr(pytest, "audit_id", None)
        assert aid
        r = client.delete(f"{API}/audits/{aid}")
        assert r.status_code == 200

    def test_dashboard_stats(self, client):
        r = client.get(f"{API}/dashboard/stats")
        assert r.status_code == 200
        d = r.json()
        for k in ["total_audits", "completed", "pending", "documents"]:
            assert k in d

    def test_samples_list_and_download(self, client):
        r = client.get(f"{API}/samples")
        assert r.status_code == 200
        samples = r.json()
        assert isinstance(samples, list)
        if samples:
            fname = samples[0]["filename"]
            r = client.get(f"{API}/samples/{fname}")
            assert r.status_code == 200

    def test_admin_can_delete_others_audit(self, client, admin):
        # create as client
        r = client.post(f"{API}/audits", json={
            "condominium_name": "TEST_AdminDelete", "period": "2024"
        })
        assert r.status_code == 200
        aid = r.json()["id"]
        # admin deletes
        r = admin.delete(f"{API}/audits/{aid}")
        assert r.status_code == 200


# ------------------ ADMIN ------------------

class TestAdmin:
    def test_admin_only_forbidden_for_client(self, client):
        r = client.get(f"{API}/admin/users")
        assert r.status_code == 403

    def test_list_audits(self, admin):
        r = admin.get(f"{API}/admin/audits")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_list_users(self, admin):
        r = admin.get(f"{API}/admin/users")
        assert r.status_code == 200
        assert any(u["email"] == ADMIN_EMAIL for u in r.json())

    def test_delete_admin_protected(self, admin):
        users = admin.get(f"{API}/admin/users").json()
        admin_id = next(u["id"] for u in users if u["email"] == ADMIN_EMAIL)
        r = admin.delete(f"{API}/admin/users/{admin_id}")
        assert r.status_code == 400

    def test_delete_test_user_cascade(self, admin):
        # create throwaway user
        s = _session()
        email = f"todelete_{int(time.time())}@x.com"
        r = s.post(f"{API}/auth/register", json={
            "name": "To Delete", "email": email, "password": "Pass1234!", "accepted_terms": True
        })
        assert r.status_code == 200
        # create audit for them
        s.post(f"{API}/audits", json={"condominium_name": "TEST_Cascade", "period": "2024"})
        # admin deletes
        users = admin.get(f"{API}/admin/users").json()
        uid = next(u["id"] for u in users if u["email"] == email)
        r = admin.delete(f"{API}/admin/users/{uid}")
        assert r.status_code == 200

    def test_authorize_revoke_audit(self, admin, client):
        r = client.post(f"{API}/audits", json={"condominium_name": "TEST_Authz", "period": "2024"})
        aid = r.json()["id"]
        r = admin.post(f"{API}/admin/audits/{aid}/authorize")
        assert r.status_code == 200
        r = admin.post(f"{API}/admin/audits/{aid}/revoke")
        assert r.status_code == 200
        client.delete(f"{API}/audits/{aid}")

    def test_settings_get_put_revert(self, admin):
        r = admin.get(f"{API}/admin/settings")
        assert r.status_code == 200
        orig = r.json()
        original_email = orig.get("contact_email")
        r = admin.put(f"{API}/admin/settings", json={"contact_email": "temp_test@example.com"})
        assert r.status_code == 200
        r = admin.get(f"{API}/admin/settings")
        assert r.json()["contact_email"] == "temp_test@example.com"
        # revert
        admin.put(f"{API}/admin/settings", json={"contact_email": original_email})
        r = admin.get(f"{API}/admin/settings")
        assert r.json()["contact_email"] == original_email

    def test_public_settings_no_auth(self):
        r = requests.get(f"{API}/public/settings")
        assert r.status_code == 200
        assert "price_small" in r.json()

    def test_generate_propuesta(self, admin):
        r = admin.post(f"{API}/admin/documents/generate", json={
            "doc_type": "propuesta",
            "fields": {"cliente": "Test SAC", "condominio": "Villa Test"}
        })
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert len(r.content) > 500


# ------------------ CONTACT INBOX (NEW) ------------------

class TestContactInbox:
    def test_public_post_contact(self):
        r = requests.post(f"{API}/contact", json={
            "name": "TEST Regression",
            "email": "test_reg@example.com",
            "phone": "999",
            "message": "Mensaje de regresion refactor"
        })
        assert r.status_code == 200

    def test_client_forbidden(self, client):
        r = client.get(f"{API}/admin/contacts")
        assert r.status_code == 403

    def test_admin_list_and_unread(self, admin):
        r = admin.get(f"{API}/admin/contacts")
        assert r.status_code == 200
        contacts = r.json()
        assert isinstance(contacts, list)
        assert len(contacts) >= 1
        latest = next((c for c in contacts if c["name"] == "TEST Regression"), None)
        assert latest is not None, "Contact just created not found"
        assert latest["read"] is False
        pytest.contact_id = latest["id"]

    def test_mark_read_and_unread(self, admin):
        cid = getattr(pytest, "contact_id", None)
        assert cid
        r = admin.put(f"{API}/admin/contacts/{cid}/read", json={"read": True})
        assert r.status_code == 200
        contacts = admin.get(f"{API}/admin/contacts").json()
        item = next(c for c in contacts if c["id"] == cid)
        assert item["read"] is True

        r = admin.put(f"{API}/admin/contacts/{cid}/read", json={"read": False})
        assert r.status_code == 200
        contacts = admin.get(f"{API}/admin/contacts").json()
        item = next(c for c in contacts if c["id"] == cid)
        assert item["read"] is False

    def test_delete_contact(self, admin):
        cid = getattr(pytest, "contact_id", None)
        assert cid
        r = admin.delete(f"{API}/admin/contacts/{cid}")
        assert r.status_code == 200
        # 404 on second delete
        r = admin.delete(f"{API}/admin/contacts/{cid}")
        assert r.status_code == 404

    def test_mark_read_nonexistent_404(self, admin):
        r = admin.put(f"{API}/admin/contacts/507f1f77bcf86cd799439011/read", json={"read": True})
        assert r.status_code == 404


# ------------------ CONSULTING ------------------

class TestConsulting:
    def test_list_cases(self, admin):
        r = admin.get(f"{API}/admin/cases")
        assert r.status_code == 200
        cases = r.json()
        pytest.cases = cases
        assert isinstance(cases, list)
        # No borrar - just verify demos exist
        titles = [c.get("title", "") for c in cases]
        assert any("demo" in t.lower() or "Casas Del Valle" in t for t in titles), f"Expected demo cases in: {titles}"

    def test_create_get_update_delete_case(self, admin):
        r = admin.post(f"{API}/admin/cases", json={
            "title": "TEST_Refactor_Case",
            "description": "regresion refactor"
        })
        assert r.status_code == 200, r.text
        cid = r.json()["id"]

        r = admin.get(f"{API}/admin/cases/{cid}")
        assert r.status_code == 200
        j = r.json()
        assert "case" in j and "messages" in j

        r = admin.put(f"{API}/admin/cases/{cid}", json={"status": "archivado"})
        assert r.status_code == 200

        r = admin.delete(f"{API}/admin/cases/{cid}")
        assert r.status_code == 200

    def test_demo_case_documents_and_export(self, admin):
        cases = getattr(pytest, "cases", None) or admin.get(f"{API}/admin/cases").json()
        demo = next((c for c in cases if "demo" in c.get("title", "").lower() and "biblioteca" in c.get("title", "").lower()), None)
        if not demo:
            pytest.skip("Demo library case not found")
        cid = demo["id"]
        r = admin.get(f"{API}/admin/cases/{cid}/documents")
        assert r.status_code == 200
        docs = r.json()
        assert len(docs) >= 2

        r = admin.post(f"{API}/admin/cases/{cid}/export-pdf", json={
            "message_id": docs[0]["message_id"],
            "only_document": True,
            "doc_index": docs[0]["doc_index"]
        })
        assert r.status_code == 200, f"{r.status_code}: {r.text[:200]}"
        assert r.headers.get("content-type", "").startswith("application/pdf")
