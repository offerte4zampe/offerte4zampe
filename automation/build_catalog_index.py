"""Publish bounded compressed search shards; keep merchant snapshots unchanged."""
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Fields consumed by comparison, identity, shipping and local user tools.
FIELDS = '''id title variant brand category price previous_price merchant_promotion available image image_local sku gtin weight_kg shipping_weight_kg shipping_weight_checked_at shipping_weight_source quantity_verified weight_conflict checked_at merchant merchant_id canonical_title canonical_format canonical_shop_count product_slug product_id product_matching_method product_identity_verified identity_review identity_expires_at quantity unit_price unit_price_unit'''.split()

def build(catalog, directory, chunk_size=1000):
    directory.mkdir(parents=True, exist_ok=True)
    manifest_path = directory.parent / 'catalog-index.json'
    try:
        previous = {Path(s['path']).name for s in json.loads(manifest_path.read_text())['shards']}
    except (OSError, ValueError, KeyError, TypeError):
        previous = set()
    offers = [dict({k: o[k] for k in FIELDS if k in o}, _order=i, affiliate=bool(o.get('affiliate_url'))) for i, o in enumerate(catalog['offers'])]
    offers.sort(key=lambda o: (str(o.get('brand', '')).casefold(), o['id']))
    shards = []
    for start in range(0, len(offers), chunk_size):
        rows = offers[start:start + chunk_size]
        raw = json.dumps({'offers': rows}, ensure_ascii=False, separators=(',', ':')).encode()
        compressed = gzip.compress(raw, mtime=0)
        name = hashlib.sha256(compressed).hexdigest()[:24] + '.json.gz'
        (directory / name).write_bytes(compressed)
        shards.append({'path': 'data/catalog-index/' + name, 'rows': len(rows), 'bytes': len(compressed)})
    manifest = {k: catalog.get(k) for k in ('generated_at', 'refresh_hours', 'sources')}
    manifest.update(version=1, rows=len(offers), shards=shards)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, separators=(',', ':')))
    # Retain the previous generation to cover clients reading during publication.
    keep = previous | {Path(s['path']).name for s in shards}
    for path in directory.glob('*.json.gz'):
        if path.name not in keep:
            path.unlink()
    return manifest

if __name__ == '__main__':
    catalog = json.loads(gzip.decompress((ROOT / 'site/data/catalog.json.gz').read_bytes()))
    result = build(catalog, ROOT / 'site/data/catalog-index')
    print(f"Catalog index: {result['rows']} offers, {len(result['shards'])} shards, {sum(s['bytes'] for s in result['shards'])} compressed bytes")
