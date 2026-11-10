// Offline planning only. No fetch, email adapter, subscription endpoint or scheduler.
import {priceHistoryAllowed} from './price-merchant-policy.mjs';
export function offerIdentity(offer){
 return JSON.stringify(['id','title','variant','brand','gtin','weight_kg'].map(key=>offer?.[key]??null));
}

export function priceAlertDecision(subscription,offer,now=Date.now()){
 const no=reason=>({notify:false,reason});
 if(!priceHistoryAllowed(offer?.merchant_id))return no('merchant_price_history_not_allowed');
 if(subscription?.purpose!=='price_alert'||subscription.status!=='active'||subscription.withdrawn_at)return no('unconfirmed_or_withdrawn');
 const confirmation=Date.parse(subscription.confirmed_at);
 if(!Number.isFinite(confirmation)||confirmation>now||!subscription.notice_version)return no('consent_evidence_missing');
 if(!subscription.id||!subscription.contact_ref)return no('recipient_reference_missing');
 if(subscription.offer_id!==offer?.id||subscription.offer_identity!==offerIdentity(offer))return no('product_identity_changed');
 const stamp=Date.parse(offer.checked_at),price=offer.price;
 if(offer.available!==true||!Number.isFinite(price)||price<=0||!Number.isFinite(stamp)||stamp>now+300000||stamp<confirmation||now-stamp>36*3600000)return no('offer_not_recent_or_available');
 const threshold=subscription.threshold_cents;
 if(!Number.isSafeInteger(threshold)||threshold<1||threshold>100000000)return no('invalid_threshold');
 const current=Math.round(price*100),previous=subscription.last_price_cents,seen=Date.parse(subscription.last_observed_at);
 const next={last_price_cents:current,last_observed_at:offer.checked_at};
 if(Number.isFinite(seen)&&stamp<=seen)return no('already_observed');
 if(!Number.isSafeInteger(previous)||previous<1||!Number.isFinite(seen)||seen<confirmation||stamp-seen>36*3600000)return {...no('baseline_only'),next};
 if(previous<threshold||current>=threshold)return {...no('no_threshold_crossing'),next};
 return {notify:true,reason:'observed_threshold_crossing',event_key:subscription.id+':'+offer.id+':'+offer.checked_at,next};
}
