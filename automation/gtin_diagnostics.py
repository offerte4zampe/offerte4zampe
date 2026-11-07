"""Read-only diagnostics for raw merchant identifiers; never modifies offers.

All diagnostics are best-effort: malformed records or metrics may be logged,
but cannot change, drop or reject a catalog offer.
"""
import logging
import re

LOG = logging.getLogger(__name__)


def warn(message, *args):
    """Logging is non-critical: never let a faulty handler break an import."""
    try:
        LOG.warning(message, *args)
    except Exception:
        pass


def valid_gtin(value):
    """Validate GTIN-8/12/13/14, including checksum; never infer missing zeros."""
    try:
        if not isinstance(value, str):
            return False
        s = value.strip()
        if not re.fullmatch(r'(?:[0-9]{8}|[0-9]{12}|[0-9]{13}|[0-9]{14})', s):
            return False
        digits = [int(c) for c in s]
        total = sum(d * (3 if i % 2 == 0 else 1)
                    for i, d in enumerate(reversed(digits[:-1])))
        return (10 - total % 10) % 10 == digits[-1]
    except Exception as error:
        warn("GTIN diagnostics: checksum failed (%s)", type(error).__name__)
        return False


def gtin_counters(rows):
    """Best-effort buckets for feed_gtin only, never operational offer['gtin'].

    A malformed row is counted as invalid, not silently dropped.
    Any error is recorded in diagnostic_errors; offer rows are never modified.
    """
    counts = dict(raw_present=0, valid=0, invalid=0, empty=0)
    diagnostic_errors = 0
    try:
        for row in rows:
            try:
                raw = row.get('feed_gtin') if isinstance(row, dict) else None
                if raw is None or (isinstance(raw, str) and not raw.strip()):
                    counts['empty'] += 1
                else:
                    counts['raw_present'] += 1
                    if valid_gtin(raw):
                        counts['valid'] += 1
                    else:
                        counts['invalid'] += 1
                        if not isinstance(raw, str):
                            diagnostic_errors += 1
            except Exception as error:
                diagnostic_errors += 1
                counts['raw_present'] += 1
                counts['invalid'] += 1
                warn("GTIN diagnostics: malformed row (%s)", type(error).__name__)
    except Exception as error:
        diagnostic_errors += 1
        warn("GTIN diagnostics: iteration failed (%s)", type(error).__name__)
    counts['diagnostic_errors'] = diagnostic_errors
    return counts
