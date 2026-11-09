"""Validate Wrangler's isolated Worker Preview output without printing raw logs."""
import argparse
import json
import re
import sys
from pathlib import Path

WORKER = 'zampachiara-staging'
ZONE = 'offerte4zampe.workers.dev'


def extract_preview_output(text):
    """Read one preview result, with an optional leading Wrangler session record."""
    decoder = json.JSONDecoder()
    objects = []
    offset = 0
    while offset < len(text):
        line_end = text.find('\n', offset)
        if line_end == -1:
            line_end = len(text)
        line = text[offset:line_end].lstrip()
        if line.startswith('{'):
            start = offset + len(text[offset:line_end]) - len(line)
            try:
                obj, end = decoder.raw_decode(text, start)
            except ValueError:
                raise ValueError('Malformed Wrangler JSON object') from None
            objects.append(obj)
            offset = end
            continue
        if line and not re.sub(r'\x1b\[[0-9;]*m', '', line).startswith('[custom build]'):
            raise ValueError('Unexpected content outside Wrangler JSON')
        offset = line_end + 1
    if objects and objects[0].get('type') == 'wrangler-session':
        session = objects.pop(0)
        if session.get('version') != 1:
            raise ValueError('Unsupported Wrangler session record')
    if len(objects) != 1 or objects[0].get('type') == 'wrangler-session':
        raise ValueError('Expected exactly one Wrangler preview result')
    return objects[0]


def preview_url(data, expected):
    if not re.fullmatch(r'phase2-[0-9]+', expected):
        raise ValueError('Invalid preview name')
    if 'preview' in data:
        preview = data['preview']
        deployment = data.get('deployment')
        if not isinstance(preview, dict) or not isinstance(deployment, dict):
            raise ValueError('Invalid Wrangler preview response')
        worker = data.get('worker_name', WORKER)
        name = preview.get('name')
        urls = preview.get('urls')
        deployment_urls = deployment.get('urls', [])
    else:
        worker = data.get('worker_name')
        name = data.get('preview_name')
        urls = data.get('preview_urls')
        deployment_urls = data.get('deployment_urls', [])
    if worker != WORKER or name != expected:
        raise ValueError('Unexpected Wrangler Worker or preview name')
    host = f'{expected}-{WORKER}.{ZONE}'
    url = f'https://{host}'
    if not isinstance(urls, list) or not urls or any(v not in (url, url + '/') for v in urls):
        raise ValueError('Expected the named staging preview HTTPS URL')
    deployment_pattern = rf'https://[a-f0-9]{{8}}-{WORKER}\.{re.escape(ZONE)}/?'
    if not isinstance(deployment_urls, list) or any(
        not isinstance(v, str) or not re.fullmatch(deployment_pattern, v)
        for v in deployment_urls
    ):
        raise ValueError('Unexpected deployment URL outside the staging Worker')
    return url


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('path', type=Path)
    parser.add_argument('--expected', required=True)
    args = parser.parse_args()
    try:
        print('url=' + preview_url(extract_preview_output(args.path.read_text()), args.expected))
    except (ValueError, OSError) as error:
        sys.exit(str(error))
