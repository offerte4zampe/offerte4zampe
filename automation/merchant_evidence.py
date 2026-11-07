"""Private, best-effort merchant evidence from data already fetched.

Local runner-only output. Never place under site/ and never commit or upload
the contents to public GitHub Actions artifacts or logs.
"""
import datetime as dt
import hashlib
import json
import logging
from pathlib import Path
import re
import tempfile
import threading

_LOCK = threading.Lock()
PATH = Path(__file__).resolve().parent / 'diagnostics' / 'latest.json'
CATEGORIES = ('spaces', 'separators', 'non_numeric', 'leading_zeros', 'length', 'checksum')

def warn(area, error):
    try:
        logging.getLogger(__name__).warning(
            'Optional merchant evidence %s failed: %s', area, type(error).__name__)
    except Exception:
        pass

def safe_value(value, max_chars=240):
    try:
        if value is None:
            return ''
        if not isinstance(value, (str, int, float)):
            return ''
        return str(value)[:max_chars]
    except Exception:
        return ''

def signature(identity):
    """Stable fingerprint of SKU, EAN, title and *verified* selling weight."""
    try:
        value=json.dumps(identity, ensure_ascii=False, sort_keys=True,
                         separators=(',', ':')).encode('utf-8')
        return hashlib.sha256(value).hexdigest()
    except Exception as error:
        warn('fingerprint', error)
        return ''

def paco_record(row, reason, now, context=None, verified=None):
    """Only allowlisted product fields; do not collect URL, price or personal data."""
    try:
        context = context if isinstance(context, dict) else {}
        result = {
            'offer_id': safe_value(row.get('id'), 90),
            'feed_gtin': safe_value(row.get('feed_gtin'), 40),
            'page_ean13': [safe_value(x,40) for x in context.get('page_ean13',[])][:80],
            'feed_sku': safe_value(row.get('sku'), 90),
            'page_variant_id': [safe_value(x,90) for x in context.get('page_variant_id',[])][:80],
            'feed_title': safe_value(row.get('title')),
            'page_variant_label': [safe_value(x) for x in context.get('page_variant_label',[])][:80],
            'failure_reason': safe_value(reason,60),
            'checked_at': now.isoformat() if hasattr(now, 'isoformat') else safe_value(now,40),
        }
        if verified is not None and verified.get('quantity_verified') is True:
            identity = {
                'sku': result['feed_sku'],
                'ean': safe_value(verified.get('gtin'),40),
                'title': result['feed_title'],
                'weight_kg': verified.get('weight_kg'),
            }
            result['identity_fingerprint'] = signature(identity)
        return result
    except Exception as error:
        warn('paco_record', error)
        return None

def classify_gtin(value):
    """Exclusive invalid groups; source code is never rewritten."""
    try:
        from .gtin_diagnostics import valid_gtin
    except ImportError:
        from gtin_diagnostics import valid_gtin
    try:
        if isinstance(value,str):
            raw=value
        else:
            return 'non_numeric'
        if valid_gtin(raw):
            return None
        if any(ch.isspace() for ch in raw):
            return 'spaces'
        if any(ch in '-./_\\\\|:;' for ch in raw):
            return 'separators'
        if not re.fullmatch(r'[0-9]+',raw):
            return 'non_numeric'
        if len(raw)>14 and raw.startswith('0') and valid_gtin(raw.lstrip('0')):
            return 'leading_zeros'
        if len(raw) not in (8,12,13,14):
            return 'length'
        return 'checksum'
    except Exception as error:
        warn('classification', error)
        return 'non_numeric'

def bauzaar_report(rows):
    counts={key:0 for key in CATEGORIES}
    samples={key:[] for key in CATEGORIES}
    try:
        for row in rows:
            try:
                raw=row.get('feed_gtin') if isinstance(row,dict) else None
                if raw is None or raw=='':
                    continue
                category=classify_gtin(raw)
                if category is None:
                    continue
                counts[category]+=1
                if len(samples[category])<10:
                    samples[category].append({
                        'offer_id':safe_value(row.get('id'),90),
                        'feed_gtin':safe_value(raw,60),
                    })
            except Exception as error:
                warn('bauzaar_row',error)
        return {'counts':counts, 'examples':samples,
                'invalid_total':sum(counts.values())}
    except Exception as error:
        warn('bauzaar_report',error)
        return {'counts':counts,'examples':samples,
                'invalid_total':sum(counts.values())}

def save_section(section, details, path=None):
    """Atomic local write; diagnostics failures are never import failures.

    No logging of product-level evidence; omitted from git and web output.
    """
    try:
        target=Path(path) if path is not None else PATH
        with _LOCK:
            target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists():
                try:
                    existing=json.loads(target.read_text(encoding='utf-8'))
                except (OSError,ValueError,UnicodeError):
                    existing={}
            else:
                existing={}
            if not isinstance(existing,dict):
                existing={}
            existing[section]=details
            data=json.dumps(existing,ensure_ascii=False,sort_keys=True,indent=2)
            with tempfile.NamedTemporaryFile('w',encoding='utf-8',
                   dir=target.parent,prefix='.diagnostic-',suffix='.tmp',
                   delete=False) as tmp:
                tmp.write(data)
                temp_path=Path(tmp.name)
            try:
                temp_path.replace(target)
            finally:
                temp_path.unlink(missing_ok=True)
        return True
    except Exception as error:
        warn('write',error)
        return False
