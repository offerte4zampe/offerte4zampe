"""Offline-only source audit of the compressed catalog committed on main."""
import copy
import gzip
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from automation.merchant_evidence import bauzaar_report, save_section, diagnostic_lines
from automation.gtin_diagnostics import gtin_counters

def main():
    base=subprocess.check_output(['git','merge-base','origin/main','HEAD'],cwd=ROOT,text=True).strip()
    raw=subprocess.check_output(['git','show',base+':site/data/catalog.json.gz'],cwd=ROOT)
    original=json.loads(gzip.decompress(raw))
    offers=original['offers']
    before=json.dumps(offers,ensure_ascii=False,sort_keys=True)
    bauzaar=[r for r in offers if r.get('merchant_id')=='bauzaar']
    report=bauzaar_report(bauzaar)
    counted=gtin_counters(bauzaar)
    assert report['invalid_total']==counted['invalid'], (report['invalid_total'],counted)
    assert all(len(v)<=10 for v in report['examples'].values())
    assert sum(report['counts'].values())==report['invalid_total']
    assert save_section('bauzaar',report)
    lines=diagnostic_lines()
    assert any(x.startswith('BAUZAAR_CATEGORY_COUNTS ') for x in lines)
    assert not any(x.startswith('PACO_EVIDENCE ') for x in lines)
    assert json.dumps(offers,ensure_ascii=False,sort_keys=True)==before
    print('BAUZAAR_LENGTH_EXAMPLES', [x['feed_gtin'] for x in report['examples']['length'][:5]])
    print('MERCHANT_EVIDENCE_SNAPSHOT',{
        'base_sha':base,'offers':len(offers),
        'bauzaar_invalid_total':report['invalid_total'],
        'bauzaar_categories':report['counts'],
        'offers_unchanged':True,'public_html_untouched':True,
        'examples_logged':False,
    })

if __name__=='__main__':
    main()
