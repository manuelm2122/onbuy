"""Iteration 6 - Legal citation robustness (016-2024-JUS + 003-2013-JUS derogación) and mandatory alerts in AUDIT_SYSTEM_PROMPT."""
import io
import os
import re
import pytest
import requests
from pymongo import MongoClient
from bson import ObjectId

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://proyecto-nuevo-10--3sst8oxb.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
ADMIN_EMAIL = "admin@onbuysolutions.com"
ADMIN_PASSWORD = "OnBuy2026!"
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")


@pytest.fixture(scope="module")
def sess():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"admin login failed: {r.text}"
    return s


@pytest.fixture(scope="module")
def mongo():
    return MongoClient(MONGO_URL)[DB_NAME]


def _extract_pdf_text(content: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        from PyPDF2 import PdfReader
    reader = PdfReader(io.BytesIO(content))
    text = "".join(p.extract_text() or "" for p in reader.pages)
    return " ".join(text.split())  # normalize whitespace/newlines


# --- 1. Audit report PDF disclaimer ---

def test_audit_report_pdf_contains_updated_legal_citation(sess, mongo):
    r = sess.post(f"{API}/audits", json={"condominium_name": "TEST Legal Cita", "period": "2025-07"}, timeout=15)
    assert r.status_code == 200
    aid = r.json()["id"]
    try:
        mongo.audits.update_one(
            {"_id": ObjectId(aid)},
            {"$set": {"analysis": "## 1. RESUMEN EJECUTIVO\nTest.\n", "status": "completada"}},
        )
        r = sess.get(f"{API}/audits/{aid}/report", timeout=20)
        assert r.status_code == 200
        assert r.content[:4] == b"%PDF"
        norm = _extract_pdf_text(r.content)
        # Robust legal citation: current reglamento + derogated reglamento + vigency date
        assert "016-2024-JUS" in norm, f"Missing 016-2024-JUS. Extract: {norm[-800:]}"
        assert "003-2013-JUS" in norm, f"Missing 003-2013-JUS (derogated). Extract: {norm[-800:]}"
        # Vigency phrase — pypdf may split; check tokens
        assert "30 de marzo de 2025" in norm or re.search(r"30\s*de\s*marzo\s*de\s*2025", norm), \
            f"Missing vigency date. Extract: {norm[-800:]}"
        assert "derog" in norm.lower(), "Missing derogación language"
    finally:
        sess.delete(f"{API}/audits/{aid}", timeout=10)


# --- 2. AUDIT_SYSTEM_PROMPT static checks ---

def test_audit_system_prompt_has_mandatory_alerts_and_regulation_rule():
    with open("/app/backend/server.py", "r", encoding="utf-8") as f:
        code = f.read()
    # Locate the prompt constant
    m = re.search(r'AUDIT_SYSTEM_PROMPT\s*=\s*"""(.+?)"""', code, re.DOTALL)
    assert m, "AUDIT_SYSTEM_PROMPT not found"
    prompt = m.group(1)
    assert "ALERTAS AUTOMÁTICAS OBLIGATORIAS" in prompt, "Missing mandatory alerts section"
    assert "patrón de omisión" in prompt, "Missing public-services alert text"
    assert "servicios públicos regulados" in prompt
    assert "cortes de agua/luz" in prompt
    assert "Vigencia de Poder" in prompt, "Missing Sunarp note"
    assert "Sunarp" in prompt
    assert "016-2024-JUS" in prompt, "Missing current reglamento rule"
    assert "003-2013-JUS" in prompt, "Missing derogated reglamento in rule"


# --- 3. Admin document generator: tratamiento_datos PDF ---

def test_admin_tratamiento_datos_pdf_has_updated_citation(sess):
    payload = {
        "doc_type": "tratamiento_datos",
        "client_name": "TEST Junta Directiva Condominio X",
        "client_document": "20500000001",
        "client_address": "Av. Test 123, Lima",
        "condominium_name": "TEST Condominio",
        "representative_name": "Juan Pérez",
    }
    r = sess.post(f"{API}/admin/documents/generate", json=payload, timeout=25)
    assert r.status_code == 200, r.text
    assert r.headers.get("content-type", "").startswith("application/pdf")
    norm = _extract_pdf_text(r.content)
    assert "016-2024-JUS" in norm, f"Missing 016-2024-JUS. Extract: {norm[:800]}"
    assert "003-2013-JUS" in norm, f"Missing 003-2013-JUS. Extract: {norm[:800]}"


# --- 4. /privacidad page (LegalPage) ---

def test_privacy_page_shows_derogated_reglamento():
    r = requests.get(f"{BASE_URL}/privacidad", timeout=15)
    assert r.status_code == 200
    # SPA — content is client-side rendered, so scan the JS bundle indirectly by hitting the static source (not possible over the SPA HTML).
    # Instead, check the LegalPage.jsx source file.
    with open("/app/frontend/src/pages/LegalPage.jsx", "r", encoding="utf-8") as f:
        src = f.read()
    assert "016-2024-JUS" in src
    assert "003-2013-JUS" in src
    assert "derogó" in src or "derogo" in src


# --- 5. Regression: admin login + create audit + PDF still 200 ---

def test_regression_admin_flow_report_pdf_200(sess, mongo):
    r = sess.post(f"{API}/audits", json={"condominium_name": "TEST Regression PDF", "period": "2025-08"}, timeout=15)
    assert r.status_code == 200
    aid = r.json()["id"]
    try:
        mongo.audits.update_one(
            {"_id": ObjectId(aid)},
            {"$set": {"analysis": "## 1. RESUMEN EJECUTIVO\nRegression OK.\n", "status": "completada"}},
        )
        r = sess.get(f"{API}/audits/{aid}/report", timeout=20)
        assert r.status_code == 200
        assert r.content[:4] == b"%PDF"
        assert len(r.content) > 1000
    finally:
        sess.delete(f"{API}/audits/{aid}", timeout=10)
