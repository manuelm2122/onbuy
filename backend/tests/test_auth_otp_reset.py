"""Backend tests for OTP registration, email verification, forgot/reset password, and contact regression."""
import os
import time
import uuid
import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://onbuy-preview--2rpiwlk3.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "test_database"

_mongo = MongoClient(MONGO_URL)
_db = _mongo[DB_NAME]


def _new_email():
    return f"qa-test-{uuid.uuid4().hex[:10]}@test.com"


def _get_user(email):
    return _db.users.find_one({"email": email.lower().strip()})


# ---- REGISTER + OTP ----
class TestRegisterOtp:
    def setup_method(self):
        self.email = _new_email()
        self.password = "Test1234!"

    def teardown_method(self):
        _db.users.delete_one({"email": self.email})

    def test_register_requires_terms(self):
        r = requests.post(f"{API}/auth/register", json={
            "name": "QA", "email": self.email, "password": self.password, "accepted_terms": False
        })
        assert r.status_code == 400

    def test_full_flow_register_verify_login(self):
        # register
        r = requests.post(f"{API}/auth/register", json={
            "name": "QA Tester", "email": self.email, "password": self.password, "accepted_terms": True
        })
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["requires_verification"] is True
        assert data["email"] == self.email

        # user in DB, not verified, has verification_code
        user = _get_user(self.email)
        assert user is not None
        assert user.get("email_verified") is False
        code = user.get("verification_code")
        assert code and len(code) == 6

        # login before verify → 403 EMAIL_NOT_VERIFIED
        r = requests.post(f"{API}/auth/login", json={"email": self.email, "password": self.password})
        assert r.status_code == 403
        detail = r.json().get("detail")
        assert isinstance(detail, dict) and detail.get("error_code") == "EMAIL_NOT_VERIFIED"

        # re-read code (login may have re-issued a new one after cooldown - but was just sent so same)
        user = _get_user(self.email)
        code = user.get("verification_code")

        # verify with wrong code → 400
        r = requests.post(f"{API}/auth/verify-email", json={"email": self.email, "code": "000000"})
        # 000000 could randomly match but unlikely; if it matches, skip
        if code != "000000":
            assert r.status_code == 400, r.text

        # verify with correct code
        r = requests.post(f"{API}/auth/verify-email", json={"email": self.email, "code": code})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["email"] == self.email
        assert "id" in body
        # cookies set
        assert "access_token" in r.cookies or any("access_token" in c for c in r.headers.get("set-cookie", ""))

        # /me works with cookies
        s = requests.Session()
        # login again via verified account
        r2 = s.post(f"{API}/auth/login", json={"email": self.email, "password": self.password})
        assert r2.status_code == 200
        me = s.get(f"{API}/auth/me")
        assert me.status_code == 200
        assert me.json()["email"] == self.email

    def test_resend_cooldown(self):
        r = requests.post(f"{API}/auth/register", json={
            "name": "QA Resend", "email": self.email, "password": self.password, "accepted_terms": True
        })
        assert r.status_code == 200
        # immediate resend within 60s cooldown → 429
        r = requests.post(f"{API}/auth/resend-code", json={"email": self.email})
        assert r.status_code == 429, r.text


# ---- FORGOT / RESET ----
class TestForgotReset:
    def setup_method(self):
        self.email = _new_email()
        self.password = "OldPass123!"
        self.new_password = "NewPass456!"
        # create verified user directly via API: register + verify
        r = requests.post(f"{API}/auth/register", json={
            "name": "QA Reset", "email": self.email, "password": self.password, "accepted_terms": True
        })
        assert r.status_code == 200
        code = _get_user(self.email)["verification_code"]
        r = requests.post(f"{API}/auth/verify-email", json={"email": self.email, "code": code})
        assert r.status_code == 200

    def teardown_method(self):
        _db.users.delete_one({"email": self.email})

    def test_forgot_generic_for_nonexistent(self):
        r = requests.post(f"{API}/auth/forgot-password", json={"email": f"nobody-{uuid.uuid4().hex[:6]}@test.com"})
        assert r.status_code == 200
        assert "message" in r.json()

    def test_forgot_and_reset_flow(self):
        # forgot-password
        r = requests.post(f"{API}/auth/forgot-password", json={"email": self.email})
        assert r.status_code == 200

        user = _get_user(self.email)
        code = user.get("reset_code")
        assert code and len(code) == 6

        # wrong code → 400
        r = requests.post(f"{API}/auth/reset-password", json={
            "email": self.email, "code": "000000", "new_password": self.new_password
        })
        if code != "000000":
            assert r.status_code == 400

        # correct code → 200
        r = requests.post(f"{API}/auth/reset-password", json={
            "email": self.email, "code": code, "new_password": self.new_password
        })
        assert r.status_code == 200, r.text

        # login with old fails
        r = requests.post(f"{API}/auth/login", json={"email": self.email, "password": self.password})
        assert r.status_code == 401

        # login with new works
        r = requests.post(f"{API}/auth/login", json={"email": self.email, "password": self.new_password})
        assert r.status_code == 200
        assert r.json()["email"] == self.email

    def test_forgot_cooldown(self):
        r = requests.post(f"{API}/auth/forgot-password", json={"email": self.email})
        assert r.status_code == 200
        r = requests.post(f"{API}/auth/forgot-password", json={"email": self.email})
        assert r.status_code == 429


# ---- ADMIN LOGIN REGRESSION ----
def test_admin_login():
    r = requests.post(f"{API}/auth/login", json={
        "email": "admin@onbuysolutions.com", "password": "OnBuy2026!"
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["role"] == "admin"


# ---- CONTACT REGRESSION ----
def test_contact_endpoint():
    payload = {"name": "QA Bot", "email": "qa@test.com", "message": "Mensaje de prueba automatizado"}
    r = requests.post(f"{API}/contact", json=payload)
    assert r.status_code == 200, r.text
    # persisted
    doc = _db.contacts.find_one({"email": "qa@test.com"}, sort=[("_id", -1)])
    assert doc is not None
    assert doc["message"] == payload["message"]
