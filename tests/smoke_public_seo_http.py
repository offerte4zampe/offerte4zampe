#!/usr/bin/env python3
"""Read-only public SEO HTTP smoke. No affiliate, API, or admin endpoints."""
import json
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

BASE = "https://offerte4zampe.it"
CHECKS = ["/", "/robots.txt", "/sitemap.xml", "/sitemap-products.xml",
          "/sitemap-brands.xml", "/sitemap-guides.xml", "/sitemap-pages.xml",
          "/sitemap-categories.xml", "/codici-sconto", "/marca-acana",
          "/linea-monge-bwild", "/confrontare-prezzi-lettiere",
          "/prezzo-confezione-o-prezzo-kg"]
REPORT = []
HEADERS = {"User-Agent": "Offerte4Zampe-SEO-Smoke/1.0 (+https://offerte4zampe.it/)",
           "Accept": "text/html,application/xml,text/xml,*/*"}

class SEOParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.canonicals = []
        self.robots = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "link" and "canonical" in a.get("rel", "").lower().split():
            self.canonicals.append(a.get("href", ""))
        if tag == "meta" and a.get("name", "").lower() in ("robots", "googlebot"):
            self.robots.append(a.get("content", ""))

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

OPENER = urllib.request.build_opener(NoRedirect)

def inspect(path, expect_html=False, expect_index=False):
    url = BASE + path
    redirects = []
    record = {"path": path, "status": None, "location": None, "x_robots_tag": None,
              "canonical": [], "meta_robots": [], "redirects": [], "errors": []}
    try:
        for _ in range(5):
            request = urllib.request.Request(url, headers=HEADERS)
            try:
                response = OPENER.open(request, timeout=18)
            except urllib.error.HTTPError as exc:
                response = exc
            status = response.status
            location = response.headers.get("Location")
            record["status"] = status
            record["location"] = location
            record["x_robots_tag"] = response.headers.get("X-Robots-Tag")
            record["content_type"] = response.headers.get("Content-Type", "")
            if status in (301, 302, 303, 307, 308) and location:
                destination = urljoin(url, location)
                redirects.append({"status": status, "location": destination})
                if urlparse(destination).netloc != urlparse(BASE).netloc:
                    record["errors"].append("Unexpected cross-domain redirect")
                    break
                url = destination
                continue
            data = response.read(2_000_000)
            record["size"] = len(data)
            record["final_url"] = url
            record["redirects"] = redirects
            text = data.decode("utf-8", errors="replace")
            if "html" in record["content_type"] or expect_html:
                parser = SEOParser()
                parser.feed(text)
                record["canonical"] = parser.canonicals
                record["meta_robots"] = parser.robots
                if expect_html and status != 200:
                    record["errors"].append(f"Expected HTML HTTP 200, got {status}")
                if expect_html and status == 200:
                    expected_url = BASE + path
                    if parser.canonicals != [expected_url]:
                        record["errors"].append(f"Canonical differs from {expected_url}")
                    if expect_index and ("noindex" in str(parser.robots).lower() or
                                         "noindex" in str(record["x_robots_tag"]).lower()):
                        record["errors"].append("Indexable page served noindex")
            if path == "/robots.txt":
                if status != 200 or "Sitemap: " + BASE + "/sitemap.xml" not in text:
                    record["errors"].append("robots.txt missing expected sitemap declaration")
                record["allows_home"] = not bool(re.search(r"(?im)^Disallow:\s*/\s*$", text))
                if not record["allows_home"]:
                    record["errors"].append("robots.txt appears to disallow the entire site")
            if path.endswith(".xml"):
                if status != 200:
                    record["errors"].append(f"Sitemap returned HTTP {status}")
                else:
                    try:
                        root = ET.fromstring(data)
                        locs = [node.text for node in root.iter() if node.tag.endswith("}loc")]
                        record["xml_root"] = root.tag.split("}")[-1]
                        record["loc_count"] = len(locs)
                        record["example_locs"] = locs[:3]
                        if not locs:
                            record["errors"].append("Sitemap has no <loc> entries")
                        if any(not x.startswith(BASE + "/") for x in locs if x):
                            record["errors"].append("Sitemap contains unexpected-domain URLs")
                        if path == "/sitemap.xml":
                            expected = {BASE + "/sitemap-" + t + ".xml" for t in
                                        ("brands", "categories", "guides", "pages", "products")}
                            if not expected.issubset(set(locs)):
                                record["errors"].append("Sitemap index missing expected child sitemaps")
                    except ET.ParseError as exc:
                        record["errors"].append("Invalid XML: " + str(exc))
            break
        else:
            record["errors"].append("More than five redirects")
    except Exception as exc:
        record["errors"].append(type(exc).__name__ + ": " + str(exc))
    REPORT.append(record)
    return record

def main():
    html_paths = {"/", "/codici-sconto", "/marca-acana", "/linea-monge-bwild",
                  "/confrontare-prezzi-lettiere", "/prezzo-confezione-o-prezzo-kg"}
    for path in CHECKS:
        inspect(path, expect_html=path in html_paths, expect_index=path in html_paths)
    product_sitemap = next((x for x in REPORT if x["path"] == "/sitemap-products.xml"), None)
    if product_sitemap and product_sitemap.get("example_locs"):
        # Check a real product URL published in the sitemap, not a fabricated slug.
        samples = [u for u in product_sitemap["example_locs"] if "/prodotto/" in u]
        if samples:
            inspect(urlparse(samples[0]).path, expect_html=True, expect_index=True)
    failures = [(r["path"], e) for r in REPORT for e in r["errors"]]
    with open("seo-http-smoke-results.json", "w", encoding="utf-8") as f:
        json.dump({"base": BASE, "checks": REPORT, "failures": failures}, f,
                  indent=2, ensure_ascii=False)
    for r in REPORT:
        print(f'{r["status"]} {r["path"]} redirect={r["location"]} x-robots={r["x_robots_tag"]} '
              f'canonical={r["canonical"]} meta-robots={r["meta_robots"]} '
              f'loc-count={r.get("loc_count")}')
        for issue in r["errors"]:
            print("  FAIL:", issue)
    print(f"Checked {len(REPORT)} URLs; {len(failures)} problems.")
    return 1 if failures else 0

if __name__ == "__main__":
    sys.exit(main())
