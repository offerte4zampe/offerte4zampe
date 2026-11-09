"""Read-only shipping evidence monitor; never renews or modifies any rule.

The default 14-day warning window is operational notice, not rule validity.
Expired or missing rules produce warnings; --fail-on-expired is opt-in.
"""
import argparse
import datetime as dt
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_MERCHANTS = ('bauzaar', 'webpet', 'animaliapet', 'isola-dei-tesori', 'paco', 'hygge')
WARNING_HOURS = 14 * 24


def parse(value):
    if not isinstance(value, str):
        raise ValueError('missing date')
    parsed = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    return parsed.replace(tzinfo=parsed.tzinfo or dt.timezone.utc)


def report(data, now, expected=EXPECTED_MERCHANTS, warn_hours=WARNING_HOURS):
    rows = []
    for merchant in sorted(set(data.get('merchants', {})) | set(expected)):
        rule = data.get('merchants', {}).get(merchant)
        if rule is None:
            rows.append({'merchant': merchant, 'status': 'missing', 'quote_status': 'unknown',
                         'reason': 'Nessuna regola documentata; totale sconosciuto'})
            continue
        row = {'merchant': merchant, 'source': rule.get('source'),
               'checked_at': rule.get('checked_at', data.get('checked_at')),
               'verified_until': rule.get('verified_until')}
        try:
            checked, until = parse(row['checked_at']), parse(row['verified_until'])
            if until < checked or checked > now + dt.timedelta(minutes=5):
                raise ValueError('invalid dates')
            hours = (until - now).total_seconds() / 3600
            row.update(status='expired' if hours <= 0 else 'expiring' if hours <= warn_hours else 'current',
                       hours_remaining=round(hours, 2))
        except (TypeError, ValueError, OverflowError):
            row.update(status='invalid', reason='Verifica o scadenza assente/non valida')
        if rule.get('conflict'):
            row.update(quote_status='conflict', reason='Indicazioni del negozio non coerenti')
        elif rule.get('status') in ('uncertain', 'unknown'):
            row.update(quote_status='unknown', reason='Condizioni non verificate')
        elif row['status'] in ('expired', 'invalid'):
            row['quote_status'] = 'unknown'
        else:
            row['quote_status'] = 'requires_offer_check'
        rows.append(row)
    return {'as_of': now.isoformat(), 'warning_hours': warn_hours, 'merchants': rows,
            'action': 'Riverificare le fonti. Il monitor non modifica tariffe, date o condizioni.'}


def annotation_message(value):
    return str(value).replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path', nargs='?', type=Path, default=ROOT / 'site/data/shipping-rules.json')
    parser.add_argument('--now', help='UTC timestamp for reproducible checks')
    parser.add_argument('--warn-hours', type=float, default=WARNING_HOURS)
    parser.add_argument('--expected', default=','.join(EXPECTED_MERCHANTS))
    parser.add_argument('--fail-on-expired', action='store_true',
                        help='Fail on expired/invalid/missing evidence; default is warning only')
    parser.add_argument('--annotations', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    if not 0 <= args.warn_hours < float('inf'):
        parser.error('--warn-hours must be finite and nonnegative')
    if args.output and args.output.resolve() == args.path.resolve():
        parser.error('--output must not replace the source rules')
    now = parse(args.now) if args.now else dt.datetime.now(dt.timezone.utc)
    result = report(json.loads(args.path.read_text()), now,
                    filter(None, args.expected.split(',')), args.warn_hours)
    encoded = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded)
    print(encoded, end='')
    if args.annotations:
        for row in result['merchants']:
            if row['status'] != 'current' or row['quote_status'] in ('conflict', 'unknown'):
                message = f"{row['merchant']}: {row['status']}; {row.get('reason', 'verificare la fonte prima della scadenza')}. Nessun rinnovo automatico."
                print('::warning title=Shipping evidence::' + annotation_message(message), file=sys.stderr)
    return int(args.fail_on_expired and any(row['status'] in ('expired', 'invalid', 'missing')
                                           for row in result['merchants']))


if __name__ == '__main__':
    sys.exit(main())
