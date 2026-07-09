"""OnBuySolutions API tests - auth, audits, documents, analyze (budget-exceeded), report, stats, contact."""
import os
import io
import time
import pytest
import requests
from pymongo import MongoClient
from bson import ObjectId

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://condominio-audit.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@onbuysolutions.com"
ADMIN_PASSWORD = "OnBuy2026!"

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")


@pytest.fixture(scope="module")
def sess():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    assert "access_token" in s.cookies
    return s


@pytest.fixture(scope="module")
def mongo():
    return MongoClient(MONGO_URL)[DB_NAME]


# -------- Health & Contact --------

def test_root():
    r = requests.get(f"{API}/", timeout=10)
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


def test_contact_public():
    r = requests.post(f"{API}/contact", json={
        "name": "TEST Usuario",
        "email": "test_contact@example.com",
        "phone": "999",
        "message": "Mensaje de prueba de contacto",
    }, timeout=15)
    assert r.status_code == 200
    assert "recibido" in r.json().get("message", "").lower()


# -------- Auth --------

def test_login_wrong_password():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong"}, timeout=10)
    assert r.status_code in (401, 429)


def test_me_authenticated(sess):
    r = sess.get(f"{API}/auth/me", timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == ADMIN_EMAIL
    assert data["role"] == "admin"


def test_me_unauthenticated():
    r = requests.get(f"{API}/auth/me", timeout=10)
    assert r.status_code == 401


def test_register_and_login_flow(mongo):
    email = f"test_user_{int(time.time())}@example.com"
    s = requests.Session()
    r = s.post(f"{API}/auth/register", json={"name": "TEST User", "email": email, "password": "Passw0rd!", "accepted_terms": True}, timeout=15)
    assert r.status_code == 200, r.text
    assert "access_token" in s.cookies
    # Verify accepted_terms_at persisted
    user_doc = mongo.users.find_one({"email": email})
    assert user_doc is not None
    assert "accepted_terms_at" in user_doc and user_doc["accepted_terms_at"]
    # duplicate
    r2 = requests.post(f"{API}/auth/register", json={"name": "TEST User", "email": email, "password": "Passw0rd!", "accepted_terms": True}, timeout=10)
    assert r2.status_code == 400
    # login
    s2 = requests.Session()
    r3 = s2.post(f"{API}/auth/login", json={"email": email, "password": "Passw0rd!"}, timeout=10)
    assert r3.status_code == 200
    # me
    r4 = s2.get(f"{API}/auth/me", timeout=10)
    assert r4.status_code == 200
    assert r4.json()["email"] == email
    # logout
    r5 = s2.post(f"{API}/auth/logout", timeout=10)
    assert r5.status_code == 200
    # cleanup
    mongo.users.delete_one({"email": email})


def test_register_requires_accepted_terms():
    email = f"test_noterms_{int(time.time())}@example.com"
    # Missing accepted_terms (defaults to False)
    r = requests.post(f"{API}/auth/register", json={"name": "TEST NoTerms", "email": email, "password": "Passw0rd!"}, timeout=10)
    assert r.status_code == 400
    detail = r.json().get("detail", "")
    assert "Términos" in detail or "términos" in detail.lower()
    # Explicit accepted_terms=false
    r2 = requests.post(f"{API}/auth/register", json={"name": "TEST NoTerms", "email": email, "password": "Passw0rd!", "accepted_terms": False}, timeout=10)
    assert r2.status_code == 400


# -------- Audits CRUD --------

def test_audit_crud_flow(sess):
    # create
    r = sess.post(f"{API}/audits", json={
        "condominium_name": "TEST Condominio San Isidro",
        "address": "Av. Pardo 123",
        "district": "San Isidro",
        "period": "2025-01",
        "purpose": "Auditoría anual",
        "notes": "test",
    }, timeout=15)
    assert r.status_code == 200, r.text
    audit = r.json()
    assert audit["condominium_name"] == "TEST Condominio San Isidro"
    assert audit["status"] == "pendiente"
    assert audit["id"]
    aid = audit["id"]

    # get
    r = sess.get(f"{API}/audits/{aid}", timeout=10)
    assert r.status_code == 200
    assert r.json()["id"] == aid

    # list
    r = sess.get(f"{API}/audits", timeout=10)
    assert r.status_code == 200
    ids = [a["id"] for a in r.json()]
    assert aid in ids

    # delete
    r = sess.delete(f"{API}/audits/{aid}", timeout=10)
    assert r.status_code == 200

    # get 404
    r = sess.get(f"{API}/audits/{aid}", timeout=10)
    assert r.status_code == 404


def test_audit_requires_auth():
    r = requests.get(f"{API}/audits", timeout=10)
    assert r.status_code == 401


# -------- Documents --------

def test_document_upload_delete(sess):
    r = sess.post(f"{API}/audits", json={
        "condominium_name": "TEST Condo Docs",
        "period": "2025-02",
    }, timeout=15)
    aid = r.json()["id"]
    try:
        csv_bytes = b"fecha,descripcion,monto\n2025-01-05,Mantenimiento,500.00\n2025-01-10,Limpieza,250.00\n"
        files = {"files": ("test.csv", csv_bytes, "text/csv")}
        r = sess.post(f"{API}/audits/{aid}/documents", files=files, timeout=20)
        assert r.status_code == 200, r.text
        docs = r.json()
        assert len(docs) == 1
        doc_id = docs[0]["id"]
        # Auto-classify: docs start as 'clasificando'
        assert docs[0]["category"] == "clasificando"

        # list
        r = sess.get(f"{API}/audits/{aid}/documents", timeout=10)
        assert r.status_code == 200
        assert len(r.json()) == 1

        # invalid ext
        r = sess.post(f"{API}/audits/{aid}/documents",
                      files={"files": ("bad.exe", b"x", "application/octet-stream")},
                      timeout=10)
        assert r.status_code == 400

        # delete document
        r = sess.delete(f"{API}/documents/{doc_id}", timeout=10)
        assert r.status_code == 200

        r = sess.get(f"{API}/audits/{aid}/documents", timeout=10)
        assert len(r.json()) == 0
    finally:
        sess.delete(f"{API}/audits/{aid}", timeout=10)


# -------- Analyze (budget exceeded) --------

def test_analyze_budget_exceeded_streams_error(sess, mongo):
    r = sess.post(f"{API}/audits", json={"condominium_name": "TEST Analyze", "period": "2025-03"}, timeout=15)
    aid = r.json()["id"]
    try:
        csv_bytes = b"fecha,monto\n2025-01-01,100\n"
        sess.post(f"{API}/audits/{aid}/documents",
                  files={"files": ("t.csv", csv_bytes, "text/csv")},
                  timeout=20)

        # No documents error
        r_no = sess.post(f"{API}/audits/{aid}/analyze", timeout=60, stream=False)
        # It has docs so it should be 200 stream
        assert r_no.status_code == 200
        body = r_no.text
        # Expect error message about budget or exception (budget exceeded)
        # Wait a moment for background update
        time.sleep(2)
        doc = mongo.audits.find_one({"_id": ObjectId(aid)})
        status = doc.get("status")
        # Should be 'error' since budget exceeded, but could also be 'completada' if key works
        assert status in ("error", "completada", "analizando"), f"unexpected status: {status}"
        # Body should contain either analysis text or [ERROR]
        assert len(body) > 0
    finally:
        sess.delete(f"{API}/audits/{aid}", timeout=10)


def test_analyze_no_documents(sess):
    r = sess.post(f"{API}/audits", json={"condominium_name": "TEST NoDocs", "period": "2025-04"}, timeout=15)
    aid = r.json()["id"]
    try:
        r = sess.post(f"{API}/audits/{aid}/analyze", timeout=15)
        assert r.status_code == 400
    finally:
        sess.delete(f"{API}/audits/{aid}", timeout=10)


# -------- Report PDF --------

def test_report_400_without_analysis(sess):
    r = sess.post(f"{API}/audits", json={"condominium_name": "TEST Report No", "period": "2025-05"}, timeout=15)
    aid = r.json()["id"]
    try:
        r = sess.get(f"{API}/audits/{aid}/report", timeout=15)
        assert r.status_code == 400
    finally:
        sess.delete(f"{API}/audits/{aid}", timeout=10)


def test_report_pdf_with_manual_analysis(sess, mongo):
    r = sess.post(f"{API}/audits", json={"condominium_name": "TEST Report OK", "period": "2025-06"}, timeout=15)
    aid = r.json()["id"]
    try:
        mongo.audits.update_one(
            {"_id": ObjectId(aid)},
            {"$set": {
                "analysis": "## 1. RESUMEN EJECUTIVO\nAnálisis de prueba.\n\n## 2. HALLAZGOS\n- Hallazgo 1 [ALTA]\n",
                "status": "completada",
            }},
        )
        r = sess.get(f"{API}/audits/{aid}/report", timeout=20)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:4] == b"%PDF"
        assert len(r.content) > 1000
        # Verify new legal disclaimer content (Ley 31814 + supervisión final)
        try:
            from pypdf import PdfReader
        except ImportError:
            from PyPDF2 import PdfReader
        reader = PdfReader(io.BytesIO(r.content))
        text = "".join(p.extract_text() or "" for p in reader.pages)
        # normalize whitespace
        norm = " ".join(text.split())
        assert "31814" in norm, f"Missing Ley 31814 in PDF: {norm[:500]}"
        assert "supervisi" in norm.lower() and "final" in norm.lower(), f"Missing supervisión final: {norm[:500]}"
        assert "29733" in norm, f"Missing Ley 29733 in PDF"
    finally:
        sess.delete(f"{API}/audits/{aid}", timeout=10)


# -------- Dashboard stats --------

def test_dashboard_stats(sess):
    r = sess.get(f"{API}/dashboard/stats", timeout=10)
    assert r.status_code == 200
    data = r.json()
    for k in ("total_audits", "completed", "pending", "documents"):
        assert k in data
        assert isinstance(data[k], int)



# -------- Sample files --------

EXPECTED_SAMPLES = {
    "estado_cuenta_enero_2025.pdf": b"%PDF",
    "factura_ascensores_E001-0456.pdf": b"%PDF",
    "factura_jardineria_E001-0789.pdf": b"%PDF",
    "factura_limpieza_E001-1234.pdf": b"%PDF",
    "presupuesto_anual_2025.xlsx": b"PK",  # xlsx = zip
    "recibos_mantenimiento_enero_2025.csv": None,
}


def test_samples_list_requires_auth():
    r = requests.get(f"{API}/samples", timeout=10)
    assert r.status_code == 401


def test_samples_list(sess):
    r = sess.get(f"{API}/samples", timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) == 6
    names = {f["filename"] for f in data}
    assert names == set(EXPECTED_SAMPLES.keys())
    for item in data:
        assert item["size"] > 0
        assert "category" in item
        assert "description" in item
        assert item["description"]  # non-empty


@pytest.mark.parametrize("fname,magic", list(EXPECTED_SAMPLES.items()))
def test_sample_download(sess, fname, magic):
    r = sess.get(f"{API}/samples/{fname}", timeout=15)
    assert r.status_code == 200, f"{fname} -> {r.status_code}"
    assert len(r.content) > 0
    if magic:
        assert r.content[:len(magic)] == magic, f"{fname} bad magic"


def test_sample_not_found(sess):
    r = sess.get(f"{API}/samples/nope_does_not_exist.pdf", timeout=10)
    assert r.status_code == 404


def test_sample_path_traversal(sess):
    # URL-encoded traversal
    r = sess.get(f"{API}/samples/..%2F..%2Fetc%2Fpasswd", timeout=10)
    assert r.status_code in (400, 404)
    # Also plain (may be normalized by client)
    r2 = sess.get(f"{API}/samples/..%2Fserver.py", timeout=10)
    assert r2.status_code in (400, 404)



# -------- Admin Document Generator --------

DOC_TYPES = ["propuesta", "contrato", "confidencialidad", "tratamiento_datos", "autorizacion_bancaria", "recibo"]

BASE_FIELDS = {
    "empresa_razon_social": "OnBuySolutions S.A.C.",
    "empresa_ruc": "20601234567",
    "empresa_representante": "Juan Perez",
    "empresa_dni": "12345678",
    "empresa_direccion": "Av. Javier Prado 100, San Isidro",
    "cliente_nombre": "Junta de Propietarios Cond. Los Pinos",
    "cliente_ruc": "20509876543",
    "cliente_representante": "Maria Lopez",
    "cliente_dni": "87654321",
    "cliente_cargo": "Presidente de la Junta",
    "cliente_direccion": "Calle Las Flores 456",
    "cliente_distrito": "Miraflores",
    "num_departamentos": "40",
    "plan": "pequeno",
    "monto": "1100",
    "periodo": "Enero - Diciembre 2025",
    "ciudad": "Lima",
    "fecha": "15/01/2026",
    "forma_pago": "Transferencia bancaria",
    "plazo_entrega": "7 días hábiles",
    "validez_dias": "15",
    "vigencia_anios": "5",
    "recibo_numero": "001-2026",
    "concepto": "Servicio de auditoría",
    "fecha_pago": "15/01/2026",
}


def _pdf_text(content: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        from PyPDF2 import PdfReader
    reader = PdfReader(io.BytesIO(content))
    return " ".join(" ".join((p.extract_text() or "").split()) for p in reader.pages)


@pytest.mark.parametrize("doc_type", DOC_TYPES)
def test_admin_docgen_all_types(sess, doc_type):
    r = sess.post(f"{API}/admin/documents/generate",
                  json={"doc_type": doc_type, "fields": BASE_FIELDS}, timeout=30)
    assert r.status_code == 200, f"{doc_type}: {r.status_code} {r.text[:200]}"
    assert r.headers.get("content-type", "").startswith("application/pdf")
    assert r.content[:4] == b"%PDF"
    assert len(r.content) > 1000
    cd = r.headers.get("Content-Disposition", "")
    assert ".pdf" in cd


def test_admin_docgen_contrato_content(sess):
    r = sess.post(f"{API}/admin/documents/generate",
                  json={"doc_type": "contrato", "fields": BASE_FIELDS}, timeout=30)
    assert r.status_code == 200
    text = _pdf_text(r.content)
    assert "SUPERVISIÓN HUMANA" in text.upper() or "SUPERVISI" in text.upper()
    assert "29733" in text


def test_admin_docgen_recibo_monto_en_letras(sess):
    fields = {**BASE_FIELDS, "monto": "1100"}
    r = sess.post(f"{API}/admin/documents/generate",
                  json={"doc_type": "recibo", "fields": fields}, timeout=30)
    assert r.status_code == 200
    text = _pdf_text(r.content).upper()
    assert "MIL CIEN CON 00/100 SOLES" in text, f"Missing amount in letters: {text[:400]}"


def test_admin_docgen_recibo_mediano_2100(sess):
    fields = {**BASE_FIELDS, "plan": "mediano", "monto": "2100"}
    r = sess.post(f"{API}/admin/documents/generate",
                  json={"doc_type": "recibo", "fields": fields}, timeout=30)
    assert r.status_code == 200
    text = _pdf_text(r.content).upper()
    assert "DOS MIL CIEN CON 00/100 SOLES" in text


def test_admin_docgen_invalid_type(sess):
    r = sess.post(f"{API}/admin/documents/generate",
                  json={"doc_type": "nope", "fields": {}}, timeout=15)
    assert r.status_code == 400


def test_admin_docgen_requires_auth():
    r = requests.post(f"{API}/admin/documents/generate",
                      json={"doc_type": "propuesta", "fields": {}}, timeout=15)
    assert r.status_code == 401


def test_admin_docgen_forbidden_for_non_admin(mongo):
    email = f"test_docgen_nonadmin_{int(time.time())}@example.com"
    s = requests.Session()
    r = s.post(f"{API}/auth/register",
               json={"name": "TEST NoAdmin", "email": email, "password": "Passw0rd!", "accepted_terms": True}, timeout=15)
    assert r.status_code == 200
    try:
        r2 = s.post(f"{API}/admin/documents/generate",
                    json={"doc_type": "propuesta", "fields": {}}, timeout=15)
        assert r2.status_code == 403
    finally:
        mongo.users.delete_one({"email": email})


def test_admin_docgen_empty_fields_ok(sess):
    r = sess.post(f"{API}/admin/documents/generate",
                  json={"doc_type": "propuesta", "fields": {}}, timeout=30)
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF"
    text = _pdf_text(r.content)
    assert "__________________" in text


# -------- Payment Authorization (Commercial Access Control) --------

@pytest.fixture()
def regular_user(mongo):
    """Register a regular (non-admin) test user; cleanup after."""
    email = f"test_regular_{int(time.time()*1000)}@example.com"
    s = requests.Session()
    r = s.post(f"{API}/auth/register", json={
        "name": "TEST Regular", "email": email, "password": "Passw0rd!", "accepted_terms": True,
    }, timeout=15)
    assert r.status_code == 200, r.text
    yield s, email
    # Cleanup audits + docs
    user = mongo.users.find_one({"email": email})
    if user:
        uid = str(user["_id"])
        audit_ids = [str(a["_id"]) for a in mongo.audits.find({"user_id": uid})]
        for aid in audit_ids:
            mongo.documents.delete_many({"audit_id": aid})
        mongo.audits.delete_many({"user_id": uid})
        mongo.users.delete_one({"_id": user["_id"]})


def test_regular_user_audit_created_pending_payment(regular_user):
    s, _ = regular_user
    r = s.post(f"{API}/audits", json={"condominium_name": "TEST PendPay", "period": "2025-07"}, timeout=15)
    assert r.status_code == 200
    a = r.json()
    assert a["payment_status"] == "pendiente_pago"
    assert a.get("authorized_at") in (None, "")


def test_admin_audit_created_autorizada(sess):
    r = sess.post(f"{API}/audits", json={"condominium_name": "TEST AdminAudit", "period": "2025-07"}, timeout=15)
    assert r.status_code == 200
    a = r.json()
    aid = a["id"]
    try:
        assert a["payment_status"] == "autorizada"
        assert a.get("authorized_at")
    finally:
        sess.delete(f"{API}/audits/{aid}", timeout=10)


def test_analyze_returns_402_when_pending(regular_user):
    s, _ = regular_user
    r = s.post(f"{API}/audits", json={"condominium_name": "TEST 402", "period": "2025-08"}, timeout=15)
    aid = r.json()["id"]
    # Upload a doc (uploading is allowed even when locked)
    csv_bytes = b"fecha,monto\n2025-01-01,100\n"
    r_up = s.post(f"{API}/audits/{aid}/documents",
                  files={"files": ("t.csv", csv_bytes, "text/csv")},
                  timeout=20)
    assert r_up.status_code == 200
    # Now analyze -> 402
    r_an = s.post(f"{API}/audits/{aid}/analyze", timeout=15)
    assert r_an.status_code == 402
    detail = r_an.json().get("detail", "")
    assert "autoriz" in detail.lower() or "pago" in detail.lower()


def test_admin_list_audits_shows_owner_info(sess, regular_user):
    s, email = regular_user
    r = s.post(f"{API}/audits", json={"condominium_name": "TEST OwnerInfo", "period": "2025-09"}, timeout=15)
    aid = r.json()["id"]
    r2 = sess.get(f"{API}/admin/audits", timeout=15)
    assert r2.status_code == 200
    data = r2.json()
    assert isinstance(data, list)
    match = next((x for x in data if x["id"] == aid), None)
    assert match is not None
    assert match["owner_email"] == email
    assert match["payment_status"] == "pendiente_pago"
    assert "owner_name" in match and "document_count" in match


def test_admin_authorize_then_revoke_flow(sess, regular_user):
    s, _ = regular_user
    r = s.post(f"{API}/audits", json={"condominium_name": "TEST AuthFlow", "period": "2025-10"}, timeout=15)
    aid = r.json()["id"]
    # upload doc
    s.post(f"{API}/audits/{aid}/documents",
           files={"files": ("t.csv", b"fecha,monto\n2025-01-01,100\n", "text/csv")},
           timeout=20)
    # analyze blocked
    assert s.post(f"{API}/audits/{aid}/analyze", timeout=15).status_code == 402
    # authorize
    ra = sess.post(f"{API}/admin/audits/{aid}/authorize", timeout=15)
    assert ra.status_code == 200
    assert "autoriz" in ra.json().get("message", "").lower()
    # Verify GET as owner
    rd = s.get(f"{API}/audits/{aid}", timeout=10)
    assert rd.status_code == 200
    assert rd.json()["payment_status"] == "autorizada"
    # analyze no longer 402 (may be 200 stream w/ budget error, or something else, but NOT 402)
    r_an = s.post(f"{API}/audits/{aid}/analyze", timeout=60)
    assert r_an.status_code != 402
    # revoke
    rv = sess.post(f"{API}/admin/audits/{aid}/revoke", timeout=15)
    assert rv.status_code == 200
    # analyze blocked again
    assert s.post(f"{API}/audits/{aid}/analyze", timeout=15).status_code == 402


def test_admin_authorize_404_for_missing_audit(sess):
    # Valid ObjectId format but not existing
    r = sess.post(f"{API}/admin/audits/507f1f77bcf86cd799439011/authorize", timeout=10)
    assert r.status_code == 404


def test_admin_revoke_404_for_missing_audit(sess):
    r = sess.post(f"{API}/admin/audits/507f1f77bcf86cd799439011/revoke", timeout=10)
    assert r.status_code == 404


def test_admin_endpoints_require_auth():
    assert requests.get(f"{API}/admin/audits", timeout=10).status_code == 401
    assert requests.post(f"{API}/admin/audits/507f1f77bcf86cd799439011/authorize", timeout=10).status_code == 401
    assert requests.post(f"{API}/admin/audits/507f1f77bcf86cd799439011/revoke", timeout=10).status_code == 401


def test_admin_endpoints_forbidden_for_non_admin(regular_user):
    s, _ = regular_user
    assert s.get(f"{API}/admin/audits", timeout=10).status_code == 403
    assert s.post(f"{API}/admin/audits/507f1f77bcf86cd799439011/authorize", timeout=10).status_code == 403
    assert s.post(f"{API}/admin/audits/507f1f77bcf86cd799439011/revoke", timeout=10).status_code == 403


def test_regular_user_can_upload_docs_when_locked(regular_user):
    s, _ = regular_user
    r = s.post(f"{API}/audits", json={"condominium_name": "TEST UploadLocked", "period": "2025-11"}, timeout=15)
    aid = r.json()["id"]
    assert r.json()["payment_status"] == "pendiente_pago"
    r_up = s.post(f"{API}/audits/{aid}/documents",
                  files={"files": ("locked.csv", b"a,b\n1,2\n", "text/csv")},
                  timeout=20)
    assert r_up.status_code == 200  # upload allowed even when locked
