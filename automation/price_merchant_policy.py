"""Merchant-level allowlist for observed price history and price-derived alerts.

Global PRICE_TRACKING_ENABLED is independently enforced by PR #63.
Adding a merchant requires an explicit review of its programme conditions.
Amazon is always excluded, even when the global flag is enabled.
"""
PRICE_HISTORY_ALLOWED = {
    'amazon': False,
    'bauzaar': True,
    'isola-dei-tesori': True,
    'paco': True,
    'webpet': True,
    'animaliapet': True,
}

def price_history_allowed(merchant_id):
    return merchant_id is not None and PRICE_HISTORY_ALLOWED.get(str(merchant_id).strip().lower(), False) is True

def history_offer_allowed(offer_id):
    if not isinstance(offer_id, str) or ':' not in offer_id:
        return False
    return price_history_allowed(offer_id.split(':', 1)[0])
