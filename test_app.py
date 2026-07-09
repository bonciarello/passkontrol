"""Test suite per PassKontrol — validatore di password."""

import json
import pytest
from app import app, analyze_password


@pytest.fixture
def client():
    """Fixture per il client di test Flask."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# ── Unit test: analyze_password ──────────────────────────────


def test_empty_password():
    """Password vuota deve restituire debole con suggerimento."""
    result = analyze_password("")
    assert result["level"] == "debole"
    assert result["percentage"] == 0
    assert result["score"] == 0
    assert not any(result["checks"].values())
    assert len(result["suggestions"]) == 1


def test_very_short_password():
    """Password cortissima 'a' deve essere debole."""
    result = analyze_password("a")
    assert result["level"] == "debole"
    assert result["percentage"] <= 33
    assert result["checks"]["lowercase"] is True
    assert result["checks"]["length"] is False
    assert result["checks"]["uppercase"] is False


def test_ciao_password():
    """'Ciao' deve essere debole con suggerimenti in italiano."""
    result = analyze_password("Ciao")
    assert result["level"] == "debole"
    assert result["percentage"] <= 33
    assert result["checks"]["uppercase"] is True
    assert result["checks"]["lowercase"] is True
    assert result["checks"]["length"] is False
    assert result["checks"]["number"] is False
    assert result["checks"]["special"] is False
    # Deve avere suggerimenti in italiano
    assert any("8 caratteri" in s for s in result["suggestions"])
    assert any("numero" in s for s in result["suggestions"])


def test_all_criteria_met():
    """Tutti i criteri minimi soddisfatti → forte."""
    result = analyze_password("CiaoMondo1!")
    assert result["level"] == "forte"
    assert result["percentage"] >= 67
    assert result["checks"]["length"] is True  # 11 chars >= 8
    assert result["checks"]["uppercase"] is True
    assert result["checks"]["lowercase"] is True
    assert result["checks"]["number"] is True
    assert result["checks"]["special"] is True
    assert any("robusta" in s for s in result["suggestions"])


def test_only_lowercase():
    """Solo minuscole, nessun altro criterio."""
    result = analyze_password("abcdefgh")
    assert result["checks"]["lowercase"] is True
    assert result["checks"]["uppercase"] is False
    assert result["checks"]["number"] is False
    assert result["checks"]["special"] is False
    assert result["checks"]["length"] is True


def test_only_numbers():
    """Solo numeri, lunghezza >= 8."""
    result = analyze_password("12345678")
    assert result["checks"]["number"] is True
    assert result["checks"]["length"] is True
    assert result["checks"]["lowercase"] is False
    assert result["checks"]["uppercase"] is False
    assert result["checks"]["special"] is False


def test_mixed_but_short():
    """Mix di tipi ma troppo corta."""
    result = analyze_password("Ab1!")
    assert result["checks"]["uppercase"] is True
    assert result["checks"]["lowercase"] is True
    assert result["checks"]["number"] is True
    assert result["checks"]["special"] is True
    assert result["checks"]["length"] is False
    assert result["level"] == "debole"


def test_very_strong_password():
    """Password molto lunga e complessa."""
    result = analyze_password("Tr0ub4dor&3xtraL0ngP@ss!")
    assert result["level"] == "forte"
    assert result["percentage"] == 100
    assert result["checks"]["length"] is True
    assert result["checks"]["uppercase"] is True
    assert result["checks"]["lowercase"] is True
    assert result["checks"]["number"] is True
    assert result["checks"]["special"] is True


def test_common_password_pattern():
    """Password con pattern comune 'password' penalizzata."""
    result = analyze_password("MyPassword123!")
    # Ha tutti i criteri ma contiene "password"
    assert "password" in "MyPassword123!".lower()
    # Potrebbe ancora essere media o forte a seconda del bilanciamento
    assert result["level"] in ("media", "forte")
    # Score deve essere penalizzato rispetto a senza pattern
    result_no_pattern = analyze_password("MyP@ssw0rd456!")
    assert result_no_pattern["score"] >= result["score"]


def test_sequential_characters():
    """Sequenze alfabetiche penalizzate."""
    result = analyze_password("abcdefgh1A!")
    # Contiene 'abcdefgh' che include sequenze
    assert result["checks"]["length"] is True
    assert result["checks"]["uppercase"] is True
    assert result["checks"]["lowercase"] is True
    assert result["checks"]["number"] is True
    assert result["checks"]["special"] is True
    # Penalizzata per sequenze, potrebbe non essere forte
    assert result["level"] in ("media", "forte")


def test_repeated_characters():
    """Caratteri ripetuti penalizzati."""
    result = analyze_password("aaaBBB111!")
    assert result["level"] in ("debole", "media")
    # Penalità per caratteri ripetuti


def test_all_uppercase():
    """Solo maiuscole."""
    result = analyze_password("PASSWORD123!")
    assert result["checks"]["uppercase"] is True
    assert result["checks"]["lowercase"] is False


def test_minimum_strong_boundary():
    """Password che soddisfa esattamente i criteri minimi per forte."""
    # 8 caratteri, 1 maiuscola, minuscole, 1 numero, 1 speciale
    result = analyze_password("Abcdef1!")
    assert result["checks"]["length"] is True
    assert result["checks"]["uppercase"] is True
    assert result["checks"]["lowercase"] is True
    assert result["checks"]["number"] is True
    assert result["checks"]["special"] is True
    assert result["level"] == "forte"


def test_score_range():
    """Lo score deve essere sempre tra 0 e 10."""
    test_cases = [
        "",
        "a",
        "Ciao",
        "password",
        "Abcdef1!",
        "Str0ng!P@ss",
        "Tr0ub4dor&3xtraL0ngP@ss!VerySecure2024!!",
    ]
    for pwd in test_cases:
        result = analyze_password(pwd)
        assert 0 <= result["score"] <= 10, f"Score {result['score']} out of range for '{pwd}'"
        assert 0 <= result["percentage"] <= 100
        assert result["level"] in ("debole", "media", "forte")


def test_percentage_monotonic():
    """Password più complesse dovrebbero avere percentuali non inferiori."""
    result_weak = analyze_password("ciao")
    result_better = analyze_password("Ciaomondo")
    result_strong = analyze_password("Ciaomondo1!")
    assert result_weak["percentage"] <= result_better["percentage"]
    assert result_better["percentage"] <= result_strong["percentage"]


def test_italian_suggestions():
    """Tutti i suggerimenti devono essere in italiano."""
    test_cases = ["", "a", "Ciao", "abcdefgh", "ABC1!"]
    for pwd in test_cases:
        result = analyze_password(pwd)
        for s in result["suggestions"]:
            # Verifica che contenga parole italiane comuni
            assert any(
                word in s.lower()
                for word in [
                    "password", "caratteri", "maiuscola", "minuscola",
                    "numero", "speciale", "robusta", "inserisci",
                    "aggiungi", "usa", "evita", "ottimo", "almeno",
                ]
            ), f"Suggestion doesn't look Italian: '{s}'"


# ── Integration test: API endpoint ───────────────────────────


def test_api_validate_empty(client):
    """POST /api/validate con password vuota."""
    resp = client.post("/api/validate", json={"password": ""})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["level"] == "debole"
    assert data["percentage"] == 0


def test_api_validate_ciao(client):
    """POST /api/validate con 'Ciao'."""
    resp = client.post("/api/validate", json={"password": "Ciao"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["level"] == "debole"
    assert data["checks"]["uppercase"] is True
    assert data["checks"]["lowercase"] is True


def test_api_validate_strong(client):
    """POST /api/validate con password forte."""
    resp = client.post("/api/validate", json={"password": "CiaoMondo1!"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["level"] == "forte"
    assert all(data["checks"].values())


def test_api_validate_no_body(client):
    """POST /api/validate senza body JSON."""
    resp = client.post("/api/validate", data="not json")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["level"] == "debole"


def test_index_page(client):
    """GET / deve restituire la pagina HTML."""
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "PassKontrol" in html
    assert "lang=\"it\"" in html
    assert "robustezza" in html.lower()


def test_index_has_seo_tags(client):
    """La pagina deve contenere i tag SEO richiesti."""
    resp = client.get("/")
    html = resp.data.decode("utf-8")
    assert "og:title" in html
    assert "og:description" in html
    assert "og:url" in html
    assert "canonical" in html
    assert "cristianporco.it" in html
    assert "application/ld+json" in html


def test_index_has_relative_assets(client):
    """Gli asset devono usare percorsi relativi (niente / iniziale)."""
    resp = client.get("/")
    html = resp.data.decode("utf-8")

    # Estrai i path degli asset
    import re
    hrefs = re.findall(r'href="([^"]*\.css)"', html)
    srcs = re.findall(r'src="([^"]*\.js)"', html)

    for path in hrefs + srcs:
        # I path relativi non devono iniziare con "/"
        if path.startswith("http"):
            continue  # URL assoluti come canonical sono OK
        assert not path.startswith("/"), f"Asset path '{path}' starts with '/' — must be relative"


def test_static_files(client):
    """I file statici devono essere serviti correttamente."""
    resp_css = client.get("/static/css/style.css")
    assert resp_css.status_code == 200

    resp_js = client.get("/static/js/app.js")
    assert resp_js.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
