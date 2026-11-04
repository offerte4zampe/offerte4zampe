import unittest
from automation.phase2_preview_url import preview_url

class PreviewURLTest(unittest.TestCase):
    def test_named_preview_only(self):
        self.assertEqual(preview_url({'preview':{'url':'https://phase2-56-zampachiara.example.workers.dev/'}},'phase2-56'),'https://phase2-56-zampachiara.example.workers.dev')
    def test_production_and_ambiguous_urls_rejected(self):
        for data in [{'url':'https://offerte4zampe.it/'},{'url':'https://zampachiara.example.workers.dev/'},{'url':'https://phase2-57-zampachiara.example.workers.dev/'},{'urls':['https://phase2-56-a.example.workers.dev','https://phase2-56-b.example.workers.dev']}]:
            with self.subTest(data=data),self.assertRaises(ValueError):preview_url(data,'phase2-56')
    def test_credentials_queries_and_bad_names_rejected(self):
        for value in ['https://user@phase2-56-z.example.workers.dev','https://phase2-56-z.example.workers.dev/?token=test','https://phase2-56-z.example.workers.dev/#fragment']:
            with self.subTest(value=value),self.assertRaises(ValueError):preview_url({'url':value},'phase2-56')
        with self.assertRaises(ValueError):preview_url({},'main')
