"""
Consulting module tests — Iteration 9.
LLM budget is TIGHT: this suite spends ~2 chat calls (turn1+turn2 memory), 1 chat
call with PDF attachment, 1 chat call for document generation, 1 final-report,
1 image. All test cases are cleaned up at the end (final teardown fixture).
Regression: also verifies admin listings still respond.
"""
import os
import io
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
ADMIN_EMAIL = "admin@onbuysolutions.com"
ADMIN_PASSWORD = "OnBuy2026!"
CLIENT_EMAIL = "cliente@test.com"
CLIENT_PASSWORD = "Cliente123!"

SAMPLE_PDF = "/app/backend/sample_files/factura_limpieza_E001-1234.pdf"


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"Login {email} failed: {r.status_code} {r.text[:200]}"
    return s


@pytest.fixture(scope="module")
def admin():
    return _login(ADMIN_EMAIL, ADMIN_PASSWORD)


@pytest.fixture(scope="module")
def client_user():
    # ensure exists
    tmp = requests.Session()
    tmp.post(f"{BASE_URL}/api/auth/register", json={
        "name": "Cliente Test", "email": CLIENT_EMAIL, "password": CLIENT_PASSWORD, "accepted_terms": True
    }, timeout=15)
    return _login(CLIENT_EMAIL, CLIENT_PASSWORD)


CREATED_IDS = []


@pytest.fixture(scope="module")
def case_id(admin):
    r = admin.post(f"{BASE_URL}/api/admin/cases",
                   json={"title": "TEST_Caso_Consultoria_Iter9", "description": "Prueba automatizada"},
                   timeout=20)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["title"] == "TEST_Caso_Consultoria_Iter9"
    assert data["status"] == "activo"
    assert "id" in data
    CREATED_IDS.append(data["id"])
    return data["id"]


def _read_stream(session, url, data, files=None, timeout=180):
    with session.post(url, data=data, files=files, stream=True, timeout=timeout) as r:
        assert r.status_code == 200, f"Chat failed: {r.status_code} {r.text[:300]}"
        buf = []
        for chunk in r.iter_content(chunk_size=None, decode_unicode=True):
            if chunk:
                buf.append(chunk)
        return "".join(buf)


# ---------- CRUD ----------
class TestCRUD:
    def test_list_cases(self, admin, case_id):
        r = admin.get(f"{BASE_URL}/api/admin/cases", timeout=15)
        assert r.status_code == 200
        ids = [c["id"] for c in r.json()]
        assert case_id in ids
        item = next(c for c in r.json() if c["id"] == case_id)
        assert "message_count" in item
        assert "updated_at" in item
        assert "final_report" in item  # key present (None or dict)

    def test_get_case_detail(self, admin, case_id):
        r = admin.get(f"{BASE_URL}/api/admin/cases/{case_id}", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "case" in d and "messages" in d
        assert d["case"]["id"] == case_id

    def test_update_case_status_invalid(self, admin, case_id):
        r = admin.put(f"{BASE_URL}/api/admin/cases/{case_id}",
                      json={"status": "loquesea"}, timeout=15)
        assert r.status_code == 400

    def test_update_case_valid(self, admin, case_id):
        r = admin.put(f"{BASE_URL}/api/admin/cases/{case_id}",
                      json={"title": "TEST_Caso_Consultoria_Iter9", "description": "Actualizado"},
                      timeout=15)
        assert r.status_code == 200
        assert r.json()["description"] == "Actualizado"

    def test_client_forbidden(self, client_user, case_id):
        # Non-admin should be 403 on all routes
        for verb, url in [
            ("get", f"{BASE_URL}/api/admin/cases"),
            ("get", f"{BASE_URL}/api/admin/cases/{case_id}"),
            ("delete", f"{BASE_URL}/api/admin/cases/{case_id}"),
        ]:
            r = getattr(client_user, verb)(url, timeout=15)
            assert r.status_code == 403, f"{verb} {url} → {r.status_code}"
        r = client_user.post(f"{BASE_URL}/api/admin/cases",
                             json={"title": "no"}, timeout=15)
        assert r.status_code == 403


# ---------- CHAT / MEMORY / ATTACHMENTS ----------
class TestChat:
    def test_chat_turn1_and_memory_turn2(self, admin, case_id):
        # Turn 1: give a specific number
        url = f"{BASE_URL}/api/admin/cases/{case_id}/chat"
        answer1 = _read_stream(admin, url, data={
            "text": "Registra este dato: el administrador retiró S/ 8,500 sin justificar el 12 de marzo. Responde en 2 líneas confirmando."
        })
        assert answer1 and len(answer1) > 20, f"Empty/short answer: {answer1!r}"

        # Turn 2: ask what amount was mentioned
        answer2 = _read_stream(admin, url, data={
            "text": "¿Qué monto exacto te mencioné en el mensaje anterior? Responde sólo con el monto."
        })
        assert "8,500" in answer2 or "8500" in answer2 or "8.500" in answer2, \
            f"Memory failed. Answer: {answer2!r}"

        # Verify persistence: both turns present as user+assistant pairs
        r = admin.get(f"{BASE_URL}/api/admin/cases/{case_id}", timeout=15)
        msgs = r.json()["messages"]
        roles = [m["role"] for m in msgs]
        assert roles.count("user") >= 2
        assert roles.count("assistant") >= 2

    def test_chat_with_pdf_attachment(self, admin, case_id):
        url = f"{BASE_URL}/api/admin/cases/{case_id}/chat"
        with open(SAMPLE_PDF, "rb") as f:
            files = {"files": ("factura_limpieza_E001-1234.pdf", f, "application/pdf")}
            answer = _read_stream(admin, url,
                                  data={"text": "Analiza esta factura en 3 líneas: emisor y monto total."},
                                  files=files, timeout=180)
        assert len(answer) > 30
        # attachment stored
        r = admin.get(f"{BASE_URL}/api/admin/cases/{case_id}", timeout=15)
        msgs = r.json()["messages"]
        atts = [a for m in msgs for a in m.get("attachments", [])]
        assert any(a["filename"] == "factura_limpieza_E001-1234.pdf" for a in atts)
        stored = next(a["stored_name"] for a in atts if a["filename"] == "factura_limpieza_E001-1234.pdf")
        # download
        rf = admin.get(f"{BASE_URL}/api/admin/cases/{case_id}/files/{stored}", timeout=30)
        assert rf.status_code == 200
        assert rf.headers.get("content-type", "").startswith("application/pdf")

    def test_chat_unsupported_extension(self, admin, case_id):
        url = f"{BASE_URL}/api/admin/cases/{case_id}/chat"
        files = {"files": ("malware.exe", io.BytesIO(b"MZ\x90\x00"), "application/octet-stream")}
        r = admin.post(url, data={"text": "toma"}, files=files, timeout=30)
        assert r.status_code == 400
        assert "no soportado" in r.text.lower() or "formato" in r.text.lower()


# ---------- DOCUMENT / EXPORT / LIBRARY ----------
class TestDocuments:
    def test_document_generation_and_export(self, admin, case_id):
        url = f"{BASE_URL}/api/admin/cases/{case_id}/chat"
        answer = _read_stream(admin, url, data={
            "text": "Redacta ahora una CARTA NOTARIAL DE REQUERIMIENTO breve al administrador exigiéndole rendir cuentas por los S/ 8,500. Usa los marcadores obligatorios."
        }, timeout=180)
        assert "<<<DOCUMENTO" in answer and "<<<FIN_DOCUMENTO>>>" in answer, \
            f"No delimiters in answer: {answer[:500]!r}"

        # find the assistant message with has_document
        r = admin.get(f"{BASE_URL}/api/admin/cases/{case_id}", timeout=15)
        msgs = r.json()["messages"]
        doc_msg = next((m for m in reversed(msgs) if m["role"] == "assistant" and m.get("has_document")), None)
        assert doc_msg is not None, "No assistant message with has_document=true"

        # library lists it
        rl = admin.get(f"{BASE_URL}/api/admin/cases/{case_id}/documents", timeout=15)
        assert rl.status_code == 200
        docs = rl.json()
        assert any(d["message_id"] == doc_msg["id"] for d in docs)

        # export only_document PDF
        rp = admin.post(f"{BASE_URL}/api/admin/cases/{case_id}/export-pdf",
                        json={"message_id": doc_msg["id"], "only_document": True, "doc_index": 0},
                        timeout=30)
        assert rp.status_code == 200
        assert rp.content[:4] == b"%PDF"

        # doc_index out of range
        rp2 = admin.post(f"{BASE_URL}/api/admin/cases/{case_id}/export-pdf",
                         json={"message_id": doc_msg["id"], "only_document": True, "doc_index": 99},
                         timeout=15)
        assert rp2.status_code == 404

        # only_document=True on a message without markers → 400
        user_msg_id = next(m["id"] for m in msgs if m["role"] == "user")
        rp3 = admin.post(f"{BASE_URL}/api/admin/cases/{case_id}/export-pdf",
                         json={"message_id": user_msg_id, "only_document": True},
                         timeout=15)
        assert rp3.status_code == 400


# ---------- IMAGE ----------
class TestImage:
    def test_generate_image(self, admin, case_id):
        r = admin.post(f"{BASE_URL}/api/admin/cases/{case_id}/generate-image",
                       json={"prompt": "Diagrama simple del flujo de fondos entre condominio y proveedor, minimalista."},
                       timeout=180)
        assert r.status_code == 200, r.text[:300]
        msg = r.json()
        assert msg["attachments"], "No attachment on generated-image response"
        att = msg["attachments"][0]
        assert att["kind"] == "generated"
        assert att["mime_type"].startswith("image/")
        # download
        rf = admin.get(f"{BASE_URL}/api/admin/cases/{case_id}/files/{att['stored_name']}", timeout=30)
        assert rf.status_code == 200
        assert rf.headers.get("content-type", "").startswith("image/")


# ---------- FINAL REPORT ----------
class TestFinalReport:
    def test_final_report_empty_case_400(self, admin):
        r = admin.post(f"{BASE_URL}/api/admin/cases",
                       json={"title": "TEST_EmptyCase_Iter9"}, timeout=15)
        cid = r.json()["id"]
        CREATED_IDS.append(cid)
        rr = admin.post(f"{BASE_URL}/api/admin/cases/{cid}/final-report", timeout=30)
        assert rr.status_code == 400

    def test_final_report_ok(self, admin, case_id):
        rr = admin.post(f"{BASE_URL}/api/admin/cases/{case_id}/final-report", timeout=180)
        assert rr.status_code == 200, rr.text[:300]
        data = rr.json()
        assert data.get("stored_name") and data.get("filename") and data.get("generated_at")
        # Case now has final_report in list
        rl = admin.get(f"{BASE_URL}/api/admin/cases", timeout=15)
        it = next(c for c in rl.json() if c["id"] == case_id)
        assert it["final_report"] is not None
        assert it["final_report"]["stored_name"] == data["stored_name"]
        # Download
        rf = admin.get(f"{BASE_URL}/api/admin/cases/{case_id}/files/{data['stored_name']}", timeout=30)
        assert rf.status_code == 200
        assert rf.content[:4] == b"%PDF"


# ---------- REGRESSION ----------
class TestRegression:
    def test_admin_users_list(self, admin):
        r = admin.get(f"{BASE_URL}/api/admin/users", timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_admin_settings(self, admin):
        r = admin.get(f"{BASE_URL}/api/admin/settings", timeout=15)
        assert r.status_code == 200
        # llm_key must be masked
        assert "llm_key" not in r.json() or not r.json().get("llm_key")

    def test_public_settings(self):
        r = requests.get(f"{BASE_URL}/api/public/settings", timeout=15)
        assert r.status_code == 200


# ---------- TEARDOWN: delete cases we created ----------
@pytest.fixture(scope="module", autouse=True)
def _cleanup(admin):
    yield
    for cid in CREATED_IDS:
        try:
            admin.delete(f"{BASE_URL}/api/admin/cases/{cid}", timeout=15)
        except Exception:
            pass
