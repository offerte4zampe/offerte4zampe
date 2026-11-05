import assert from 'node:assert/strict';
import test from 'node:test';
import {assertPreviewRedirect} from './phase2_preview_redirect.mjs';

const target = 'https://affiliate.example/redirect?a=1&u=https%3A%2F%2Fshop.example%2F';
function reply(robots, status = 302, location = target) {
  const headers = new Headers({location});
  if (robots !== null) headers.set('x-robots-tag', robots);
  return new Response(null, {status, headers});
}

test('preview redirect accepts a noindex directive with or without nofollow', () => {
  for (const robots of ['noindex', 'noindex, nofollow', 'nofollow, NOINDEX']) {
    assert.doesNotThrow(() => assertPreviewRedirect(reply(robots), target));
  }
});

test('preview redirect rejects missing noindex and substring lookalikes', () => {
  for (const robots of [null, '', 'index', 'nofollow', 'not-noindex', 'noindexing']) {
    assert.throws(() => assertPreviewRedirect(reply(robots), target), /must include the noindex directive/);
  }
});

test('preview redirect rejects other status codes and byte differences in Location', () => {
  assert.throws(() => assertPreviewRedirect(reply('noindex', 301), target), {code: 'ERR_ASSERTION'});
  const differentBytes = target.replace('%3A', '%3a');
  assert.throws(() => assertPreviewRedirect(reply('noindex', 302, differentBytes), target),
    /Affiliate target must remain byte-for-byte intact/);
});
