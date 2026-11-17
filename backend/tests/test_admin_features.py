"""Tests for iteration 8: admin users, admin settings, admin delete audit, change-password."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://onbuy-preview--2rpiwlk3.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@onbuysolutions.com"
ADMIN_PASS = "OnBuy2026!"

import uuid as _uuid
TS = f"{int(time.time())}_{_uuid.uuid4().hex[:6]}"
CLIENT_EMAIL = f"TEST_cliente_{TS}@test.com"
CLIENT_PASS = "Cliente123!"
CLIENT2_EMAIL = f"TEST_cliente2_{TS}@test.com"


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def client_session():
    s = requests.Session()
    # register test client
    r = s.post(f"{API}/auth/register", json={
        "name": "Cliente Test", "email": CLIENT_EMAIL, "password": CLIENT_PASS, "accepted_terms": True
    })
    assert r.status_code in (200, 201), f"register failed: {r.status_code} {r.text}"
    # login (register may auto-login, but ensure cookies)
    r = s.post(f"{API}/auth/login", json={"email": CLIENT_EMAIL, "password": CLIENT_PASS})
    assert r.status_code == 200
    return s


@pytest.fixture(scope="module")
def client2_session():
    s = requests.Session()
    s.post(f"{API}/auth/register", json={
        "name": "Cliente2", "email": CLIENT2_EMAIL, "password": CLIENT_PASS, "accepted_terms": True
    })
    s.post(f"{API}/auth/login", json={"email": CLIENT2_EMAIL, "password": CLIENT_PASS})
    return s


# ---------- change-password ----------
class TestChangePassword:
    def test_wrong_current_returns_401(self, client_session):
        r = client_session.post(f"{API}/auth/change-password",
                                json={"current_password": "wrongpass", "new_password": "NewPass123!"})
        assert r.status_code == 401

    def test_correct_change_and_login(self, client_session):
        new_pass = "NewCliente456!"
        r = client_session.post(f"{API}/auth/change-password",
                                json={"current_password": CLIENT_PASS, "new_password": new_pass})
        assert r.status_code == 200
        # login with new
        s = requests.Session()
        r = s.post(f"{API}/auth/login", json={"email": CLIENT_EMAIL, "password": new_pass})
        assert r.status_code == 200
        # restore
        r = s.post(f"{API}/auth/change-password",
                   json={"current_password": new_pass, "new_password": CLIENT_PASS})
        assert r.status_code == 200


# ---------- admin/users ----------
class TestAdminUsers:
    def test_client_forbidden(self, client_session):
        r = client_session.get(f"{API}/admin/users")
        assert r.status_code == 403

    def test_admin_list(self, admin_session):
        r = admin_session.get(f"{API}/admin/users")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list) and len(data) > 0
        u = data[0]
        for k in ("id", "name", "email", "role", "created_at", "audit_count", "document_count"):
            assert k in u

    def test_cannot_delete_admin(self, admin_session):
        users = admin_session.get(f"{API}/admin/users").json()
        admin_user = next((u for u in users if u["role"] == "admin"), None)
        assert admin_user
        r = admin_session.delete(f"{API}/admin/users/{admin_user['id']}")
        assert r.status_code == 400

    def test_delete_client_cascade(self, admin_session):
        # create a throwaway user
        throw_email = f"TEST_throw_{TS}@test.com"
        throw_email_lc = throw_email.lower()
        s = requests.Session()
        r = s.post(f"{API}/auth/register", json={
            "name": "Throw", "email": throw_email, "password": CLIENT_PASS, "accepted_terms": True
        })
        assert r.status_code in (200, 201)
        s.post(f"{API}/auth/login", json={"email": throw_email, "password": CLIENT_PASS})
        # create audit as this user
        r = s.post(f"{API}/audits", json={
            "condominium_name": "TEST Cascade", "address": "Av. X", "district": "Lima",
            "period": "2024", "purpose": "Test", "notes": ""
        })
        assert r.status_code == 200, r.text
        audit_id = r.json()["id"]
        # find user id
        users = admin_session.get(f"{API}/admin/users").json()
        target = next(u for u in users if u["email"] == throw_email_lc)
        # delete
        r = admin_session.delete(f"{API}/admin/users/{target['id']}")
        assert r.status_code == 200
        # verify cascade - user no longer in list
        users2 = admin_session.get(f"{API}/admin/users").json()
        assert not any(u["email"] == throw_email_lc for u in users2)
        # audit not in admin's own list - just verify get returns 404 for owner (session gone)
        # Instead check via admin: list audits filtered by user - we don't have that endpoint, skip


# ---------- admin delete audit (any user's) ----------
class TestAdminDeleteAudit:
    def test_admin_deletes_other_users_audit(self, admin_session, client2_session):
        # cliente2 creates an audit
        r = client2_session.post(f"{API}/audits", json={
            "condominium_name": "TEST Admin Delete", "address": "Y", "district": "Lima",
            "period": "2024", "purpose": "Test", "notes": ""
        })
        assert r.status_code == 200
        aid = r.json()["id"]
        # admin deletes
        r = admin_session.delete(f"{API}/audits/{aid}")
        assert r.status_code == 200
        # cliente2 no longer sees it
        r = client2_session.get(f"{API}/audits/{aid}")
        assert r.status_code == 404

    def test_client_cannot_delete_others_audit(self, client_session, client2_session):
        # client2 creates
        r = client2_session.post(f"{API}/audits", json={
            "condominium_name": "TEST c2 own", "address": "Z", "district": "Lima",
            "period": "2024", "purpose": "Test", "notes": ""
        })
        aid = r.json()["id"]
        # client tries delete
        r = client_session.delete(f"{API}/audits/{aid}")
        assert r.status_code == 404
        # cleanup by owner
        client2_session.delete(f"{API}/audits/{aid}")


# ---------- admin/settings ----------
class TestAdminSettings:
    def test_client_forbidden_get(self, client_session):
        assert client_session.get(f"{API}/admin/settings").status_code == 403

    def test_client_forbidden_put(self, client_session):
        assert client_session.put(f"{API}/admin/settings", json={"price_small": 999}).status_code == 403

    def test_admin_get_masked(self, admin_session):
        r = admin_session.get(f"{API}/admin/settings")
        assert r.status_code == 200
        data = r.json()
        assert "llm_key_masked" in data
        assert "llm_key" not in data  # full key must never be exposed
        for k in ("price_small", "price_medium", "contact_email"):
            assert k in data

    def test_put_updates_and_public_reflects(self, admin_session):
        r = admin_session.put(f"{API}/admin/settings", json={"price_small": 1200})
        assert r.status_code == 200
        r = requests.get(f"{API}/public/settings")
        assert r.status_code == 200
        assert r.json()["price_small"] == 1200
        # revert
        r = admin_session.put(f"{API}/admin/settings", json={"price_small": 1100})
        assert r.status_code == 200
        assert requests.get(f"{API}/public/settings").json()["price_small"] == 1100

    def test_empty_llm_key_does_not_wipe(self, admin_session):
        # get masked before
        before = admin_session.get(f"{API}/admin/settings").json()["llm_key_masked"]
        r = admin_session.put(f"{API}/admin/settings", json={"llm_key": ""})
        assert r.status_code == 200
        after = admin_session.get(f"{API}/admin/settings").json()["llm_key_masked"]
        assert after == before, f"key was wiped: before={before} after={after}"


# ---------- Regression: create audit + upload doc ----------
class TestRegression:
    def test_create_audit_and_upload(self, client_session):
        r = client_session.post(f"{API}/audits", json={
            "condominium_name": "TEST Regression", "address": "Av R", "district": "Lima",
            "period": "2024", "purpose": "Test", "notes": ""
        })
        assert r.status_code == 200
        audit = r.json()
        assert audit["payment_status"] == "pendiente_pago"
        aid = audit["id"]
        # upload a small doc
        files = {"files": ("test.txt", b"hello world content for regression", "text/plain")}
        r = client_session.post(f"{API}/audits/{aid}/documents", files=files)
        assert r.status_code == 200, r.text
        docs = r.json()
        assert len(docs) == 1
        # cleanup
        client_session.delete(f"{API}/audits/{aid}")
