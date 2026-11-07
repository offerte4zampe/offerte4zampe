"""Private, best-effort merchant evidence from data already fetched.

Read-only capture in memory; authorized evidence is emitted to GitHub Actions
logs and step summary only. Never commit or upload a separate artifact.
"""
import hashlib
import json
import logging
import re
import threading

_LOCK = threading.Lock()
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
                if raw is None or (isinstance(raw, str) and not raw.strip()):
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


# This is per-process memory only. No output file in the checkout.
_SECTIONS={}

def save_section(section, details, path=None):
    """Retain allowlisted diagnostics in memory; never writes a disk file.

    `path` is ignored for compatibility with callers; neither the repository nor
    the runner filesystem is used to persist product-level records.
    """
    try:
        if section not in ('paco','bauzaar'):
            return False
        with _LOCK:
            if section == 'paco':
                entries=details.get('records',[]) if isinstance(details,dict) else []
                _SECTIONS[section]={
                    'records': [r for r in entries[:80] if isinstance(r,dict)],
                    'checked_at':safe_value(details.get('checked_at'),40),
                    'aggregate':details.get('aggregate',{}),
                }
            else:
                _SECTIONS[section]={
                    'counts':dict(details.get('counts',{})),
                    'invalid_total':int(details.get('invalid_total',0)),
                }
        return True
    except Exception as error:
        warn('capture',error)
        return False

def diagnostic_lines():
    """Return only explicitly authorized product fields and aggregate counts."""
    try:
        with _LOCK:
            paco=dict(_SECTIONS.get('paco',{}))
            bauzaar=dict(_SECTIONS.get('bauzaar',{}))
        allowed=('offer_id','feed_gtin','page_ean13','feed_sku','page_variant_id',
                 'feed_title','page_variant_label','failure_reason','checked_at',
                 'identity_fingerprint')
        records=paco.get('records',[])[:80]
        lines=['MERCHANT_DIAGNOSTICS_BEGIN']
        for record in records:
            lines.append('PACO_EVIDENCE '+json.dumps(
                {k:record[k] for k in allowed if k in record},
                ensure_ascii=False,sort_keys=True,separators=(',',':')))
        from collections import Counter
        reasons=Counter(r.get('failure_reason') or 'success' for r in records)
        aggregate=paco.get('aggregate',{})
        official=aggregate.get('failures',{})
        reason_counts=(dict(official) if isinstance(official,dict) else {})
        reason_counts['success']=int(aggregate.get('succeeded',reasons.get('success',0)))
        lines.append('PACO_REASON_COUNTS '+json.dumps(
            dict(sorted(reason_counts.items())),sort_keys=True,separators=(',',':')))
        budget={key:int(aggregate.get(key,0)) for key in
                ('scheduled','attempted','succeeded','skipped_limit','reused_proof')}
        lines.append('PACO_VERIFICATION_COUNTS '+json.dumps(
            budget,sort_keys=True,separators=(',',':')))
        counts=bauzaar.get('counts',{})
        lines.append('BAUZAAR_CATEGORY_COUNTS '+json.dumps(
            {k:int(counts.get(k,0)) for k in CATEGORIES},
            sort_keys=True,separators=(',',':')))
        lines.append('MERCHANT_DIAGNOSTICS_END')
        return lines
    except Exception as error:
        warn('format',error)
        return []

def emit_summary():
    """Print bounded diagnostics and GitHub summary, without other fields."""
    try:
        lines=diagnostic_lines()
        for line in lines:
            print(line,flush=True)
        import os
        summary=os.environ.get('GITHUB_STEP_SUMMARY')
        if summary and lines:
            # The only file opened is the GitHub-provided step summary, outside
            # the repository. GitHub itself makes the same data visible in logs.
            with open(summary,'a',encoding='utf-8') as handle:
                handle.write('## Merchant diagnostics\\n\\n')
                for line in lines:
                    handle.write('\\`' + line.replace('\\`', r'\\\\`') + '\\`\\n')
    except Exception as error:
        warn('emit',error)
