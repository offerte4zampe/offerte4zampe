import assert from 'node:assert/strict';

export function assertPreviewRedirect(response, affiliateTarget) {
  assert.equal(response.status, 302);
  assert.equal(response.headers.get('location'), affiliateTarget, 'Affiliate target must remain byte-for-byte intact');
  // The Worker is identical on main and the PR. Live /go/ returned "noindex, nofollow"
  // in production, while the isolated preview returned "noindex" on /go/ and its home.
  // Require the preview platform's noindex directive here; the Worker test stays strict.
  const directives = (response.headers.get('x-robots-tag') ?? '').split(',');
  assert(directives.some(directive => directive.trim().toLowerCase() === 'noindex'),
    'The isolated preview redirect must include the noindex directive');
}
