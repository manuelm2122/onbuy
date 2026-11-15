"""Iteration 7 — Auto-classification + DOCUMENTOS_FALTANTES parsing tests."""
import os
import time
import pytest
import requests
from pathlib import Path
from pymongo import MongoClient
from bson import ObjectId

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://proyecto-nuevo-10--3sst8oxb.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
ADMIN_EMAIL = "admin@onbuysolutions.com"
ADMIN_PASSWORD = "OnBuy2026!"
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")
SAMPLES_DIR = Path("/app/backend/sample_files")
SERVER_PY = Path("/app/backend/server.py")
AUDIT_JSX = Path("/app/frontend/src/pages/AuditDetail.jsx")


@pytest.fixture(scope="module")
def sess():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200
    return s


@pytest.fixture(scope="module")
def mongo():
    return MongoClient(MONGO_URL)[DB_NAME]


# ---- Upload without category ----

def test_upload_no_category_field_creates_clasificando(sess):
    r = sess.post(f"{API}/audits", json={"condominium_name": "TEST NoCategory", "period": "2026-01"}, timeout=15)
    aid = r.json()["id"]
    try:
        files = [("files", ("recibos_mantenimiento_enero_2025.csv",
                            (SAMPLES_DIR / "recibos_mantenimiento_enero_2025.csv").read_bytes(), "text/csv"))]
        r_up = sess.post(f"{API}/audits/{aid}/documents", files=files, timeout=30)
        assert r_up.status_code == 200, r_up.text
        docs = r_up.json()
        assert len(docs) == 1
        # Initial category must be 'clasificando' (auto-classify runs in background)
        assert docs[0]["category"] == "clasificando", f"expected clasificando, got {docs[0]['category']}"
    finally:
        sess.delete(f"{API}/audits/{aid}", timeout=10)


def test_upload_multiple_samples_get_classified(sess):
    """Upload 3 real samples w/o category, poll until none are 'clasificando' (max 90s)."""
    r = sess.post(f"{API}/audits", json={"condominium_name": "TEST AutoClassify", "period": "2026-02"}, timeout=15)
    aid = r.json()["id"]
    try:
        samples = [
            "estado_cuenta_enero_2025.pdf",
            "factura_jardineria_E001-0789.pdf",
            "recibos_mantenimiento_enero_2025.csv",
        ]
        files = []
        for name in samples:
            data = (SAMPLES_DIR / name).read_bytes()
            mime = "application/pdf" if name.endswith(".pdf") else "text/csv"
            files.append(("files", (name, data, mime)))
        r_up = sess.post(f"{API}/audits/{aid}/documents", files=files, timeout=60)
        assert r_up.status_code == 200, r_up.text
        assert all(d["category"] == "clasificando" for d in r_up.json())

        # Poll
        final_cats = {}
        deadline = time.time() + 90
        while time.time() < deadline:
            r_list = sess.get(f"{API}/audits/{aid}/documents", timeout=10)
            docs = r_list.json()
            if all(d["category"] != "clasificando" for d in docs):
                final_cats = {d["filename"]: d["category"] for d in docs}
                break
            time.sleep(3)
        assert final_cats, f"documents still 'clasificando' after 90s"
        # Validate expected classifications (E1 verified these mapping)
        assert final_cats.get("estado_cuenta_enero_2025.pdf") == "estado_cuenta", final_cats
        assert final_cats.get("factura_jardineria_E001-0789.pdf") == "factura", final_cats
        assert final_cats.get("recibos_mantenimiento_enero_2025.csv") == "recibo", final_cats
    finally:
        sess.delete(f"{API}/audits/{aid}", timeout=10)


# ---- AUDIT_SYSTEM_PROMPT contains DOCUMENTOS_FALTANTES instruction ----

def test_system_prompt_has_documentos_faltantes_instruction():
    src = SERVER_PY.read_text(encoding="utf-8")
    assert "INSTRUCCIÓN FINAL OBLIGATORIA" in src
    assert "DOCUMENTOS_FALTANTES:" in src
    assert "NINGUNO" in src


# ---- Backend removes DOCUMENTOS_FALTANTES marker + persists missing_documents ----

def test_analyze_marker_parsing_via_mongo_seed(sess, mongo):
    """Seed an audit with missing_documents to verify Audit model surfaces field via GET."""
    r = sess.post(f"{API}/audits", json={"condominium_name": "TEST MissingDocs", "period": "2026-03"}, timeout=15)
    aid = r.json()["id"]
    try:
        missing = ["Recibos de luz y agua de áreas comunes", "Contratos con proveedores"]
        mongo.audits.update_one(
            {"_id": ObjectId(aid)},
            {"$set": {
                "analysis": "## 1. RESUMEN EJECUTIVO\nInforme completo.\n",
                "status": "completada",
                "missing_documents": missing,
            }},
        )
        r_get = sess.get(f"{API}/audits/{aid}", timeout=10)
        assert r_get.status_code == 200
        data = r_get.json()
        assert data.get("missing_documents") == missing
        # analysis stored MUST NOT contain the DOCUMENTOS_FALTANTES marker
        assert "DOCUMENTOS_FALTANTES" not in (data.get("analysis") or "")

        # PDF report still works with missing_documents populated
        r_pdf = sess.get(f"{API}/audits/{aid}/report", timeout=20)
        assert r_pdf.status_code == 200
        assert r_pdf.headers.get("content-type", "").startswith("application/pdf")
    finally:
        sess.delete(f"{API}/audits/{aid}", timeout=10)


# ---- Frontend source guarantees ----

def test_frontend_source_has_banner_and_dropzone():
    src = AUDIT_JSX.read_text(encoding="utf-8")
    assert 'data-testid="required-docs-banner"' in src
    assert 'data-testid="upload-dropzone"' in src
    assert 'data-testid="file-input"' in src
    assert 'data-testid="missing-docs-warning"' in src
    # dropdown selector must be gone
    assert 'doc-category-select' not in src
    # marker filter regex present
    assert "DOCUMENTOS_FALTANTES" in src


# ---- Regression: invalid extension still rejected ----

def test_upload_invalid_extension_rejected(sess):
    r = sess.post(f"{API}/audits", json={"condominium_name": "TEST BadExt", "period": "2026-04"}, timeout=15)
    aid = r.json()["id"]
    try:
        r_up = sess.post(f"{API}/audits/{aid}/documents",
                         files={"files": ("bad.exe", b"x", "application/octet-stream")},
                         timeout=10)
        assert r_up.status_code == 400
    finally:
        sess.delete(f"{API}/audits/{aid}", timeout=10)
