import os
import re
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)


def analyze_password(password: str) -> dict:
    """Analizza la robustezza di una password e restituisce risultati dettagliati."""
    if not password:
        return {
            "score": 0,
            "level": "debole",
            "percentage": 0,
            "checks": {
                "length": False,
                "uppercase": False,
                "lowercase": False,
                "number": False,
                "special": False,
            },
            "suggestions": ["Inserisci una password per valutarne la robustezza."],
        }

    checks = {
        "length": len(password) >= 8,
        "uppercase": bool(re.search(r"[A-Z]", password)),
        "lowercase": bool(re.search(r"[a-z]", password)),
        "number": bool(re.search(r"[0-9]", password)),
        "special": bool(re.search(r"[^A-Za-z0-9]", password)),
    }

    met_count = sum(1 for v in checks.values() if v)

    # Se la password è troppo corta, è sempre debole
    if len(password) < 8:
        level = "debole"
        percentage = min(met_count * 6, 33)
        suggestions = []
        if not checks["length"]:
            suggestions.append("Usa almeno 8 caratteri per una password pi\u00f9 sicura.")
        if not checks["uppercase"]:
            suggestions.append("Aggiungi almeno una lettera maiuscola (A-Z).")
        if not checks["lowercase"]:
            suggestions.append("Aggiungi almeno una lettera minuscola (a-z).")
        if not checks["number"]:
            suggestions.append("Inserisci almeno un numero (0-9).")
        if not checks["special"]:
            suggestions.append("Aggiungi un carattere speciale (! @ # $ % & *).")
        if not suggestions:
            suggestions.append("Inserisci una password per valutarne la robustezza.")
        return {
            "score": round(met_count * 2, 1),
            "level": level,
            "percentage": percentage,
            "checks": checks,
            "suggestions": suggestions,
        }

    # Bonus per lunghezza extra
    bonus = 0.0
    if len(password) >= 12:
        bonus += 0.5
    if len(password) >= 16:
        bonus += 0.5
    if len(password) >= 20:
        bonus += 0.5

    # Penalità per pattern comuni
    penalty = 0.0
    common_patterns = [
        "123", "abc", "qwerty", "password", "admin",
        "123456", "qwerty123", "letmein", "welcome", "monkey",
        "dragon", "master", "football", "italia",
    ]
    lower = password.lower()
    for pat in common_patterns:
        if pat in lower:
            penalty += 1.0

    # Caratteri ripetuti (3+ uguali consecutivi) — penalità per gruppo
    repeated_groups = re.findall(r"(.)\1{2,}", password)
    penalty += len(repeated_groups) * 1.0

    # Sequenze alfabetiche
    if re.search(
        r"(?:abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)",
        lower,
    ):
        penalty += 0.5

    # Sequenze numeriche
    if re.search(r"(?:012|123|234|345|456|567|678|789)", password):
        penalty += 0.5

    score = max(0.0, min(10.0, met_count * 2 + bonus - penalty))

    # Determina livello e percentuale
    if score <= 4:
        level = "debole"
        percentage = round((score / 4) * 33) if score > 0 else 0
    elif score <= 7:
        level = "media"
        percentage = 34 + round(((score - 4) / 3) * 33)
    else:
        level = "forte"
        percentage = 67 + round(((score - 7) / 3) * 33)

    percentage = min(100, max(0, percentage))

    # Suggerimenti in italiano
    suggestions = []
    if not checks["length"]:
        suggestions.append("Usa almeno 8 caratteri per una password pi\u00f9 sicura.")
    if not checks["uppercase"]:
        suggestions.append("Aggiungi almeno una lettera maiuscola (A-Z).")
    if not checks["lowercase"]:
        suggestions.append("Aggiungi almeno una lettera minuscola (a-z).")
    if not checks["number"]:
        suggestions.append("Inserisci almeno un numero (0-9).")
    if not checks["special"]:
        suggestions.append("Aggiungi un carattere speciale (! @ # $ % & *).")
    if penalty > 0 and met_count >= 3:
        suggestions.append("Evita sequenze comuni o caratteri ripetuti.")
    if not suggestions:
        suggestions.append("Ottimo! La tua password \u00e8 robusta e ben bilanciata.")

    return {
        "score": round(score, 1),
        "level": level,
        "percentage": percentage,
        "checks": checks,
        "suggestions": suggestions,
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/robots.txt")
def robots():
    return app.send_static_file("robots.txt")


@app.route("/sitemap.xml")
def sitemap():
    return app.send_static_file("sitemap.xml")


@app.route("/api/validate", methods=["POST"])
def validate():
    data = request.get_json(silent=True) or {}
    password = data.get("password", "")
    result = analyze_password(password)
    return jsonify(result)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 4600))
    app.run(host="0.0.0.0", port=port, debug=False)
