import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {gunzipSync} from 'node:zlib';
import {assertPreviewRedirect} from './phase2_preview_redirect.mjs';

export async function checkShippingAcceptance(page, origin, catalog) {
  const rows=[],now=Date.now(),fresh=o=>o.available&&o.product_slug&&o.quantity?.verified!==false&&now-Date.parse(o.checked_at)<=36*3600000;
  const limits={bauzaar:59,'isola-dei-tesori':59,paco:79,webpet:39.9};
  const fees={bauzaar:6.9,'isola-dei-tesori':5.9,paco:5.9,webpet:5.9};
  const reference=JSON.parse(gunzipSync(await fs.readFile(process.env.MAIN_CATALOG_REFERENCE)));
  const mainOffers=new Map(reference.offers.map(o=>[o.id,o]));
  const money=n=>new Intl.NumberFormat('it-IT',{style:'currency',currency:'EUR'}).format(n);
  async function observe(o,q,territory='standard'){
    const response=await page.goto(origin+'/prodotto/'+o.product_slug+'?quantity='+q+'&territory='+territory,{waitUntil:'networkidle0'});
    assert.equal(response.status(),200);
    const observed=await page.evaluate(id=>{
      const a=[...document.querySelectorAll('.canonical-offers a[href^="/go/"]')].find(a=>decodeURIComponent(new URL(a.href).pathname.slice(4))===id);
      const row=a?.closest('tr');
      return {total:row?.querySelector('[data-label="Totale"]')?.textContent.trim(),shipping:row?.querySelector('[data-label="Spedizione"]')?.textContent.trim(),promo:!!row?.querySelector('[data-merchant-promo]'),overflow:document.documentElement.scrollWidth-innerWidth};
    },o.id);
    assert(observed.total,'The real offer must be visible: '+o.id);
    assert(observed.overflow<=1,'Mobile horizontal overflow: '+o.id);
    return observed;
  }
  async function record(o,q,label,expected,territory='standard'){
    const observed=await observe(o,q,territory);
    assert.equal(observed.total,expected,label+' '+o.id);
    if(expected==='Non calcolabile')assert(observed.shipping.includes(' · '),'Unknown total needs a visible reason');
    rows.push({case:label,id:o.id,product:o.title,quantity:q,expected,observed:observed.total,result:'passed'});
    return observed;
  }
  for(const [shop,threshold] of Object.entries(limits)){
    const weight=(o,q)=>shop!=='bauzaar'||o.shipping_weight_kg>0&&o.shipping_weight_kg*q<=35;
    const candidates=catalog.offers.filter(o=>o.merchant_id===shop&&fresh(o));
    const chosen=[];
    for(const kind of ['below','above','quantity']){
      const o=candidates.find(o=>!chosen.includes(o.id)&&weight(o,kind==='quantity'?2:1)&&(kind==='below'?o.price<threshold:kind==='above'?o.price>threshold:o.price<threshold&&o.price*2>threshold));
      assert(o,'A real '+kind+' product is required for '+shop);chosen.push(o.id);
      for(const q of kind==='quantity'?[1,2]:[1]){
        const sub=Math.round(o.price*q*100)/100,expected=money(sub+(sub>threshold?0:fees[shop]));
        await record(o,q,shop+' '+kind,expected);
      }
      const baseline=mainOffers.get(o.id);assert(baseline,'Missing main affiliate reference: '+o.id);
      const target=o.affiliate_url||o.url;
      assert.equal(target,baseline.affiliate_url||baseline.url,'Affiliate URL differs from main: '+o.id);
      const r=await fetch(origin+'/go/'+encodeURIComponent(o.id)+'?from=product',{redirect:'manual'});
      assertPreviewRedirect(r,target);
      rows.push({case:'affiliate bytes vs main',id:o.id,expected:'302 and identical Location',observed:'302 and identical Location',result:'passed'});
    }
    const o=candidates.find(o=>weight(o,1));assert(o);
    await record(o,1,shop+' excluded destinations and services','Non calcolabile','special');
    if(shop==='bauzaar'){
      const missing=candidates.find(o=>!o.shipping_weight_kg),heavy=candidates.find(o=>o.shipping_weight_kg*2>35&&o.shipping_weight_kg>0);
      assert(missing&&heavy,'Real missing-weight and overweight products required');
      await record(missing,1,'Bauzaar missing shipping weight','Non calcolabile');
      await record(heavy,2,'Bauzaar over 35 kg','Non calcolabile');
    }
  }
  for(const shop of ['animaliapet','hygge']){
    const o=catalog.offers.find(o=>o.merchant_id===shop&&fresh(o));assert(o);
    await record(o,1,shop+' unknown shipping','Non calcolabile');
  }
  // Controlled client-only fixtures exercise the deployed calculator at exact cents.
  // They never change stored offers, merchant sources, or the server-rendered catalog.
  const boundaries=await page.evaluate(async()=>{
    const rules=await fetch('/data/shipping-rules.json').then(r=>r.json()),out=[],now=Date.now();
    for(const [id,threshold,fee] of [['bauzaar',59,6.9],['isola-dei-tesori',59,5.9],['paco',79,5.9],['webpet',39.9,5.9]]){
      for(const cents of [-1,0,1]){
        const price=Math.round((threshold+cents/100)*100)/100;
        const offer={merchant_id:id,price,quantity_verified:true,checked_at:new Date(now).toISOString(),shipping_weight_kg:1};
        const quote=window.O4ZTrade.shipping(offer,rules,1,'standard',now);
        out.push({id,price,cents,status:quote.status,fee:quote.fee,total:quote.total,reason:quote.reason,expectedFee:cents<0?fee:0});
      }
    }
    return out;
  });
  for(const c of boundaries){
    assert.equal(c.status,c.cents===0?'unknown':'exact');
    if(c.cents===0){assert.equal(c.total,undefined);assert(c.reason);}
    else {assert.equal(c.fee,c.expectedFee);assert.equal(c.total,Math.round((c.price+c.expectedFee)*100)/100);}
    rows.push({case:'exact-cent deployed calculator fixture',id:c.id,price:c.price,expected:c.cents===0?'unknown with reason':'exact',observed:c.status,result:'passed'});
  }
  const promo=catalog.offers.find(o=>fresh(o)&&o.merchant_promotion&&now-Date.parse(o.merchant_promotion.observed_at)<=12*3600000);
  if(promo){
    const observed=await record(promo,1,'promotion with unknown total','Non calcolabile','special');
    assert(observed.promo,'Verified promotion must remain visible with unknown total');
  }else rows.push({case:'promotion with unknown total',expected:'visible',observed:'no fresh declared promotion in snapshot',result:'non simulato'});
  rows.push({case:'merchant checkout verification for the 12 products',expected:'same total without personal details',observed:'requires separate merchant checkout simulation',result:'non simulato'});
  return rows;
}
