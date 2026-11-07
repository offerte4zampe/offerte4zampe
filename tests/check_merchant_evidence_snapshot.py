"""Offline-only source audit of the compressed catalog committed on main."""
import copy
import gzip
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from automation.merchant_evidence import bauzaar_report, save_section
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
    with tempfile.TemporaryDirectory() as temp:
        path=Path(temp)/'private'/'report.json'
        assert save_section('bauzaar',report,path)
        assert json.loads(path.read_text())['bauzaar']==report
        assert not (ROOT/'site/data/report.json').exists()
    assert json.dumps(offers,ensure_ascii=False,sort_keys=True)==before
    print('MERCHANT_EVIDENCE_SNAPSHOT',{
        'base_sha':base,'offers':len(offers),
        'bauzaar_invalid_total':report['invalid_total'],
        'bauzaar_categories':report['counts'],
        'offers_unchanged':True,'public_html_untouched':True,
        'examples_logged':False,
    })

if __name__=='__main__':
    main()
