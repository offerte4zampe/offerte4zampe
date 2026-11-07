import assert from 'node:assert/strict';
import fs from 'node:fs/promises';

export async function checkCoupons(page, origin) {
  await page.goto(origin + '/codici-sconto.html', { waitUntil: 'domcontentloaded' });
  assert.equal(await page.$$eval('main h1', es => es.length), 1);
  assert.equal(await page.$eval('link[rel=canonical]', e => e.href), 'https://offerte4zampe.it/codici-sconto');
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));

  const records = JSON.parse(await fs.readFile(new URL('../automation/coupons.json', import.meta.url), 'utf8')).coupons;
  const now = Date.now();
  const active = records.filter(r => {
    if (r.status !== 'cart_tested' || r.publication_allowed !== true || !r.cart_test) return false;
    const verified = Date.parse(r.verified_at);
    const start = Date.parse(r.starts_at);
    const end = Math.min(Date.parse(r.expires_at), Date.parse(r.recheck_after), verified + 48 * 3600000);
    return Number.isFinite(verified) && Number.isFinite(start) && Number.isFinite(end)
      && start <= now && now < end && verified <= now
      && r.cart_test.code === r.code && r.cart_test.currency === 'EUR'
      && Number.isInteger(r.cart_test.before_cents) && Number.isInteger(r.cart_test.after_cents)
      && r.cart_test.after_cents > 0 && r.cart_test.after_cents < r.cart_test.before_cents
      && Boolean(r.cart_test.product) && Boolean(r.cart_test.variant);
  });
  const visibleCodes = await page.$$eval('.coupon:not([hidden]) code', es => es.map(e => e.textContent.trim()).sort());
  assert.deepEqual(visibleCodes, active.map(r => r.code).sort());
  assert.equal(await page.$$eval('.coupon:not([hidden])', es => es.length), active.length);
  assert.equal(await page.$$eval('.coupon .status', es => es.some(e => e.textContent.includes('non ancora provato nel carrello'))), false);

  await page.click('.filter[data-shop=isola]');
  assert.equal(await page.$$eval('.coupon:not([hidden])', es => es.length), 0);
  assert(await page.$eval('#coupon-empty', e => !e.hidden));
  await page.click('.filter[data-shop=all]');
  for (const row of active) {
    assert(await page.$eval('main', (e, code) => e.textContent.includes(code), row.code));
  }
}
