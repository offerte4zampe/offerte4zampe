/* Seasonal site decoration. Never changes offer prices, discounts or ranking.
 * Calendar is interpreted in Europe/Rome and preview does not persist.
 */
const ROME_TZ = 'Europe/Rome';
export function romeDay(date = new Date()) {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: ROME_TZ, year: 'numeric', month: '2-digit', day: '2-digit'
  }).formatToParts(date);
  const values = Object.fromEntries(parts.map(p => [p.type, p.value]));
  return values.year + '-' + values.month + '-' + values.day;
}
export function seasonForDate(date = new Date(), preview = null) {
  if (preview === 'blackfriday' || preview === 'natale') return preview;
  if (preview === 'off') return null;
  const day = romeDay(date);
  if (day >= '2026-11-23' && day <= '2026-11-30') return 'blackfriday';
  if (day >= '2026-12-01' && day <= '2027-01-06') return 'natale';
  return null;
}
const CAMPAIGNS = Object.freeze({
  blackfriday: Object.freeze({
    eyebrow: 'BLACK WEEK A 4 ZAMPE',
    headline: 'BLACK WEEK. IL RISPARMIO HA FIUTO.',
    detail: 'Prezzi sotto la lente, non slogan: scopri il prezzo migliore sullo stesso prodotto.',
    button: 'FIUTA LE OFFERTE',
    href: '/black-friday-animali'
  }),
  natale: Object.freeze({
    eyebrow: 'NATALE A 4 ZAMPE',
    headline: 'A NATALE, OGNI ZAMPA MERITA UN REGALO.',
    detail: 'Giochi, coccole e sorprese: trova qualcosa di speciale e confronta prima di scegliere.',
    button: 'SCOPRI I REGALI',
    href: '/prodotti'
  })
});
export function campaignForSeason(season) { return CAMPAIGNS[season] || null; }
export function applySeason({ date = new Date(), search = '', doc = document } = {}) {
  const preview = new URLSearchParams(search).get('previewTheme');
  const season = seasonForDate(date, preview);
  if (!season) return null;
  const info = campaignForSeason(season);
  const root = doc.documentElement;
  root.dataset.o4zSeason = season;
  if (preview === season) root.dataset.o4zSeasonPreview = 'true';
  const css = doc.createElement('link');
  css.rel = 'stylesheet';
  css.href = '/assets/seasonal-theme.css?v=2026-2';
  css.dataset.o4zSeasonStyle = '';
  doc.head.append(css);
  const header = doc.querySelector('header');
  if (header && !doc.getElementById('o4z-season-ribbon')) {
    const section = doc.createElement('aside');
    section.id = 'o4z-season-ribbon';
    section.className = 'o4z-season-ribbon';
    section.setAttribute('aria-label', 'In evidenza: ' + info.eyebrow);
    const wrap = doc.createElement('div');
    wrap.className = 'o4z-season-ribbon-inner';
    const text = doc.createElement('div');
    text.className = 'o4z-season-copy';
    const kicker = doc.createElement('span');
    kicker.className = 'o4z-season-kicker';
    kicker.textContent = (preview === season ? 'ANTEPRIMA · ' : '') + info.eyebrow;
    const title = doc.createElement('strong');
    title.textContent = info.headline;
    const detail = doc.createElement('span');
    detail.className = 'o4z-season-explain';
    detail.textContent = info.detail;
    text.append(kicker, title, detail);
    const trust = doc.createElement('span');
    trust.className = 'o4z-season-proof';
    trust.textContent = season === 'blackfriday'
      ? '● Confronti verificati  ·  ● Stesso prodotto  ·  ● Prezzi aggiornati'
      : '✦ Idee per cani e gatti  ·  ✦ Confronta più negozi';
    text.append(trust);
    const visual = doc.createElement('div');
    visual.className = 'o4z-season-visual';
    visual.setAttribute('aria-hidden', 'true');
    const image = doc.createElement('img');
    image.src = season === 'blackfriday' ? '/assets/black-week-hero.svg' : '/assets/christmas-hero.svg';
    image.alt = '';
    image.width = 660;
    image.height = 470;
    image.decoding = 'async';
    visual.append(image);
    const link = doc.createElement('a');
    link.className = 'o4z-season-link';
    link.href = info.href;
    link.textContent = info.button + ' →';
    const action = doc.createElement('div');
    action.className = 'o4z-season-actions';
    action.append(link);
    wrap.append(text, visual, action);
    section.append(wrap);
    header.insertAdjacentElement('afterend', section);
  }
  return season;
}
if (typeof document !== 'undefined' && typeof location !== 'undefined') {
  applySeason({search: location.search});
}
