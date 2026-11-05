import json
import unittest

from automation.phase2_preview_url import extract_preview_output, preview_url

URL = 'https://phase2-56-zampachiara-staging.offerte4zampe.workers.dev'
VERSION = 'https://34d5962c-zampachiara-staging.offerte4zampe.workers.dev'


def structured(**changes):
    return {
        'type': 'preview', 'worker_name': 'zampachiara-staging',
        'preview_name': 'phase2-56', 'preview_urls': [URL],
        'deployment_urls': [VERSION], **changes,
    }


class PreviewURLTest(unittest.TestCase):
    def test_structured_output(self):
        self.assertEqual(preview_url(extract_preview_output(json.dumps(structured())), 'phase2-56'), URL)

    def test_build_logs_then_json(self):
        response = {'preview': {'name': 'phase2-56', 'urls': [URL + '/']},
                    'deployment': {'urls': [VERSION]}}
        output = '[custom build] generated {"offers": 12}\n' + json.dumps(response, indent=2)
        self.assertEqual(preview_url(extract_preview_output(output), 'phase2-56'), URL)

    def test_missing_or_duplicate_json(self):
        obj = json.dumps(structured())
        for output in ('[custom build] no result\n', obj + '\n' + obj, obj + obj):
            with self.subTest(output=output), self.assertRaisesRegex(ValueError, 'exactly one'):
                extract_preview_output(output)

    def test_wrong_or_missing_host(self):
        for urls in ([], ['https://offerte4zampe.it/'],
                     [URL.replace('zampachiara-staging', 'zampachiara')],
                     [URL.replace('offerte4zampe.workers.dev', 'another.workers.dev')],
                     [URL.replace('https://', 'http://')], [URL, VERSION],
                     [URL + '?token=test'], [URL + '#fragment'],
                     [URL.replace('https://', 'https://user@')]):
            with self.subTest(urls=urls), self.assertRaises(ValueError):
                preview_url(structured(preview_urls=urls), 'phase2-56')

    def test_worker_name_preview_name_and_deployment_host(self):
        for changes in ({'worker_name': 'zampachiara'}, {'preview_name': 'phase2-57'},
                        {'deployment_urls': ['https://offerte4zampe.it/']}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                preview_url(structured(**changes), 'phase2-56')
        with self.assertRaises(ValueError):
            preview_url(structured(), 'main')
