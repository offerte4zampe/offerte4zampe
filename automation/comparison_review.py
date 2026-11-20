"""Manual review holds affect canonical comparisons only, never merchant fields.

A due review is still unverified: time and feed price changes cannot authorize
joining an uncertain commercial identity. Release requires an explicit reviewed
manifest change. Malformed or missing configuration aborts the build.
"""
import datetime as dt
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

MANIFEST = Path(__file__).with_name('comparison-review-holds.json')
MERCHANTS = {'bauzaar', 'webpet', 'animaliapet', 'isola-dei-tesori', 'paco', 'hygge'}


def stamp(value):
    parsed = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('comparison review dates require timezone')
    return parsed


def validate_manifest(data):
    if not isinstance(data, dict) or (type(data.get('schema_version')) is not int or data.get('schema_version') != 1) or not isinstance(data.get('holds'), list):
        raise ValueError('invalid comparison review manifest')
    if len(data['holds']) > 1000:
        raise ValueError('comparison review manifest too large')
    holds = {}
    for entry in data['holds']:
        try:
            if not isinstance(entry, dict) or entry['review_state'] != 'unverified':
                raise ValueError('release requires explicit removal of the reviewed hold')
            oid, merchant = entry['offer_id'], entry['merchant_id']
            if merchant not in MERCHANTS or not isinstance(oid, str) or not re.fullmatch(re.escape(merchant)+r':[A-Za-z0-9_-]{1,100}', oid):
                raise ValueError('invalid exact merchant offer binding')
            if oid in holds:
                raise ValueError('duplicate comparison review hold')
            if not isinstance(entry['reason'], str) or not 10 <= len(entry['reason']) <= 2000:
                raise ValueError('comparison review reason required')
            if stamp(entry['review_due']) < stamp(entry['reviewed_at']):
                raise ValueError('invalid comparison review dates')
            sources = entry['sources']
            if not isinstance(sources, list) or not 1 <= len(sources) <= 10:
                raise ValueError('comparison review sources required')
            for source in sources:
                if not isinstance(source, str) or len(source) > 2000:
                    raise ValueError('invalid comparison review source')
                url = urlsplit(source)
                if url.scheme != 'https' or not url.hostname or url.username or url.password or url.fragment:
                    raise ValueError('invalid comparison review source')
            holds[oid] = entry
        except (KeyError, TypeError, AttributeError) as error:
            raise ValueError('malformed comparison review hold') from error
    return holds


def review_holds(offers, now, manifest=None):
    data = json.loads(MANIFEST.read_text()) if manifest is None else manifest
    configured = validate_manifest(data)
    applied = {}
    for offer in offers:
        entry = configured.get(offer['id'])
        if entry is None:
            continue
        if offer.get('merchant_id') != entry['merchant_id']:
            raise ValueError('comparison review merchant mismatch')
        applied[offer['id']] = {k: entry[k] for k in ('review_state', 'reason', 'reviewed_at', 'review_due', 'sources')}
        applied[offer['id']]['review_due_reached'] = now >= stamp(entry['review_due'])
    return applied
