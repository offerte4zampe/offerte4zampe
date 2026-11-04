import unittest
from html.parser import HTMLParser
from pathlib import Path

from automation.apply_navigation import apply, PARTIALS


class Links(HTMLParser):
    def __init__(self, raw):
        super().__init__()
        self.links=[]
        self.feed(raw)
    def handle_starttag(self, tag, attrs):
        if tag=='a': self.links.append(dict(attrs))


class SocialLinksTests(unittest.TestCase):
    def test_shared_header_and_footer_reference_three_official_channels(self):
        header=(PARTIALS/'header.html').read_text()
        footer=(PARTIALS/'footer.html').read_text()
        canonical={
            'Instagram':'https://www.instagram.com/offerte4zampe/',
            'Facebook':'https://www.facebook.com/1459528943903012',
            'Telegram':'https://t.me/sconti4zampe',
        }
        for source in (header, footer):
            links=Links(source).links
            for name, url in canonical.items():
                matches=[a for a in links if a.get('href')==url]
                self.assertTrue(matches, name)
                self.assertTrue(all(a.get('target')=='_blank' for a in matches))
                self.assertTrue(all({'noopener','noreferrer'} <= set(a.get('rel','').split()) for a in matches))
                self.assertTrue(all(name in a.get('aria-label','') for a in matches))
        self.assertIn('class="mobile-socials"',header)
        self.assertIn('class="header-socials"',header)

    def test_home_invitation_has_real_links_and_is_idempotent(self):
        header=(PARTIALS/'header.html').read_text().strip()
        html='<!doctype html><html lang="it"><body>'+header+'<main><section class="daily-pick"></section><section class="advertising-wrap"></section></main><footer>old</footer></body></html>'
        result=apply(html)
        self.assertEqual(result.count('class="social-follow-section"'),1)
        self.assertEqual(result.count('class="social-follow-links"'),1)
        self.assertLess(result.index('class="social-follow-section"'),result.index('class="advertising-wrap"'))
        for target in ('https://www.instagram.com/offerte4zampe/', 'https://www.facebook.com/1459528943903012','https://t.me/sconti4zampe'):
            self.assertIn('href="'+target+'"',result)
        self.assertEqual(result,apply(result))

    def test_non_home_pages_do_not_gain_home_promotion(self):
        html='<main><h1>Pagina prodotto</h1></main>'
        self.assertEqual(apply(html),html)

    def test_no_external_scripts_or_social_widgets(self):
        for part in ['header.html','footer.html','social-home.html']:
            html=(PARTIALS/part).read_text()
            self.assertNotIn('<iframe',html)
            self.assertNotIn('<script',html)
            self.assertNotIn('rel="sponsored"',html)
            self.assertNotIn('fb-root',html)


if __name__=='__main__':
    unittest.main()
