"""Guard WCAG contrast of critical mobile surfaces in both appearance modes.

The colors below mirror deliberate foreground/background pairs in style.css,
coupons.css and the editorial blog inline styles. We keep this test dependency
free so that the shared layout CI suite runs it on every pull request.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STYLE = ROOT / 'site/assets/style.css'
COUPONS = ROOT / 'site/assets/coupons.css'
BLOG = ROOT / 'site/blog/index.html'


def luminance(color):
    channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(foreground, background):
    high, low = sorted((luminance(foreground), luminance(background)), reverse=True)
    return (high + 0.05) / (low + 0.05)


class MobileContrastTests(unittest.TestCase):
    def test_critical_text_and_symbol_color_pairs(self):
        pairs = {
            'light navigation': ('#263f43', '#fffaf2'),
            'dark navigation': ('#e5f0ed', '#152d30'),
            'dark menu icon': ('#f0faf6', '#234543'),
            'light social icon': ('#214f3d', '#f3f8f1'),
            'dark social icon': ('#e5f0ed', '#244744'),
            'dark blog card': ('#e5f0ed', '#183235'),
            'dark blog link': ('#b8e4d3', '#183235'),
            'dark blog pill': ('#e7f7ec', '#2b5149'),
            'dark blog hero': ('#e5f0ed', '#1a3838'),
            'dark coupon value': ('#a5e4d7', '#2d2733'),
            'dark coupon disabled button': ('#d5e5df', '#394441'),
            'dark coupon copy icon': ('#f0faf6', '#354e49'),
        }
        for name, (fg, bg) in pairs.items():
            with self.subTest(name=name):
                self.assertGreaterEqual(contrast(fg, bg), 4.5)

    def test_theme_specific_rules_exist_in_public_assets(self):
        global_css = STYLE.read_text()
        coupons_css = COUPONS.read_text()
        blog_html = BLOG.read_text()
        self.assertIn('@media screen and (max-width:850px) and (prefers-color-scheme:dark)', global_css)
        self.assertIn('header .mobilemenu{background:#234543;color:#f0faf6', global_css)
        self.assertIn('header .navlinks>a{color:#e5f0ed}', global_css)
        self.assertIn('.brandlogo{background-color:#216d68}', global_css)
        self.assertIn('.coupon .discount{color:#a5e4d7}', coupons_css)
        self.assertIn('.blog-card{background:#183235;color:#e5f0ed', blog_html)
        self.assertIn('.blog-hero{background:linear-gradient(135deg,#1a3838,#213b35);color:#e5f0ed}', blog_html)
        for article in (ROOT / 'site/blog').glob('*/index.html'):
            self.assertIn('.blog-card{background:#183235;color:#e5f0ed', article.read_text())
