import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url),trade=require('../site/assets/trade.js');
export async function checkMerchantPromotions(page,origin,catalog){
 const now=Date.parse(catalog.generated_at),offer=catalog.offers.find(o=>trade.merchantPromotion(o,now)&&o.product_slug&&o.title.length<=110);
 if(!offer){console.log('MERCHANT_PROMOTION no fresh declared promotion in this snapshot; synthetic unit cases still run');return}
 await page.goto(origin+'/prodotto/'+offer.product_slug,{waitUntil:'domcontentloaded'});
 await page.waitForSelector('[data-merchant-promo]',{visible:true});
 assert((await page.$eval('[data-merchant-promo]',e=>e.textContent)).includes('sul riferimento'));
 await page.goto(origin+'/confronta-cibo?shop='+encodeURIComponent(offer.merchant)+'&q='+encodeURIComponent(offer.title),{waitUntil:'domcontentloaded'});
 await page.waitForSelector('#catalog-grid [data-merchant-promo]',{visible:true,timeout:60000});
 const data=await page.$eval('#catalog-grid [data-merchant-promo]',e=>({text:e.textContent,oldPrice:e.querySelector('s')?.textContent,overflow:document.documentElement.scrollWidth-innerWidth}));
 assert(data.oldPrice);assert(data.text.includes('PROMO NEGOZIO'));assert(data.overflow<=1);
 await page.screenshot({path:'browser-reports/merchant-promotion-mobile.png',fullPage:true});
 console.log('MERCHANT_PROMOTION '+JSON.stringify({offer_id:offer.id,...data}));
}
