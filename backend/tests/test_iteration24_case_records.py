"""Iteration 24: case records — ledger, facts, evidence, checklist, bundle, zip, permisos."""
import io
import os
import zipfile

import pytest
import requests
from dotenv import load_dotenv
from pypdf import PdfReader

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
ADMIN = ("admin@onbuysolutions.com", "OnBuy2026!")
CLIENT = ("cliente.prueba@ejemplo.com", "Cliente2026!")


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=20)
    assert r.status_code == 200, f"login {email}: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def admin():
    return _login(*ADMIN)


@pytest.fixture(scope="module")
def client():
    return _login(*CLIENT)


@pytest.fixture(scope="module")
def admin_case(admin):
    r = admin.post(f"{BASE_URL}/api/cases", json={"title": "TEST_iter24 records", "description": "auto"}, timeout=20)
    assert r.status_code == 200, r.text
    cid = r.json()["id"]
    yield cid
    admin.delete(f"{BASE_URL}/api/cases/{cid}", timeout=20)


@pytest.fixture(scope="module")
def client_case(client):
    r = client.post(f"{BASE_URL}/api/cases", json={"title": "TEST_iter24 client", "description": "auto"}, timeout=20)
    assert r.status_code == 200, r.text
    cid = r.json()["id"]
    yield cid
    client.delete(f"{BASE_URL}/api/cases/{cid}", timeout=20)


# ---------- LEDGER ----------

class TestLedger:
    def test_add_recurring_cargo_then_pago_and_balance(self, admin, admin_case):
        r = admin.post(
            f"{BASE_URL}/api/cases/{admin_case}/ledger",
            data={"type": "cargo", "date": "2025-01-31", "amount": "1500", "concept": "Renta",
                  "repeat_until": "2025-04"}, timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        assert len(data["entries"]) == 4
        dates = [e["date"] for e in data["entries"]]
        assert dates == ["2025-01-31", "2025-02-28", "2025-03-31", "2025-04-30"]
        assert data["total_cargos"] == 6000.0
        assert data["saldo"] == 6000.0

        r = admin.post(
            f"{BASE_URL}/api/cases/{admin_case}/ledger",
            data={"type": "pago", "date": "2025-02-10", "amount": "500", "concept": "Abono"}, timeout=20)
        assert r.status_code == 200
        data = r.json()
        assert data["saldo"] == 5500.0
        # balance accumulated chronologically
        feb_pago = next(e for e in data["entries"] if e["date"] == "2025-02-10")
        assert feb_pago["balance"] == 1000.0  # Jan 31 (+1500) → Feb 10 pago (-500) = 1000

    def test_validations(self, admin, admin_case):
        bad = [
            ({"type": "cargo", "date": "2025-01-01", "amount": "0", "concept": "test"}, 422),
            ({"type": "cargo", "date": "2025-01-01", "amount": "-5", "concept": "test"}, 422),
            ({"type": "foo", "date": "2025-01-01", "amount": "1", "concept": "test"}, 422),
            ({"type": "cargo", "date": "2025-13-45", "amount": "1", "concept": "test"}, 400),
        ]
        for data, code in bad:
            r = admin.post(f"{BASE_URL}/api/cases/{admin_case}/ledger", data=data, timeout=20)
            assert r.status_code == code, f"{data} -> {r.status_code} {r.text}"

    def test_repeat_until_too_far(self, admin, admin_case):
        r = admin.post(f"{BASE_URL}/api/cases/{admin_case}/ledger",
                       data={"type": "cargo", "date": "2020-01-01", "amount": "1", "concept": "test",
                             "repeat_until": "2035-01"}, timeout=20)
        assert r.status_code == 400

    def test_file_ext_forbidden(self, admin, admin_case):
        files = {"file": ("evil.py", b"print(1)", "text/x-python")}
        r = admin.post(f"{BASE_URL}/api/cases/{admin_case}/ledger",
                       data={"type": "cargo", "date": "2025-01-01", "amount": "10", "concept": "test"},
                       files=files, timeout=20)
        assert r.status_code == 400

    def test_stored_name_not_in_case(self, admin, admin_case):
        r = admin.post(f"{BASE_URL}/api/cases/{admin_case}/ledger",
                       data={"type": "cargo", "date": "2025-01-01", "amount": "10", "concept": "test",
                             "stored_name": "nope.pdf"}, timeout=20)
        assert r.status_code == 400

    def test_currency(self, admin, admin_case):
        r = admin.put(f"{BASE_URL}/api/cases/{admin_case}/ledger/currency", json={"currency": "USD"}, timeout=20)
        assert r.status_code == 200
        assert r.json()["currency"] == "USD"
        r = admin.put(f"{BASE_URL}/api/cases/{admin_case}/ledger/currency", json={"currency": "EUR"}, timeout=20)
        assert r.status_code == 422
        admin.put(f"{BASE_URL}/api/cases/{admin_case}/ledger/currency", json={"currency": "PEN"}, timeout=20)

    def test_delete_bad_id(self, admin, admin_case):
        r = admin.delete(f"{BASE_URL}/api/cases/{admin_case}/ledger/xxxx", timeout=20)
        assert r.status_code == 404

    def test_export(self, admin, admin_case):
        # has entries from earlier test
        r = admin.post(f"{BASE_URL}/api/cases/{admin_case}/ledger/export", timeout=20)
        assert r.status_code == 200, r.text
        msg_id = r.json()["message_id"]
        g = admin.get(f"{BASE_URL}/api/cases/{admin_case}", timeout=20).json()
        msg = next(m for m in g["messages"] if m.get("id") == msg_id or m.get("_id") == msg_id)
        assert msg["role"] == "assistant"
        assert msg.get("kind") == "record"
        assert "Estado de cuenta" in msg["content"]

    def test_export_empty(self, admin):
        r = admin.post(f"{BASE_URL}/api/cases", json={"title": "TEST_iter24 empty ledger"}, timeout=20)
        cid = r.json()["id"]
        try:
            r2 = admin.post(f"{BASE_URL}/api/cases/{cid}/ledger/export", timeout=20)
            assert r2.status_code == 400
        finally:
            admin.delete(f"{BASE_URL}/api/cases/{cid}", timeout=20)


# ---------- FACTS ----------

class TestFacts:
    def test_add_and_sort(self, admin, admin_case):
        r1 = admin.post(f"{BASE_URL}/api/cases/{admin_case}/facts",
                        data={"date": "2025-03-15", "text": "Hecho segundo"}, timeout=20)
        assert r1.status_code == 200, r1.text
        r2 = admin.post(f"{BASE_URL}/api/cases/{admin_case}/facts",
                        data={"date": "2025-01-10", "text": "Hecho primero"}, timeout=20)
        assert r2.status_code == 200
        lst = r2.json()
        dates = [f["date"] for f in lst]
        assert dates == sorted(dates)

    def test_export(self, admin, admin_case):
        r = admin.post(f"{BASE_URL}/api/cases/{admin_case}/facts/export", timeout=20)
        assert r.status_code == 200
        msg_id = r.json()["message_id"]
        g = admin.get(f"{BASE_URL}/api/cases/{admin_case}", timeout=20).json()
        msg = next(m for m in g["messages"] if m.get("id") == msg_id or m.get("_id") == msg_id)
        assert msg.get("kind") == "record"
        assert "PRIMERO.-" in msg["content"]
        assert "SEGUNDO.-" in msg["content"]
        assert msg["content"].index("PRIMERO.-") < msg["content"].index("SEGUNDO.-")

    def test_export_empty(self, admin):
        r = admin.post(f"{BASE_URL}/api/cases", json={"title": "TEST_iter24 empty facts"}, timeout=20)
        cid = r.json()["id"]
        try:
            r2 = admin.post(f"{BASE_URL}/api/cases/{cid}/facts/export", timeout=20)
            assert r2.status_code == 400
        finally:
            admin.delete(f"{BASE_URL}/api/cases/{cid}", timeout=20)


# ---------- CHECKLIST ----------

class TestChecklist:
    def test_get_initial(self, admin, admin_case):
        r = admin.get(f"{BASE_URL}/api/cases/{admin_case}/checklist", timeout=20)
        assert r.status_code == 200
        data = r.json()
        assert len(data["templates"]) == 6
        assert any(t["key"] == "desalojo" for t in data["templates"])

    def test_load_template(self, admin, admin_case):
        r = admin.put(f"{BASE_URL}/api/cases/{admin_case}/checklist", json={"tramite": "desalojo"}, timeout=20)
        assert r.status_code == 200
        assert len(r.json()["items"]) == 9

    def test_save_items(self, admin, admin_case):
        r = admin.put(f"{BASE_URL}/api/cases/{admin_case}/checklist",
                      json={"tramite": "desalojo", "items": [{"text": "Propio", "done": True}]}, timeout=20)
        assert r.status_code == 200
        assert r.json()["items"] == [{"text": "Propio", "done": True}]

    def test_bad_tramite(self, admin, admin_case):
        r = admin.put(f"{BASE_URL}/api/cases/{admin_case}/checklist", json={"tramite": "nope"}, timeout=20)
        assert r.status_code == 400


# ---------- EVIDENCE ----------

class TestEvidence:
    def test_list_and_download(self, admin, admin_case):
        # Upload a receipt via ledger
        files = {"file": ("recibo.pdf", open("/root/t/contrato.pdf", "rb"), "application/pdf")}
        r = admin.post(f"{BASE_URL}/api/cases/{admin_case}/ledger",
                       data={"type": "pago", "date": "2025-05-01", "amount": "100", "concept": "pago con comprobante"},
                       files=files, timeout=30)
        assert r.status_code == 200
        entry = next(e for e in r.json()["entries"] if e["concept"] == "pago con comprobante")
        stored = entry["file"]["stored_name"]

        r = admin.get(f"{BASE_URL}/api/cases/{admin_case}/evidence", timeout=20)
        assert r.status_code == 200
        ev = r.json()
        assert any(f["stored_name"] == stored and f["origin"] == "Pagos y deudas" for f in ev)

        r = admin.get(f"{BASE_URL}/api/cases/{admin_case}/files/{stored}", timeout=20)
        assert r.status_code == 200
        assert "recibo.pdf" in r.headers.get("content-disposition", "")


# ---------- BUNDLE ----------

class TestBundle:
    @pytest.fixture(scope="class")
    def bundle_case(self, admin):
        r = admin.post(f"{BASE_URL}/api/cases", json={"title": "TEST_iter24 bundle"}, timeout=20)
        cid = r.json()["id"]
        # upload 3 files: pdf (2p), jpg, mp3 via ledger receipts
        uploaded = []
        for path, mime in [("/root/t/contrato.pdf", "application/pdf"),
                           ("/root/t/foto.jpg", "image/jpeg"),
                           ("/root/t/audio.mp3", "audio/mpeg")]:
            with open(path, "rb") as fh:
                files = {"file": (os.path.basename(path), fh, mime)}
                r = admin.post(f"{BASE_URL}/api/cases/{cid}/ledger",
                               data={"type": "cargo", "date": "2025-01-01",
                                     "amount": "1", "concept": os.path.basename(path)},
                               files=files, timeout=30)
                assert r.status_code == 200, r.text
                entry = next(e for e in r.json()["entries"] if e["concept"] == os.path.basename(path))
                uploaded.append(entry["file"]["stored_name"])
        yield cid, uploaded
        admin.delete(f"{BASE_URL}/api/cases/{cid}", timeout=20)

    def test_empty_bundle(self, admin, bundle_case):
        cid, _ = bundle_case
        r = admin.post(f"{BASE_URL}/api/cases/{cid}/bundle", json={"files": []}, timeout=30)
        assert r.status_code == 400

    def test_alien_file(self, admin, bundle_case):
        cid, _ = bundle_case
        r = admin.post(f"{BASE_URL}/api/cases/{cid}/bundle",
                       json={"files": ["nope.pdf"]}, timeout=30)
        assert r.status_code == 400

    def test_folio_count_and_labels(self, admin, bundle_case):
        cid, uploaded = bundle_case
        # order: pdf (2p -> 3 folios w/ cover), jpg (1p -> 2 folios), mp3 (0p -> 1 folio cover)
        r = admin.post(f"{BASE_URL}/api/cases/{cid}/bundle", json={"files": uploaded}, timeout=60)
        assert r.status_code == 200, r.text
        reader = PdfReader(io.BytesIO(r.content))
        total = len(reader.pages)
        # front page (>=1) + 3 + 2 + 1 = 6 annex folios, front is at least 1
        # verify index on page 1
        page1 = reader.pages[0].extract_text() or ""
        assert "Índice de piezas y anexos" in page1 or "ndice" in page1
        assert "Anexo 1-A" in page1
        assert "Anexo 1-B" in page1
        assert "Anexo 1-C" in page1
        # every page should contain Folio N de T
        for i, p in enumerate(reader.pages, 1):
            t = p.extract_text() or ""
            assert f"de {total}" in t, f"Page {i} missing folio: {t[:100]}"

    def test_corrupt_pdf_does_not_break(self, admin, bundle_case):
        cid, _ = bundle_case
        files = {"file": ("corrupto.pdf", b"not a real pdf", "application/pdf")}
        r = admin.post(f"{BASE_URL}/api/cases/{cid}/ledger",
                       data={"type": "cargo", "date": "2025-02-01", "amount": "1", "concept": "corrupto"},
                       files=files, timeout=30)
        assert r.status_code == 200
        stored = next(e for e in r.json()["entries"] if e["concept"] == "corrupto")["file"]["stored_name"]
        r = admin.post(f"{BASE_URL}/api/cases/{cid}/bundle", json={"files": [stored]}, timeout=60)
        assert r.status_code == 200, r.text
        reader = PdfReader(io.BytesIO(r.content))
        assert len(reader.pages) >= 2

    def test_bundle_with_document_message(self, admin, bundle_case):
        from pymongo import MongoClient
        from bson import ObjectId
        cid, _ = bundle_case
        mongo = MongoClient(os.environ["MONGO_URL"])
        dbn = os.environ["DB_NAME"]
        from datetime import datetime, timezone
        content = "Introducción\n\n<<<DOCUMENTO: Carta notarial>>>\nSEÑOR...\n<<<FIN_DOCUMENTO>>>"
        res = mongo[dbn].case_messages.insert_one({
            "case_id": cid, "role": "assistant", "content": content,
            "attachments": [], "created_at": datetime.now(timezone.utc).isoformat(),
        })
        msg_id = str(res.inserted_id)
        try:
            r = admin.post(f"{BASE_URL}/api/cases/{cid}/bundle",
                           json={"message_id": msg_id, "doc_index": 0, "files": []}, timeout=60)
            assert r.status_code == 200, r.text
            reader = PdfReader(io.BytesIO(r.content))
            page1 = reader.pages[0].extract_text() or ""
            assert "Escrito" in page1
            assert "Carta notarial" in page1
        finally:
            mongo[dbn].case_messages.delete_one({"_id": ObjectId(msg_id)})
            mongo.close()


# ---------- ZIP ----------

class TestZip:
    def test_zip_download(self, admin, admin_case):
        r = admin.get(f"{BASE_URL}/api/cases/{admin_case}/download-zip", timeout=60)
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/zip"
        z = zipfile.ZipFile(io.BytesIO(r.content))
        names = z.namelist()
        assert "conversacion.md" in names
        assert "LEEME.txt" in names
        assert any(n.startswith("archivos/") for n in names)
        # ledger, facts, checklist CSVs exist (we added data)
        assert "pagos_y_deudas.csv" in names
        assert "hechos.csv" in names
        assert "checklist.txt" in names


# ---------- PERMISOS ----------

class TestPerms:
    def test_client_cannot_access_admin_case(self, client, admin_case):
        for path in [
            f"/api/cases/{admin_case}/ledger",
            f"/api/cases/{admin_case}/facts",
            f"/api/cases/{admin_case}/checklist",
            f"/api/cases/{admin_case}/evidence",
            f"/api/cases/{admin_case}/download-zip",
        ]:
            r = client.get(f"{BASE_URL}{path}", timeout=20)
            assert r.status_code == 404, f"{path}: {r.status_code}"
        r = client.post(f"{BASE_URL}/api/cases/{admin_case}/bundle", json={"files": []}, timeout=20)
        assert r.status_code == 404

    def test_invalid_case_id_is_404(self, admin):
        r = admin.get(f"{BASE_URL}/api/cases/zzz/ledger", timeout=20)
        assert r.status_code == 404
        r = admin.post(f"{BASE_URL}/api/cases/zzz/facts", data={"date": "2025-01-01", "text": "hecho prueba"}, timeout=20)
        assert r.status_code == 404

    def test_pending_payment_402(self, client, client_case, admin):
        from pymongo import MongoClient
        from bson import ObjectId
        mongo = MongoClient(os.environ["MONGO_URL"])
        dbn = os.environ["DB_NAME"]
        mongo[dbn].cases.update_one({"_id": ObjectId(client_case)}, {"$set": {"payment_status": "pendiente_pago"}})
        try:
            r = client.post(f"{BASE_URL}/api/cases/{client_case}/ledger",
                            data={"type": "cargo", "date": "2025-01-01", "amount": "10", "concept": "test"}, timeout=20)
            assert r.status_code == 402, r.text
            r = client.post(f"{BASE_URL}/api/cases/{client_case}/facts",
                            data={"date": "2025-01-01", "text": "hecho prueba"}, timeout=20)
            assert r.status_code == 402
            r = client.put(f"{BASE_URL}/api/cases/{client_case}/checklist", json={"tramite": "desalojo"}, timeout=20)
            assert r.status_code == 402
            r = client.post(f"{BASE_URL}/api/cases/{client_case}/bundle", json={"files": []}, timeout=20)
            assert r.status_code == 402
            r = client.get(f"{BASE_URL}/api/cases/{client_case}/download-zip", timeout=20)
            assert r.status_code == 402
        finally:
            mongo[dbn].cases.update_one({"_id": ObjectId(client_case)}, {"$set": {"payment_status": "autorizada"}})
            mongo.close()

    def test_tools_do_not_consume_quota(self, client, client_case):
        from pymongo import MongoClient
        from bson import ObjectId
        mongo = MongoClient(os.environ["MONGO_URL"])
        dbn = os.environ["DB_NAME"]
        mongo[dbn].cases.update_one({"_id": ObjectId(client_case)}, {"$set": {"payment_status": "autorizada"}})
        before = mongo[dbn].cases.find_one({"_id": ObjectId(client_case)}).get("messages_used", 0)
        try:
            client.post(f"{BASE_URL}/api/cases/{client_case}/ledger",
                        data={"type": "cargo", "date": "2025-01-01", "amount": "10", "concept": "test"}, timeout=20)
            client.post(f"{BASE_URL}/api/cases/{client_case}/facts",
                        data={"date": "2025-01-01", "text": "hecho prueba"}, timeout=20)
            client.put(f"{BASE_URL}/api/cases/{client_case}/checklist", json={"tramite": "desalojo"}, timeout=20)
            after = mongo[dbn].cases.find_one({"_id": ObjectId(client_case)}).get("messages_used", 0)
            assert after == before
        finally:
            mongo.close()

    def test_delete_case_cleans_records(self, admin):
        from pymongo import MongoClient
        mongo = MongoClient(os.environ["MONGO_URL"])
        dbn = os.environ["DB_NAME"]
        r = admin.post(f"{BASE_URL}/api/cases", json={"title": "TEST_iter24 delete"}, timeout=20)
        cid = r.json()["id"]
        r1 = admin.post(f"{BASE_URL}/api/cases/{cid}/ledger",
                        data={"type": "cargo", "date": "2025-01-01", "amount": "5", "concept": "prueba"}, timeout=20)
        assert r1.status_code == 200, r1.text
        r2 = admin.post(f"{BASE_URL}/api/cases/{cid}/facts",
                        data={"date": "2025-01-01", "text": "hecho prueba"}, timeout=20)
        assert r2.status_code == 200, r2.text
        assert mongo[dbn].case_ledger.count_documents({"case_id": cid}) >= 1
        assert mongo[dbn].case_facts.count_documents({"case_id": cid}) >= 1
        admin.delete(f"{BASE_URL}/api/cases/{cid}", timeout=20)
        assert mongo[dbn].case_ledger.count_documents({"case_id": cid}) == 0
        assert mongo[dbn].case_facts.count_documents({"case_id": cid}) == 0
        mongo.close()
