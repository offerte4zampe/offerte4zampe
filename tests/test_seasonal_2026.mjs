import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { romeDay, seasonForDate, campaignForSeason, applySeason } from '../site/assets/seasonal-theme.mjs';

const at = iso => new Date(iso);
test('Black Week 23-30 November, in Europe/Rome', () => {
  assert.equal(seasonForDate(at('2026-11-22T22:59:59Z')), null);
  assert.equal(seasonForDate(at('2026-11-22T23:00:00Z')), 'blackfriday');
  assert.equal(seasonForDate(at('2026-11-27T10:00:00Z')), 'blackfriday');
  assert.equal(seasonForDate(at('2026-11-30T22:59:59Z')), 'blackfriday');
});
test('Christmas starts Dec 1 and expires Jan 6 Rome midnight', () => {
  assert.equal(seasonForDate(at('2026-11-30T23:00:00Z')), 'natale');
  assert.equal(seasonForDate(at('2026-12-25T10:00:00Z')), 'natale');
  assert.equal(seasonForDate(at('2027-01-06T22:59:59Z')), 'natale');
  assert.equal(seasonForDate(at('2027-01-06T23:00:00Z')), null);
});
test('preview can override calendar without persistence', () => {
  const date=at('2026-11-04T14:00:00Z');
  assert.equal(seasonForDate(date,'blackfriday'), 'blackfriday');
  assert.equal(seasonForDate(date,'natale'), 'natale');
  assert.equal(seasonForDate(at('2026-12-25T14:00:00Z'),'off'), null);
  assert.equal(seasonForDate(date,'unexpected'), null);
  assert.equal(romeDay(at('2026-11-22T23:00:00Z')), '2026-11-23');
});
test('campaign links are local and text promises no invented sale percentages', () => {
  for (const name of ['blackfriday','natale']) {
    const c=campaignForSeason(name);
    assert.match(c.href,/^\/[a-z-]+$/);
    assert.doesNotMatch(c.eyebrow+c.headline+c.detail, /(?:fino al|sconti fino|saldo garantito|−\d+%)/i);
    assert.ok(c.button.length>5);
  }
  assert.equal(campaignForSeason('bogus'),null);
});
test('theme adds only a stylesheet and a safe internal-link banner', () => {
  const nodes=[];
  const doc={
    documentElement:{dataset:{}},
    head:{append(node){nodes.push(node)}},
    createElement(tag){
      const node={tag,children:[],dataset:{},append(...xs){this.children.push(...xs)},setAttribute(key,value){this[key]=value}};
      nodes.push(node);return node;
    },
    querySelector(selector){return selector==='header'?{insertAdjacentElement(where,node){assert.equal(where,'afterend');nodes.push(node)}}:null},
    getElementById(){return null}
  };
  const result=applySeason({date:at('2026-11-04T15:00:00Z'),search:'?previewTheme=natale',doc});
  assert.equal(result,'natale');
  assert.equal(doc.documentElement.dataset.o4zSeason,'natale');
  assert.equal(doc.documentElement.dataset.o4zSeasonPreview,'true');
  assert.equal(nodes.find(n=>n.tag==='a').href,'/prodotti');
  assert.equal(new Set(nodes.filter(n=>n.tag==='link')).size,1);
  assert.equal(new Set(nodes.filter(n=>n.tag==='aside')).size,1);
  const visual=nodes.find(n=>n.tag==='img');
  assert.equal(visual.src,'/assets/christmas-hero.svg');
  assert.equal(visual.alt,'');
  assert.equal(nodes.some(n=>n.className==='o4z-season-proof'),true);

});
test('CSS scoped, responsive, reduced motion, no infinite animation',()=>{
  const css=readFileSync(new URL('../site/assets/seasonal-theme.css',import.meta.url),'utf8');
  assert.match(css,/data-o4z-season="blackfriday"/);
  assert.match(css,/data-o4z-season="natale"/);
  assert.match(css,/@media\(max-width:760px\)/);
  assert.match(css,/prefers-reduced-motion:reduce/);
  assert.doesNotMatch(css,/animation:\s*[^;]+infinite/);
});

test('season artwork includes valid inline SVG structure, no external media or JavaScript',()=>{
  for(const filename of ['black-week-hero.svg','christmas-hero.svg']){
    const content=readFileSync(new URL('../site/assets/'+filename,import.meta.url),'utf8');
    assert.match(content,/<svg[^>]+xmlns="http:\/\/www.w3.org\/2000\/svg"/);
    assert.match(content,/<title\b/);
    assert.match(content,/<desc\b/);
    assert.match(content,/<\/svg>\s*$/);
    assert.doesNotMatch(content,/<script|<foreignObject|onload=|javascript:|<image\b/i);
  }
});
test('prominent seasonal hero remains responsive and does not use endless motion',()=>{
  const css=readFileSync(new URL('../site/assets/seasonal-theme.css',import.meta.url),'utf8');
  assert.match(css,/o4z-season-visual img/);
  assert.match(css,/o4z-season-copy strong/);
  assert.match(css,/@media\(max-width:680px\)/);
  assert.match(css,/prefers-reduced-motion:reduce/);
  assert.doesNotMatch(css,/animation:[^;\n]*infinite/i);
});
