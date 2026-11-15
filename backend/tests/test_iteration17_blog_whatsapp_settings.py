"""Iteration 17: blog + whatsapp + llm_provider settings + contact form."""
import os, time
import pytest
import requests

def _read_backend_url():
    url = os.environ.get("REACT_APP_BACKEND_URL", "").strip()
    if not url:
        try:
            with open("/app/frontend/.env") as fh:
                for line in fh:
                    if line.startswith("REACT_APP_BACKEND_URL="):
                        url = line.split("=", 1)[1].strip()
        except FileNotFoundError:
            pass
    return url.rstrip("/")

BASE_URL = _read_backend_url()
assert BASE_URL, "REACT_APP_BACKEND_URL missing"
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@onbuysolutions.com"
ADMIN_PASSWORD = "OnBuy2026!"


@pytest.fixture(scope="session")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="session")
def anon_session():
    return requests.Session()


# --- public blog ---

def test_public_blog_list_has_no_content(anon_session):
    r = anon_session.get(f"{API}/blog", timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list) and len(data) >= 1
    sample = next((p for p in data if "desalojar" in p["title"].lower()), None)
    assert sample is not None, "Seeded sample post missing"
    for p in data:
        assert "content" not in p, "list endpoint must not expose content"
        assert p["published"] is True


def test_public_blog_get_by_slug(anon_session):
    r = anon_session.get(f"{API}/blog", timeout=10)
    slug = r.json()[0]["slug"]
    r2 = anon_session.get(f"{API}/blog/{slug}", timeout=10)
    assert r2.status_code == 200
    doc = r2.json()
    assert doc["slug"] == slug
    assert len(doc["content"]) > 10


def test_public_blog_missing_slug_is_404(anon_session):
    r = anon_session.get(f"{API}/blog/no-existe-xyz-987", timeout=10)
    assert r.status_code == 404


# --- blog admin requires auth ---

def test_admin_blog_requires_auth(anon_session):
    assert anon_session.get(f"{API}/admin/blog", timeout=10).status_code in (401, 403)
    assert anon_session.post(f"{API}/admin/blog", json={"title": "x", "content": "yyyyyyyyyy"}, timeout=10).status_code in (401, 403)


def test_admin_blog_invalid_service_is_400(admin_session):
    r = admin_session.post(
        f"{API}/admin/blog",
        json={"title": "TEST_bad_svc_" + str(int(time.time())), "content": "contenido mínimo largo", "service": "inexistente"},
        timeout=10,
    )
    assert r.status_code == 400


def test_admin_blog_unique_slug_on_duplicate_title(admin_session):
    ids = []
    try:
        title = "TEST_blog_dup_" + str(int(time.time()))
        payload = {"title": title, "excerpt": "x", "content": "## Hola\nContenido de prueba", "service": "legal", "published": False}
        r1 = admin_session.post(f"{API}/admin/blog", json=payload, timeout=10)
        assert r1.status_code == 200, r1.text
        p1 = r1.json(); ids.append(p1["id"])
        r2 = admin_session.post(f"{API}/admin/blog", json=payload, timeout=10)
        assert r2.status_code == 200
        p2 = r2.json(); ids.append(p2["id"])
        assert p1["slug"] != p2["slug"]
        # draft invisible from public
        pub = admin_session.get(f"{API}/blog/{p1['slug']}", timeout=10)
        assert pub.status_code == 404
    finally:
        for i in ids:
            admin_session.delete(f"{API}/admin/blog/{i}", timeout=10)


# --- settings llm_provider ---

def test_settings_llm_provider_invalid_is_400(admin_session):
    r = admin_session.put(f"{API}/admin/settings", json={"llm_provider": "openai"}, timeout=10)
    assert r.status_code == 400


def test_settings_llm_provider_google_without_key_is_400(admin_session):
    # Ensure google key not configured
    cur = admin_session.get(f"{API}/admin/settings", timeout=10).json()
    if cur.get("google_key_masked"):
        pytest.skip("Google key is configured; skipping negative test")
    r = admin_session.put(f"{API}/admin/settings", json={"llm_provider": "google"}, timeout=10)
    assert r.status_code == 400


def test_settings_llm_provider_emergent_ok_and_whatsapp_roundtrip(admin_session):
    r = admin_session.put(
        f"{API}/admin/settings",
        json={"llm_provider": "emergent", "whatsapp_enabled": True, "whatsapp_number": "51 999 888 777", "whatsapp_message": "Hola OnBuySolutions, estoy interesado en: {servicio}"},
        timeout=10,
    )
    assert r.status_code == 200
    pub = requests.get(f"{API}/public/settings", timeout=10).json()
    assert pub["whatsapp_enabled"] is True
    assert pub["whatsapp_number"] == "51999888777"  # digits stripped
    assert "{servicio}" in pub["whatsapp_message"]


# --- public contact ---

def test_public_contact_submission_persists(admin_session, anon_session):
    name = f"TEST_contact_{int(time.time())}"
    r = anon_session.post(
        f"{API}/contact",
        json={"name": name, "email": "t@test.com", "phone": "999", "message": "Hola, me interesa.", "service": "Asesoría legal y contable especializada"},
        timeout=10,
    )
    assert r.status_code == 200
    # fetch inbox
    inbox = admin_session.get(f"{API}/admin/contacts", timeout=10).json()
    mine = [c for c in inbox if c["name"] == name]
    assert mine, "Contact not saved"
    assert mine[0]["service"] == "Asesoría legal y contable especializada"
    # cleanup
    admin_session.delete(f"{API}/admin/contacts/{mine[0]['id']}", timeout=10)
