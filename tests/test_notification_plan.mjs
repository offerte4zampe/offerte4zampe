import test from 'node:test';import assert from 'node:assert/strict';
import {offerIdentity,priceAlertDecision} from '../worker/notification-plan.mjs';
import {createRequire} from 'node:module';const {readiness}=createRequire(import.meta.url)('../site/assets/newsletter-readiness.js');
const now=Date.parse('2026-10-20T08:00:00Z'),offer={id:'bauzaar:1',merchant_id:'bauzaar',title:'Ricetta A',variant:'2 kg',brand:'Marca',gtin:'4006381333931',weight_kg:2,price:9,available:true,checked_at:'2026-10-20T07:00:00Z'};
const sub={id:'test-alert',contact_ref:'test-provider-reference',purpose:'price_alert',status:'active',notice_version:'test-only',confirmed_at:'2026-10-19T08:00:00Z',offer_id:offer.id,offer_identity:offerIdentity(offer),threshold_cents:1000,last_price_cents:1100,last_observed_at:'2026-10-20T01:00:00Z'};
test('newsletter stays unavailable until every verification and an approved HTTPS form exist',()=>{
 const ready={signup_url:'https://example.sibforms.com/form',double_opt_in_verified:true,unsubscribe_verified:true,privacy_notice_verified:true,separate_consent_verified:true,provider_permissions_verified:true};
 assert.equal(readiness(ready).ready,true);
 for(const key of Object.keys(ready)){assert.equal(readiness({...ready,[key]:null}).ready,false);}
 for(const url of ['https://sibforms.com.evil.test/','http://sibforms.com/','https://user:password@sibforms.com/'])assert.equal(readiness({...ready,signup_url:url}).ready,false);
});
test('plan only a fresh, available, exact-product crossing strictly below threshold',()=>{
 const plan=priceAlertDecision(sub,offer,now);assert.equal(plan.notify,true);assert.equal(plan.next.last_price_cents,900);
 for(const patch of [{status:'pending'},{status:'withdrawn',withdrawn_at:'2026-10-20'},{purpose:'newsletter'},{confirmed_at:null},{threshold_cents:NaN},{last_price_cents:900}])assert.equal(priceAlertDecision({...sub,...patch},offer,now).notify,false);
 for(const patch of [{price:10},{price:NaN},{available:false},{title:'Ricetta B'},{weight_kg:4},{checked_at:'2026-10-17T00:00:00Z'},{checked_at:'2026-10-21T00:00:00Z'}])assert.equal(priceAlertDecision(sub,{...offer,...patch},now).notify,false);
});
test('Amazon and unknown merchants cannot produce price alerts',()=>{
 const amazon={...offer,id:'amazon:1',merchant_id:'amazon'};
 const amazonSub={...sub,offer_id:amazon.id,offer_identity:offerIdentity(amazon)};
 assert.equal(priceAlertDecision(amazonSub,amazon,now).notify,false);
 assert.equal(priceAlertDecision(amazonSub,amazon,now).reason,'merchant_price_history_not_allowed');
 assert.equal(priceAlertDecision(sub,{...offer,merchant_id:'unknown-shop'},now).notify,false);
});
test('first observation, gaps and replay do not create repeated or backfilled alerts',()=>{
 assert.equal(priceAlertDecision({...sub,last_price_cents:null},offer,now).reason,'baseline_only');
 assert.equal(priceAlertDecision({...sub,last_observed_at:'2026-10-10T00:00:00Z'},offer,now).reason,'baseline_only');
 const first=priceAlertDecision(sub,offer,now);assert.equal(priceAlertDecision({...sub,...first.next},offer,now).reason,'already_observed');
});


test('configured hosted cancellation can be visible while signup remains closed',()=>{
 const {unsubscribeUrl}=createRequire(import.meta.url)('../site/assets/newsletter-readiness.js');
 const config={unsubscribe_form_configured:true,unsubscribe_url:'https://example.sibforms.com/serve/cancel'};
 assert.equal(unsubscribeUrl(config),config.unsubscribe_url);assert.equal(readiness(config).ready,false);
 for(const url of ['https://sibforms.com.evil.test/','http://example.sibforms.com/','https://user:pass@example.sibforms.com/'])assert.equal(unsubscribeUrl({...config,unsubscribe_url:url}),null);
 assert.equal(unsubscribeUrl({...config,unsubscribe_form_configured:false}),null);
});
