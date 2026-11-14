"""Bounded merchant evidence. Descriptions/photos support review, never certify identity."""
import hashlib
import re
from html.parser import HTMLParser
from urllib.parse import urlsplit

class _Text(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts=[]; self.hidden=0
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'):self.hidden+=1
    def handle_endtag(self,tag):
        if tag in ('script','style'):self.hidden=max(0,self.hidden-1)
    def handle_data(self,text):
        if not self.hidden:self.parts.append(text)

def description_evidence(value,source,checked_at):
    if not isinstance(value,str) or len(value)>100000:return None
    try:
        u=urlsplit(source)
        if u.scheme!='https' or not u.hostname or u.username or u.password:return None
        parser=_Text();parser.feed(value)
        text=re.sub(r'\s+',' ',' '.join(parser.parts)).strip().casefold()
        # A title, slogan or empty HTML is not a distinctive description.
        if len(text)<120 or len(set(re.findall(r'\w+',text)))<20:return None
        return dict(sha256=hashlib.sha256(text.encode()).hexdigest(),characters=len(text),
                    source=source,checked_at=checked_at,scope='product_description_not_selected_variant')
    except (TypeError,ValueError):return None

def attach_description(row,value):
    evidence=description_evidence(value,row.get('url',''),row.get('checked_at',''))
    if evidence:row['description_evidence']=evidence
    return row

def image_fingerprint(offer,site,rules):
    """Read only the licensed cached ORIGINAL URL asset, never a shared canonical image."""
    try:
        try:from .image_policy import eligible
        except ImportError:from image_policy import eligible
        rule=rules.get(offer.get('merchant_id'),{})
        if not eligible(offer,rule):return None
        remote=offer.get('image','');u=urlsplit(remote)
        if u.scheme!='https' or u.hostname not in rule.get('hosts',[]):return None
        name=hashlib.sha256(remote.encode()).hexdigest()[:24]+'-400.webp'
        path=site/'img/p'/name
        if not path.is_file() or path.stat().st_size>2000000:return None
        from PIL import Image
        with Image.open(path) as image:
            if image.width*image.height>1000000:return None
            pixels=list(image.convert('RGB').resize((9,8)).convert('L').getdata())
            dhash=0
            for y in range(8):
                for x in range(8):dhash=(dhash<<1)|int(pixels[y*9+x]>pixels[y*9+x+1])
        return {'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'dhash':dhash}
    except (OSError,ValueError,ImportError):return None
