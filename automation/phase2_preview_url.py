"""Select only the named isolated workers.dev preview URL from Wrangler JSON."""
import argparse,json,re,sys
from urllib.parse import urlsplit

def preview_url(data,expected):
    if not re.fullmatch(r'phase2-[0-9]+',expected):raise ValueError('Invalid preview name')
    def strings(value):
        if isinstance(value,str):yield value
        elif isinstance(value,dict):
            for item in value.values():yield from strings(item)
        elif isinstance(value,list):
            for item in value:yield from strings(item)
    candidates=[]
    for text in strings(data):
        try:u=urlsplit(text)
        except ValueError:continue
        host=u.hostname or ''
        if u.scheme=='https' and host.endswith('.workers.dev') and (host.startswith(expected+'-') or host.startswith(expected+'.')) and not u.username and not u.password and u.port in (None,443) and u.path in ('','/') and not u.query and not u.fragment:
            candidates.append(text.rstrip('/'))
    candidates=list(dict.fromkeys(candidates))
    if len(candidates)!=1:raise ValueError('Expected exactly one named isolated preview URL')
    return candidates[0]

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('path');p.add_argument('--expected',required=True);a=p.parse_args()
    try:print('url='+preview_url(json.load(open(a.path)),a.expected))
    except (ValueError,OSError) as error:sys.exit(str(error))
