"""Iteration 23: case tools — calculators, events, idempotent chat, report, reminders."""
import os
import sys
import uuid
import time

import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
ADMIN_EMAIL = "admin@onbuysolutions.com"
ADMIN_PASSWORD = "OnBuy2026!"
CLIENT_EMAIL = "cliente.prueba@ejemplo.com"
CLIENT_PASSWORD = "Cliente2026!"


# ---------- fixtures ----------

def _login(email, password):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=20)
    assert r.status_code == 200, f"login {email}: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def admin_headers():
    return _login(ADMIN_EMAIL, ADMIN_PASSWORD)


@pytest.fixture(scope="module")
def client_headers():
    return _login(CLIENT_EMAIL, CLIENT_PASSWORD)


@pytest.fixture(scope="module")
def admin_case(admin_headers):
    r = admin_headers.post(f"{BASE_URL}/api/cases", json={"title": "TEST_iter23 case tools", "description": "auto"}, timeout=20)
    assert r.status_code == 200, r.text
    cid = r.json()["id"]
    yield cid
    admin_headers.delete(f"{BASE_URL}/api/cases/{cid}", timeout=20)


# ---------- CALCULADORAS: aritmética ----------

class TestCalculatorsArithmetic:
    def _run(self, headers, cid, payload):
        r = headers.post(f"{BASE_URL}/api/cases/{cid}/calculations", json=payload, timeout=20)
        assert r.status_code == 200, r.text
        return r.json()

    def _content(self, headers, cid, msg_id):
        r = headers.get(f"{BASE_URL}/api/cases/{cid}", timeout=20)
        assert r.status_code == 200
        for m in r.json()["messages"]:
            if m["id"] == msg_id:
                return m
        pytest.fail("message not found")

    def test_alquileres(self, admin_headers, admin_case):
        res = self._run(admin_headers, admin_case, {
            "type": "alquileres",
            "inputs": {"renta_mensual": 1500, "mes_inicio": "2025-01", "mes_fin": "2025-04", "pagos": "2025-01 1500"},
        })
        msg = self._content(admin_headers, admin_case, res["message_id"])
        assert msg["kind"] == "calculation"
        assert msg["role"] == "assistant"
        assert "S/ 4,500.00" in msg["content"], msg["content"]

    def test_alimentos(self, admin_headers, admin_case):
        res = self._run(admin_headers, admin_case, {
            "type": "alimentos",
            "inputs": {"monto_mensual": 600, "mes_inicio": "2024-11", "mes_fin": "2025-01", "pagos": ""},
        })
        msg = self._content(admin_headers, admin_case, res["message_id"])
        assert "S/ 1,800.00" in msg["content"]

    def test_intereses_efectiva(self, admin_headers, admin_case):
        res = self._run(admin_headers, admin_case, {
            "type": "intereses",
            "inputs": {"capital": 10000, "fecha_inicio": "2024-01-01", "fecha_fin": "2025-01-01", "tasa_anual": 3.5},
        })
        msg = self._content(admin_headers, admin_case, res["message_id"])
        assert "S/ 355.94" in msg["content"], msg["content"]

    def test_intereses_factores_laboral(self, admin_headers, admin_case):
        res = self._run(admin_headers, admin_case, {
            "type": "intereses",
            "inputs": {"capital": 10000, "fecha_inicio": "2024-01-01", "fecha_fin": "2025-01-01",
                       "factor_inicio": 1.95, "factor_fin": 1.98, "tipo": "laboral"},
        })
        msg = self._content(admin_headers, admin_case, res["message_id"])
        assert "S/ 300.00" in msg["content"], msg["content"]

    def test_beneficios(self, admin_headers, admin_case):
        res = self._run(admin_headers, admin_case, {
            "type": "beneficios",
            "inputs": {"fecha_ingreso": "2022-03-01", "fecha_cese": "2025-08-15", "sueldo": 3000, "asignacion_familiar": True},
        })
        msg = self._content(admin_headers, admin_case, res["message_id"])
        c = msg["content"]
        assert "S/ 1,059.28" in c, c
        assert "S/ 518.83" in c, c
        assert "S/ 1,426.79" in c, c


# ---------- CALCULADORAS: validación ----------

class TestCalculatorsValidation:
    def _post(self, headers, cid, payload):
        return headers.post(f"{BASE_URL}/api/cases/{cid}/calculations", json=payload, timeout=20)

    def test_tipo_inexistente(self, admin_headers, admin_case):
        r = self._post(admin_headers, admin_case, {"type": "nope", "inputs": {}})
        assert r.status_code == 400

    def test_fechas_invertidas_beneficios(self, admin_headers, admin_case):
        r = self._post(admin_headers, admin_case, {
            "type": "beneficios",
            "inputs": {"fecha_ingreso": "2025-08-15", "fecha_cese": "2022-03-01", "sueldo": 3000},
        })
        assert r.status_code == 400

    def test_intereses_sin_tasa_ni_factores(self, admin_headers, admin_case):
        r = self._post(admin_headers, admin_case, {
            "type": "intereses",
            "inputs": {"capital": 10000, "fecha_inicio": "2024-01-01", "fecha_fin": "2025-01-01"},
        })
        assert r.status_code == 400

    def test_pago_mal_escrito(self, admin_headers, admin_case):
        r = self._post(admin_headers, admin_case, {
            "type": "alquileres",
            "inputs": {"renta_mensual": 1500, "mes_inicio": "2025-01", "mes_fin": "2025-02", "pagos": "abc"},
        })
        assert r.status_code == 400

    def test_caso_ajeno_devuelve_404(self, client_headers, admin_case):
        # cliente intenta usar la calculadora en un caso del admin
        r = client_headers.post(f"{BASE_URL}/api/cases/{admin_case}/calculations",
                          json={"type": "alimentos", "inputs": {"monto_mensual": 600, "mes_inicio": "2024-11", "mes_fin": "2025-01"}}, timeout=20)
        assert r.status_code == 404

    def test_cliente_pendiente_pago_402(self, client_headers):
        # crear un caso de cliente nuevo (queda en 'pendiente_pago' si ya consumió trial, o 'prueba' si no)
        c = client_headers.post(f"{BASE_URL}/api/cases", json={"title": "TEST_iter23 client calc", "description": ""}, timeout=20)
        assert c.status_code == 200
        cid = c.json()["id"]
        try:
            # forzar pendiente_pago via Mongo para probar 402 de forma determinista
            from pymongo import MongoClient
            from bson import ObjectId
            mc = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
            mc[os.environ.get("DB_NAME", "test_database")].cases.update_one(
                {"_id": ObjectId(cid)}, {"$set": {"payment_status": "pendiente_pago"}}
            )
            r = client_headers.post(f"{BASE_URL}/api/cases/{cid}/calculations",
                              json={"type": "alimentos", "inputs": {"monto_mensual": 600, "mes_inicio": "2024-11", "mes_fin": "2025-01"}}, timeout=20)
            assert r.status_code == 402, r.text
        finally:
            client_headers.delete(f"{BASE_URL}/api/cases/{cid}", timeout=20)

    def test_calculadora_no_descuenta_mensajes_cliente(self, client_headers):
        c = client_headers.post(f"{BASE_URL}/api/cases", json={"title": "TEST_iter23 client no decrement", "description": ""}, timeout=20)
        cid = c.json()["id"]
        try:
            before = client_headers.get(f"{BASE_URL}/api/cases/{cid}", timeout=20).json()["case"]
            if before.get("payment_status") != "prueba":
                pytest.skip("cliente sin cupo de prueba; se omite el test de no-descuento")
            used_before = before["messages_used"]
            r = client_headers.post(f"{BASE_URL}/api/cases/{cid}/calculations",
                              json={"type": "alimentos", "inputs": {"monto_mensual": 600, "mes_inicio": "2024-11", "mes_fin": "2025-01"}}, timeout=20)
            assert r.status_code == 200
            after = client_headers.get(f"{BASE_URL}/api/cases/{cid}", timeout=20).json()["case"]
            assert after["messages_used"] == used_before
        finally:
            client_headers.delete(f"{BASE_URL}/api/cases/{cid}", timeout=20)


# ---------- EVENTOS ----------

class TestEventsCRUD:
    def test_crud_flow(self, admin_headers, admin_case):
        # create
        r = admin_headers.post(f"{BASE_URL}/api/cases/{admin_case}/events",
                          json={"title": "TEST_contestar demanda", "date": "2025-12-01", "kind": "plazo", "note": "x"}, timeout=20)
        assert r.status_code == 200, r.text
        ev = r.json()
        assert ev["kind"] == "plazo"
        eid = ev["id"]

        # create a second one, earlier date, to verify ordering
        r2 = admin_headers.post(f"{BASE_URL}/api/cases/{admin_case}/events",
                           json={"title": "TEST_audiencia", "date": "2025-11-15", "kind": "etapa"}, timeout=20)
        assert r2.status_code == 200
        eid2 = r2.json()["id"]

        # list ordered by date asc
        lst = admin_headers.get(f"{BASE_URL}/api/cases/{admin_case}/events", timeout=20).json()
        dates = [e["date"] for e in lst if e["id"] in (eid, eid2)]
        assert dates == sorted(dates)

        # mark done
        upd = admin_headers.put(f"{BASE_URL}/api/cases/{admin_case}/events/{eid}",
                           json={"done": True}, timeout=20)
        assert upd.status_code == 200 and upd.json()["done"] is True

        # delete
        d = admin_headers.delete(f"{BASE_URL}/api/cases/{admin_case}/events/{eid}", timeout=20)
        assert d.status_code == 200
        d2 = admin_headers.delete(f"{BASE_URL}/api/cases/{admin_case}/events/{eid2}", timeout=20)
        assert d2.status_code == 200

    def test_fecha_invalida(self, admin_headers, admin_case):
        r = admin_headers.post(f"{BASE_URL}/api/cases/{admin_case}/events",
                          json={"title": "TEST_x", "date": "2025-13-45", "kind": "plazo"}, timeout=20)
        # pydantic regex may accept 2025-13-45 (matches pattern); but then _valid_date returns 400
        assert r.status_code in (400, 422)

    def test_kind_invalido(self, admin_headers, admin_case):
        r = admin_headers.post(f"{BASE_URL}/api/cases/{admin_case}/events",
                          json={"title": "TEST_x", "date": "2025-12-01", "kind": "basura"}, timeout=20)
        assert r.status_code == 422

    def test_evento_de_otro_caso(self, admin_headers, admin_case):
        # crear evento en admin_case y intentar borrarlo via otro case_id
        r = admin_headers.post(f"{BASE_URL}/api/cases/{admin_case}/events",
                          json={"title": "TEST_x", "date": "2025-12-01", "kind": "plazo"}, timeout=20).json()
        eid = r["id"]
        # crear un segundo caso
        c2 = admin_headers.post(f"{BASE_URL}/api/cases", json={"title": "TEST_iter23 otro", "description": ""}, timeout=20).json()["id"]
        try:
            r2 = admin_headers.put(f"{BASE_URL}/api/cases/{c2}/events/{eid}", json={"done": True}, timeout=20)
            assert r2.status_code == 404
        finally:
            admin_headers.delete(f"{BASE_URL}/api/cases/{c2}", timeout=20)
            admin_headers.delete(f"{BASE_URL}/api/cases/{admin_case}/events/{eid}", timeout=20)

    def test_delete_case_cascades_events(self, admin_headers):
        c = admin_headers.post(f"{BASE_URL}/api/cases", json={"title": "TEST_iter23 cascade", "description": ""}, timeout=20).json()["id"]
        ev = admin_headers.post(f"{BASE_URL}/api/cases/{c}/events",
                           json={"title": "TEST_x", "date": "2025-12-01", "kind": "plazo"}, timeout=20).json()
        eid = ev["id"]
        admin_headers.delete(f"{BASE_URL}/api/cases/{c}", timeout=20)
        # verify directly in Mongo
        from pymongo import MongoClient
        from bson import ObjectId
        mc = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
        remaining = mc[os.environ.get("DB_NAME", "test_database")].case_events.find_one({"_id": ObjectId(eid)})
        assert remaining is None


# ---------- SUGERENCIAS (sin IA cuando no hay memoria) ----------

class TestSuggestionsEdge:
    def test_sin_conversacion_400(self, admin_headers):
        # crear caso vacío sin memoria -> 400
        c = admin_headers.post(f"{BASE_URL}/api/cases", json={"title": "TEST_iter23 empty", "description": ""}, timeout=20).json()["id"]
        try:
            r = admin_headers.post(f"{BASE_URL}/api/cases/{c}/events/suggest", timeout=30)
            assert r.status_code == 400, r.text
        finally:
            admin_headers.delete(f"{BASE_URL}/api/cases/{c}", timeout=20)


# ---------- VERIFY CITATIONS: edge no-AI (user role 404) ----------

class TestVerifyCitationsEdge:
    def test_user_message_404(self, admin_headers, admin_case):
        # directly insert a user message via Mongo
        from pymongo import MongoClient
        from datetime import datetime, timezone as tz
        mc = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
        coll = mc[os.environ.get("DB_NAME", "test_database")].case_messages
        res = coll.insert_one({"case_id": admin_case, "role": "user", "content": "hola",
                               "attachments": [], "created_at": datetime.now(tz.utc).isoformat()})
        try:
            r = admin_headers.post(f"{BASE_URL}/api/cases/{admin_case}/messages/{res.inserted_id}/verify-citations", timeout=60)
            assert r.status_code == 404
        finally:
            coll.delete_one({"_id": res.inserted_id})


# ---------- REPORTE DE FALLA ----------

class TestReportFailure:
    def test_report_creates_contact(self, admin_headers, admin_case):
        r = admin_headers.post(f"{BASE_URL}/api/cases/{admin_case}/report-failure",
                          json={"message": "TEST_iter23 msg", "error": "TEST_iter23 err"}, timeout=20)
        assert r.status_code == 200
        # contacto creado
        from pymongo import MongoClient
        mc = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
        coll = mc[os.environ.get("DB_NAME", "test_database")].contacts
        doc = coll.find_one({"service": "Falla en chat de asesoría", "message": {"$regex": "TEST_iter23 msg"}})
        assert doc is not None
        try:
            # visible via admin API
            lst = admin_headers.get(f"{BASE_URL}/api/admin/contacts", timeout=20)
            assert lst.status_code == 200
            assert any("TEST_iter23 msg" in (c.get("message") or "") for c in lst.json())
        finally:
            coll.delete_one({"_id": doc["_id"]})


# ---------- RECORDATORIOS (dry-run) ----------

class TestReminders:
    def test_send_due_reminders_no_exception(self, admin_headers, admin_case):
        # inserta un evento plazo con fecha = mañana en Lima
        from datetime import datetime, timezone as tz, timedelta
        from pymongo import MongoClient
        from bson import ObjectId
        mc = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
        coll = mc[os.environ.get("DB_NAME", "test_database")].case_events
        manana = ((datetime.now(tz.utc) - timedelta(hours=5)).date() + timedelta(days=1)).isoformat()
        ev = coll.insert_one({"case_id": admin_case, "title": "TEST_iter23 reminder",
                              "date": manana, "kind": "plazo", "done": False, "reminded": [],
                              "note": "", "source": "cliente",
                              "created_at": datetime.now(tz.utc).isoformat()})
        # etapa (no debe tocarse)
        ev_etapa = coll.insert_one({"case_id": admin_case, "title": "TEST_iter23 etapa",
                                    "date": manana, "kind": "etapa", "done": False, "reminded": [],
                                    "created_at": datetime.now(tz.utc).isoformat()})
        try:
            import subprocess
            result = subprocess.run(
                [sys.executable, "-c", "import asyncio; from routes.case_tools import send_due_reminders; asyncio.run(send_due_reminders())"],
                cwd="/app/backend", capture_output=True, text=True, timeout=30,
            )
            assert result.returncode == 0, f"stderr={result.stderr}"
            # reminded debe seguir vacío (no API de Resend en preview)
            doc = coll.find_one({"_id": ev.inserted_id})
            assert doc["reminded"] == [], f"reminded={doc['reminded']}"
            # etapa intacta
            doc2 = coll.find_one({"_id": ev_etapa.inserted_id})
            assert doc2["reminded"] == []
        finally:
            coll.delete_one({"_id": ev.inserted_id})
            coll.delete_one({"_id": ev_etapa.inserted_id})


# ---------- IDEMPOTENT CHAT ----------

class TestIdempotentChat:
    def test_same_client_msg_id_dedupe(self, admin_headers, admin_case):
        """Same client_msg_id twice => replay, only 1 user + 1 assistant for that id."""
        cmid = f"TEST_iter23_{uuid.uuid4().hex[:8]}"
        payload = {"text": "Responde en máximo 20 palabras: ¿cuál es la capital de Perú?", "client_msg_id": cmid}
        # First call (streaming)
        r1 = admin_headers.post(f"{BASE_URL}/api/cases/{admin_case}/chat", data=payload, timeout=120, stream=True)
        assert r1.status_code == 200
        body1 = r1.text
        assert body1.strip()
        time.sleep(1.0)
        # Second call with same id
        r2 = admin_headers.post(f"{BASE_URL}/api/cases/{admin_case}/chat", data=payload, timeout=60)
        assert r2.status_code == 200
        body2 = r2.text
        # Replay must match the saved assistant content
        from pymongo import MongoClient
        mc = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
        coll = mc[os.environ.get("DB_NAME", "test_database")].case_messages
        users = list(coll.find({"case_id": admin_case, "role": "user", "client_msg_id": cmid}))
        assistants = list(coll.find({"case_id": admin_case, "role": "assistant", "reply_to": cmid}))
        assert len(users) == 1, f"user msgs={len(users)}"
        assert len(assistants) == 1, f"assistant msgs={len(assistants)}"
        assert body2.strip() == assistants[0]["content"].strip()
        # cleanup
        coll.delete_many({"case_id": admin_case, "$or": [{"client_msg_id": cmid}, {"reply_to": cmid}]})
