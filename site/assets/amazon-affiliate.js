/* Amazon.it Associates link builder. No API, prices, images, scraping or automatic matching. */
(function(root){
  'use strict';
  const ASIN=/^[A-Z0-9]{10}$/;
  const TAG=/^[a-z0-9][a-z0-9-]{0,62}-21$/i;
  const GTIN=/^\d{8}(?:\d{4,6})?$/;
  const clean=s=>String(s==null?'':s).trim();
  const lower=s=>clean(s).normalize('NFKC').toLocaleLowerCase('it');
  function eligible(product, curated){
    if(!product || !curated || curated.reviewed!==true) return false;
    if(!ASIN.test(clean(curated.asin))) return false;
    if(!GTIN.test(clean(product.gtin)) || clean(product.gtin)!==clean(curated.gtin)) return false;
    if(!lower(product.brand) || lower(product.brand)!==lower(curated.brand)) return false;
    const p=Number(product.weight_kg), c=Number(curated.weight_kg);
    return Number.isFinite(p)&&p>0&&Number.isFinite(c)&&c>0&&Math.abs(p-c)<0.000001;
  }
  function affiliateUrl(product,curated,tag){
    if(!eligible(product,curated)||!TAG.test(clean(tag))) return null;
    return 'https://www.amazon.it/dp/'+clean(curated.asin)+'?tag='+encodeURIComponent(clean(tag));
  }
  const api=Object.freeze({eligible,affiliateUrl,disclosure:'In qualità di Affiliato Amazon ricevo un guadagno dagli acquisti idonei.'});
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
  root.O4ZAmazon=api;
})(typeof window!=='undefined'?window:globalThis);
