"""Corroborate a missing Shopify variant without inferring stock or replacements."""
import hashlib
import json
import re
from html.parser import HTMLParser
from urllib.parse import urlsplit

try:
    from .check_merchant_links import safe_product
except ImportError:
    from check_merchant_links import safe_product

SHOPIFY = ('bauzaar', 'webpet', 'animaliapet')


def numeric(value):
    return (not isinstance(value, bool) and str(value).isascii() and str(value).isdigit()
            and int(value) > 0 and str(int(value)) == str(value))


def missing_candidate(offer, body):
    """At the documented 250-variant API cap, absence is inconclusive."""
    try:
        if offer.get('merchant_id') not in SHOPIFY or not safe_product(offer):
            return None
        expected = offer['id'].split(':', 1)[1]
        url = urlsplit(offer['url'])
        path = url.path
        data = json.loads(body)
        variants = data.get('variants')
        if (offer['id'].split(':', 1)[0] != offer['merchant_id'] or url.query != 'variant=' + expected
                or not numeric(expected) or not numeric(data.get('id'))
                or path != '/products/' + data.get('handle', '')
                or not isinstance(variants, list) or not 0 < len(variants) < 250):
            return None
        ids = [str(v['id']) for v in variants if isinstance(v, dict) and numeric(v.get('id'))]
        if len(ids) != len(variants) or len(set(ids)) != len(ids) or expected in ids:
            return None
        return data
    except (ValueError, TypeError, KeyError, AttributeError):
        return None


class MainSelection(HTMLParser):
    """Read selected JSON only in pickers belonging to MainProduct's section."""
    def __init__(self, path):
        super().__init__(convert_charrefs=True)
        self.path = path
        self.canonicals = []
        self.main_count = 0
        self.main = {}
        self.depth = 0
        self.picker_depth = 0
        self.valid_picker = False
        self.script = None
        self.selected = []
        self.bad = False
        self.stack = []

    @staticmethod
    def inactive(tag, attrs):
        style = attrs.get('style') or ''
        return (tag in ('template', 'noscript') or 'inert' in attrs or 'hidden' in attrs
                or (attrs.get('aria-hidden') or '').lower() == 'true'
                or bool(re.search(r'(?:^|;)\s*(?:display\s*:\s*none|visibility\s*:\s*hidden)\b', style, re.I)))

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        own_inactive = self.inactive(tag, a)
        inactive = own_inactive or any(hidden for _, hidden in self.stack)
        if tag not in ('area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'):
            self.stack.append((tag, own_inactive))
        if tag == 'link' and not inactive and 'canonical' in (a.get('rel') or '').lower().split():
            self.canonicals.append(a.get('href'))
        if tag == 'product-info':
            if self.depth:
                self.depth += 1
            elif (a.get('id') or '').startswith('MainProduct-'):
                if inactive:
                    self.bad = True
                self.main_count += 1
                self.main = a
                self.depth = 1
        if tag == 'variant-selects' and self.depth == 1:
            if self.picker_depth or inactive:
                self.bad = True
            if not self.picker_depth:
                self.valid_picker = (bool(self.main.get('data-section'))
                                     and a.get('data-section') == self.main.get('data-section')
                                     and a.get('data-url') == self.path)
            self.picker_depth += 1
        if tag == 'script' and self.depth == 1 and 'data-selected-variant' in a:
            if inactive or not self.picker_depth or not self.valid_picker:
                self.bad = True
                return
            if a.get('type') != 'application/json' or self.script is not None:
                self.bad = True
            self.script = ''

    def handle_data(self, data):
        if self.script is not None:
            self.script += data

    def handle_endtag(self, tag):
        if tag == 'script' and self.script is not None:
            try:
                value = json.loads(self.script)
                if not isinstance(value, dict):
                    raise ValueError('selected variant is not an object')
                self.selected.append(value)
            except (ValueError, TypeError):
                self.bad = True
            self.script = None
        if tag == 'variant-selects' and self.depth == 1 and self.picker_depth:
            self.picker_depth -= 1
            if not self.picker_depth:
                self.valid_picker = False
        if tag == 'product-info' and self.depth:
            self.depth -= 1
        for i in range(len(self.stack)-1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break


def verify_missing_variant(offer, api_body, document, *, api_status, document_status):
    if api_status != 200 or document_status != 200:
        return None
    data = missing_candidate(offer, api_body)
    if data is None:
        return None
    try:
        url = urlsplit(offer['url'])
        canonical = url._replace(query='', fragment='').geturl()
        parser = MainSelection(url.path)
        parser.feed(document)
        parser.close()
        if (parser.bad or parser.script is not None or parser.depth != 0 or parser.picker_depth != 0
                or parser.main_count != 1 or parser.canonicals != [canonical]
                or parser.main.get('data-url') != url.path
                or str(parser.main.get('data-product-id')) != str(data['id'])
                or not parser.selected):
            return None
        ids = {str(v['id']): v for v in data['variants']}
        selected_ids = []
        for selected in parser.selected:
            sid = str(selected.get('id', ''))
            if sid not in ids:
                return None
            # The main selected object must describe this API variant, not just reuse an ID.
            for key in ('id', 'title', 'sku', 'barcode', 'price', 'available'):
                if key not in selected or key not in ids[sid] or selected[key] != ids[sid][key]:
                    return None
            selected_ids.append(sid)
        if len(set(selected_ids)) != 1:
            return None
        proof = {
            'exact_variant': offer['id'].split(':', 1)[1], 'variant_exists': False,
            'product_id': str(data['id']), 'html_product_id': str(parser.main['data-product-id']),
            'handle': data['handle'], 'remaining_variant_ids': sorted(ids),
            'html_selected_variant_ids': selected_ids,
            'api_url': canonical + '.js', 'document_url': offer['url'],
            'api_http_status': api_status, 'document_http_status': document_status,
            'api_sha256': hashlib.sha256(api_body.encode('utf-8')).hexdigest(),
            'document_sha256': hashlib.sha256(document.encode('utf-8')).hexdigest(),
        }
        return {'status': 'verified_missing_variant', 'compared': ['variant_exists'],
                'discrepancies': ['variant_exists'], 'evidence': proof,
                'reason': 'complete_api_absence_and_main_product_fallback'}
    except (ValueError, TypeError, KeyError, AttributeError):
        return None


def valid_missing_proof(offer, proof):
    """Validate the cached proof shape again before a row can be withheld."""
    try:
        if offer.get('merchant_id') not in SHOPIFY or not safe_product(offer):
            return False
        url = urlsplit(offer['url'])
        canonical = url._replace(query='', fragment='').geturl()
        ident = offer['id'].split(':', 1)[1]
        if offer['id'].split(':', 1)[0] != offer['merchant_id'] or url.query != 'variant=' + ident:
            return False
        ids = proof.get('remaining_variant_ids')
        selected = proof.get('html_selected_variant_ids')
        hashes = [proof.get('api_sha256', ''), proof.get('document_sha256', '')]
        return bool(
            numeric(ident) and proof.get('variant_exists') is False and proof.get('exact_variant') == ident
            and isinstance(proof.get('product_id'), str) and numeric(proof.get('product_id'))
            and proof.get('product_id') == proof.get('html_product_id')
            and url.path == '/products/' + proof.get('handle', '')
            and proof.get('api_url') == canonical + '.js' and proof.get('document_url') == offer['url']
            and proof.get('api_http_status') == 200 and proof.get('document_http_status') == 200
            and isinstance(ids, list) and 0 < len(ids) < 250
            and all(isinstance(v, str) and numeric(v) for v in ids)
            and len(set(ids)) == len(ids) and ident not in ids
            and isinstance(selected, list) and selected
            and all(isinstance(v, str) and numeric(v) for v in selected) and len(set(selected)) == 1
            and selected[0] != ident and selected[0] in ids
            and all(len(h) == 64 and all(c in '0123456789abcdef' for c in h) for h in hashes)
        )
    except (ValueError, TypeError, KeyError, AttributeError):
        return False
