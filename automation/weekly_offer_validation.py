"""Conservative quality gates shared by weekly newsletter, article and social drafts."""
import re
from urllib.parse import urlsplit

_ALLOWED = ("crocchett", "lettiera", "litter", "mangime", "alimento", "alimenti", "cibo ", "pet food", "dry food", "wet food", "umido", "secco", "snack", "biscott", "paté", "pate")
_EXCLUDED = ("monofilo", "lenza", "collare", "guinzaglio", "pettorina", "antiparassitario", "shampoo", "spray", "giocattolo", "gioco ", "accessorio")
_KG = re.compile(r"(?<![\w\d])([0-9]+(?:[.,][0-9]+)?)\s*kg\b", re.IGNORECASE)
_TARGET = re.compile(r"[<>≥≤]\s*[0-9]+(?:[.,][0-9]+)?\s*kg\b", re.IGNORECASE)

def safe_https(value):
    if not isinstance(value, str):
        return False
    parsed = urlsplit(value.strip())
    return parsed.scheme == "https" and bool(parsed.hostname) and not parsed.username and not parsed.password

def validated_package(title, variant, category, weight_kg):
    title, variant, category = str(title or ""), str(variant or ""), str(category or "")
    description = (title + " " + category).casefold()
    if any(term in description for term in _EXCLUDED):
        return False
    if not any(term in description for term in _ALLOWED):
        return False
    if _TARGET.search(title) or _TARGET.search(variant):
        return False
    try:
        weight = float(weight_kg)
    except (TypeError, ValueError):
        return False
    if not (0.05 <= weight <= 30):
        return False
    matches = _KG.findall(title + " " + variant)
    return any(abs(float(x.replace(",", ".")) - weight) < max(0.01, weight * 0.02) for x in matches)

def validate_offer(offer):
    if not all(offer.get(k) for k in ("name", "format", "price", "shop", "url", "image", "category", "weight_kg")):
        return False
    if not safe_https(offer["url"]) or not safe_https(offer["image"]):
        return False
    if not re.fullmatch(r"[0-9]+\.[0-9]{2} €", str(offer["price"])):
        return False
    return validated_package(offer["name"], offer["format"], offer["category"], offer["weight_kg"])

def validate_payload(payload):
    if payload.get("selection_version") != 2:
        raise ValueError("Unvalidated newsletter selection version")
    offers = payload.get("offers", [])
    if not 3 <= len(offers) <= 5 or any(not validate_offer(o) for o in offers):
        raise ValueError("Invalid weekly offers: package weights, category, images or links")
    return offers
