"""Tests for PayPal payment endpoints and admin settings."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL") or open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split("\n")[0].strip()
BASE_URL = BASE_URL.rstrip("/")
API = f"{BASE_URL}/api"

CLIENT_EMAIL = "otptest@test.com"
CLIENT_PASS = "nuevapass456"
ADMIN_EMAIL = "admin@onbuysolutions.com"
ADMIN_PASS = "OnBuy2026!"
AUDIT_ID = "6a57731f1ba8274ddfe93fd6"


def login(email, pw):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=15)
    assert r.status_code == 200, f"login failed {r.status_code}: {r.text}"
    return s


@pytest.fixture(scope="module")
def client_session():
    return login(CLIENT_EMAIL, CLIENT_PASS)


@pytest.fixture(scope="module")
def admin_session():
    return login(ADMIN_EMAIL, ADMIN_PASS)


# --- payments config/quote ---

def test_payment_config(client_session):
    r = client_session.get(f"{API}/payments/config", timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d["mode"] == "sandbox"
    assert d["client_id"]
    assert d["currency"] == "USD"


def test_payment_config_requires_auth():
    r = requests.get(f"{API}/payments/config", timeout=15)
    assert r.status_code in (401, 403)


def test_quote_small(client_session):
    r = client_session.get(f"{API}/payments/quote?plan=small", timeout=20)
    assert r.status_code == 200
    d = r.json()
    assert d["amount_pen"] == 1100
    assert d["amount_usd"] > 200 and d["amount_usd"] < 400
    assert d["rate_pen_per_usd"] and 3.0 < d["rate_pen_per_usd"] < 4.5


def test_quote_medium(client_session):
    r = client_session.get(f"{API}/payments/quote?plan=medium", timeout=20)
    assert r.status_code == 200
    d = r.json()
    assert d["amount_pen"] == 2100
    assert d["amount_usd"] > 500 and d["amount_usd"] < 700


def test_quote_invalid_plan(client_session):
    r = client_session.get(f"{API}/payments/quote?plan=large", timeout=15)
    assert r.status_code == 400


# --- create-order ---

def test_create_order_invalid_plan(client_session):
    r = client_session.post(f"{API}/payments/create-order", json={"audit_id": AUDIT_ID, "plan": "large"}, timeout=15)
    assert r.status_code == 400


def test_create_order_not_owner(client_session):
    r = client_session.post(f"{API}/payments/create-order", json={"audit_id": "000000000000000000000000", "plan": "small"}, timeout=15)
    assert r.status_code == 404


def test_create_order_success(client_session):
    r = client_session.post(f"{API}/payments/create-order", json={"audit_id": AUDIT_ID, "plan": "small"}, timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["order_id"]
    assert d["amount_usd"] > 200
    # store for capture test
    pytest.PAYPAL_ORDER = d["order_id"]


def test_capture_unapproved_order(client_session):
    order_id = getattr(pytest, "PAYPAL_ORDER", None)
    if not order_id:
        pytest.skip("no order to capture")
    r = client_session.post(f"{API}/payments/capture/{order_id}", timeout=30)
    assert r.status_code == 400
    assert "no pudo completarse" in r.json().get("detail", "").lower() or "pago" in r.json().get("detail", "").lower()


def test_capture_nonexistent_order(client_session):
    r = client_session.post(f"{API}/payments/capture/NOPE999999", timeout=15)
    assert r.status_code == 404


# --- admin settings paypal ---

def test_admin_settings_paypal_fields(admin_session):
    r = admin_session.get(f"{API}/admin/settings", timeout=15)
    assert r.status_code == 200
    s = r.json()
    assert "paypal_client_id" in s
    assert "paypal_secret_masked" in s
    assert s["paypal_secret_masked"], "secret should be masked non-empty"
    assert s["paypal_mode"] in ("sandbox", "live")
    assert "paypal_secret" not in s  # raw secret must not leak


def test_admin_settings_save_without_secret_preserves(admin_session):
    r = admin_session.get(f"{API}/admin/settings", timeout=15)
    s = r.json()
    original_masked = s["paypal_secret_masked"]

    payload = {
        "ai_model": s.get("ai_model"),
        "price_small": s.get("price_small", 1100),
        "price_medium": s.get("price_medium", 2100),
        "paypal_client_id": s.get("paypal_client_id"),
        "paypal_mode": "sandbox",
        # NO paypal_secret
    }
    r2 = admin_session.put(f"{API}/admin/settings", json=payload, timeout=15)
    assert r2.status_code == 200
    r3 = admin_session.get(f"{API}/admin/settings", timeout=15)
    assert r3.json()["paypal_secret_masked"] == original_masked


def test_admin_settings_toggle_mode(admin_session):
    payload = {"paypal_mode": "live"}
    r = admin_session.put(f"{API}/admin/settings", json=payload, timeout=15)
    assert r.status_code == 200
    assert admin_session.get(f"{API}/admin/settings", timeout=15).json()["paypal_mode"] == "live"
    # revert
    admin_session.put(f"{API}/admin/settings", json={"paypal_mode": "sandbox"}, timeout=15)
    assert admin_session.get(f"{API}/admin/settings", timeout=15).json()["paypal_mode"] == "sandbox"


# --- regression: pending payment ---

def test_audit_starts_pendiente_pago(client_session):
    r = client_session.get(f"{API}/audits", timeout=15)
    assert r.status_code == 200
    audits = r.json()
    target = next((a for a in audits if a["id"] == AUDIT_ID), None)
    assert target, "test audit missing"
    assert target["payment_status"] == "pendiente_pago"


def test_analyze_blocked_when_unpaid(client_session):
    r = client_session.post(f"{API}/audits/{AUDIT_ID}/analyze", timeout=15)
    assert r.status_code == 402
