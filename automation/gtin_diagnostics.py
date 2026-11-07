"""Read-only diagnostics for raw merchant identifiers; never modifies offers."""
import re

def valid_gtin(value):
    """Validate GTIN-8, GTIN-12, GTIN-13 or GTIN-14, including check digit."""
    s = str(value or '').strip()
    if not re.fullmatch(r'(?:[0-9]{8}|[0-9]{12}|[0-9]{13}|[0-9]{14})', s):
        return False
    digits = [int(c) for c in s]
    total = sum(d * (3 if i % 2 == 0 else 1)
                for i, d in enumerate(reversed(digits[:-1])))
    return (10 - total % 10) % 10 == digits[-1]

def gtin_counters(rows):
    """Count source feed values; operational row['gtin'] is deliberately ignored."""
    counts = dict(raw_present=0, valid=0, invalid=0, empty=0)
    for row in rows:
        raw = str(row.get('feed_gtin') or '').strip()
        if not raw:
            counts['empty'] += 1
        else:
            counts['raw_present'] += 1
            counts['valid' if valid_gtin(raw) else 'invalid'] += 1
    return counts
