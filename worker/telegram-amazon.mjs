// Manually curated, original editorial entries only. No Amazon scraping, pricing,
// Product Advertising Content, historical prices, or alerting.
const AMAZON_HOST = 'www.amazon.it';
export function amazonMode(env) {
  return env.TELEGRAM_CONTENT_MODE === 'amazon_only';
}
export function amazonApproved(env) {
  // Owner opt-in is not a statement of approval by Amazon.
  return amazonMode(env) && env.TELEGRAM_AMAZON_OWNER_ENABLED === 'true';
}
export function amazonLink(asin, tag) {
  if (!/^[A-Z0-9]{10}$/.test(asin)) throw new Error('invalid_asin');
  if (typeof tag !== 'string' || !/^[a-z0-9][a-z0-9-]{2,60}-21$/.test(tag)) throw new Error('invalid_associate_tag');
  const u = new URL('https://' + AMAZON_HOST + '/dp/' + asin);
  u.searchParams.set('tag', tag);
  return u.href;
}
export function amazonPick(entry, now = Date.now()) {
  if (!entry || typeof entry !== 'object' || !/^[A-Z0-9]{10}$/.test(entry.asin || '')) return null;
  if (typeof entry.title !== 'string' || entry.title.trim().length < 8 || entry.title.length > 140) return null;
  if (typeof entry.note !== 'string' || entry.note.trim().length < 20 || entry.note.length > 280) return null;
  if (entry.editorial_reviewed !== true) return null;
  if (entry.image && entry.rights_confirmed !== true) return null;
  const review = Date.parse(entry.reviewed_at);
  if (!Number.isFinite(review) || review > now || now - review > 30 * 86400000) return null;
  // Only a self-owned original product photo, not Amazon media or hotlinks.
  if (entry.image != null && (typeof entry.image !== 'string' || !/^\/assets\/telegram-amazon\/[a-z0-9-]+\.(?:jpg|jpeg|png)$/i.test(entry.image))) return null;
  return {
    id: 'amazon:' + entry.asin,
    kind: 'amazon_pick',
    asin: entry.asin,
    title: entry.title.trim(),
    note: entry.note.trim(),
    image: entry.image || null,
    reviewed_at: review
  };
}
export function amazonText(post, link, escape) {
  // Keep the affiliation notice clear and adjacent to the link.
  const disclosure = '#pubblicità · link affiliato';
  const title = '✨ <b>' + escape(post.title) + '</b>';
  const text = '🐾 <b>SCELTO PER TE</b>\n\n' + title +
    '\n\n💡 ' + escape(post.note) +
    '\n\n<a href="' + escape(link) + '">🛒 Scoprilo su Amazon</a>' +
    '\n\n' + escape(disclosure);
  const visible = '🐾 SCELTO PER TE\n\n✨ ' + post.title + '\n\n💡 ' + post.note +
    '\n\n🛒 Scoprilo su Amazon\n\n' + disclosure;
  if (Array.from(visible).length > (post.image ? 1024 : 4096)) throw new Error('message_too_long');
  if (post.image) return {method:'sendPhoto',body:{chat_id:'@sconti4zampe',photo:'https://offerte4zampe.it'+post.image,caption:text,parse_mode:'HTML'}};
  return {method:'sendMessage',body:{chat_id:'@sconti4zampe',text,parse_mode:'HTML',link_preview_options:{is_disabled:true}}};
}
