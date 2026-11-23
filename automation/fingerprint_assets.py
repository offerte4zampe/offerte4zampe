"""Content-address local assets and cache them without rewriting merchant URLs."""
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit,urlunsplit
ROOT=Path(__file__).resolve().parents[1]
HASHED=re.compile(r'\.[a-f0-9]{12}\.[^.]+$')
EXTENSIONS={'.js','.css','.svg','.png','.jpg','.jpeg','.webp','.avif','.ico','.woff','.woff2'}
ATTR=re.compile(r'\b(src|href|content)=(\"|\')(.*?)\2',re.S|re.I)
QUOTED=re.compile(r'([\"\'])([^\"\'\n]+)\1')
CSS_URL=re.compile(r'url\(\s*([\"\']?)([^)\"\']+)\1\s*\)',re.I)
START='# BEGIN CONTENT ADDRESSED ASSETS'
END='# END CONTENT ADDRESSED ASSETS'

def restore(site):
    site=Path(site)
    try:mapping=json.loads((site/'asset-manifest.json').read_text())
    except (OSError,ValueError):return
    reverse={value:key for key,value in mapping.items()}
    def value(raw):
        try:u=urlsplit(raw)
        except ValueError:return raw
        if u.netloc and u.hostname!='offerte4zampe.it':return raw
        original=reverse.get('/'+u.path.lstrip('/'))
        if not original:return raw
        path='/assets/'+original
        return urlunsplit((u.scheme,u.netloc,path,u.query,u.fragment))
    for path in site.rglob('*.html'):
        before=path.read_text();after=ATTR.sub(lambda m:m[1]+'='+m[2]+value(m[3])+m[2],before)
        if after!=before:path.write_text(after)


def build(site):
    site=Path(site);assets=site/'assets'
    originals={p.name:p for p in assets.iterdir() if p.is_file() and p.suffix in EXTENSIONS and not HASHED.search(p.name)}
    previous_path=site/'asset-manifest.json'
    try:previous=json.loads(previous_path.read_text())
    except (OSError,ValueError):previous={}
    reverse={value:key for key,value in previous.items()}
    mapping={};active=set()
    literals=re.compile(r'([\"\'])((?:\./|/?assets/)?(?:'+ '|'.join(re.escape(n) for n in sorted(originals,key=len,reverse=True))+r')(?:\?[^\"\']*)?)\1')
    def asset_name(value,relative=False):
        try:u=urlsplit(value)
        except ValueError:return None
        if u.scheme and u.scheme!='https' or u.netloc and u.hostname!='offerte4zampe.it':return None
        path=u.path
        if path.startswith('/assets/'):name=path[len('/assets/'):]
        elif path.startswith('assets/'):name=path[len('assets/'):]
        elif relative and '/' not in path.lstrip('./'):name=path.removeprefix('./')
        else:return None
        return name if name in originals else None
    def resolve(value,relative=False):
        name=asset_name(value,relative)
        if not name:return value
        filename=process(name)
        u=urlsplit(value)
        if u.path.startswith('/assets/'):path='/assets/'+filename
        elif u.path.startswith('assets/'):path='/assets/'+filename
        else:path=('./' if u.path.startswith('./') else '')+filename
        return urlunsplit((u.scheme,u.netloc,path,u.query,u.fragment))
    def process(name):
        if name in mapping:return Path(mapping[name]).name
        if name in active:raise ValueError('Cyclic asset dependency: '+name)
        active.add(name);path=originals[name];raw=path.read_bytes()
        if path.suffix in ('.js','.css','.svg'):
            text=raw.decode()
            if path.suffix=='.css':text=CSS_URL.sub(lambda m:'url('+m[1]+resolve(m[2].strip(),True)+m[1]+')',text)
            elif path.suffix=='.js':text=literals.sub(lambda m:m[1]+resolve(m[2],True)+m[1],text)
            else:text=ATTR.sub(lambda m:m[1]+'='+m[2]+resolve(m[3],True)+m[2],text)
            raw=text.encode()
        filename=path.stem+'.'+hashlib.sha256(raw).hexdigest()[:12]+path.suffix
        (assets/filename).write_bytes(raw);mapping[name]='/assets/'+filename;active.remove(name);return filename
    for name in sorted(originals):process(name)
    def normalize(value):
        try:u=urlsplit(value)
        except ValueError:return value
        if u.netloc and u.hostname!='offerte4zampe.it':return value
        key='/'+u.path.lstrip('/')
        if key in reverse:
            original=reverse[key];path='/assets/'+original
            value=urlunsplit((u.scheme,u.netloc,path,u.query,u.fragment))
        return resolve(value)
    for path in site.rglob('*.html'):
        before=path.read_text()
        after=ATTR.sub(lambda m:m[1]+'='+m[2]+normalize(m[3])+m[2],before)
        def defer(m):
            tag=m[0]
            if re.search(r'\bsrc=',tag) and not re.search(r'\b(?:defer|async)\b',tag):return tag[:-1]+' defer>'
            return tag
        after=re.sub(r'<script\b[^>]*>',defer,after,flags=re.I)
        if after!=before:path.write_text(after)
    previous_path.write_text(json.dumps(mapping,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n')
    headers=site/'_headers';base=headers.read_text() if headers.exists() else ''
    base=re.sub(re.escape(START)+r'.*?'+re.escape(END)+r'\n?','',base,flags=re.S).rstrip()
    rules=['/data/*','  Cache-Control: public, max-age=60, stale-while-revalidate=300','/img/p/*','  Cache-Control: public, max-age=31536000, immutable']
    for value in sorted(mapping.values()):rules.extend([value,'  Cache-Control: public, max-age=31536000, immutable'])
    headers.write_text(base+'\n\n'+START+'\n'+'\n'.join(rules)+'\n'+END+'\n')
    print('Fingerprinted assets:',len(mapping),'· data cache 60s + SWR 300s')
    return mapping
if __name__=='__main__':
    import sys
    if '--restore' in sys.argv:restore(ROOT/'site')
    else:build(ROOT/'site')
