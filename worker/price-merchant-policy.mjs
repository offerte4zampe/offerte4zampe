// Merchant-specific filter for price-derived notifications.
// The global PRICE_TRACKING_ENABLED emergency switch remains in PR #63.
const ALLOWED = new Set(['bauzaar','isola-dei-tesori','paco','webpet','animaliapet']);
export function priceHistoryAllowed(merchantId){
  return typeof merchantId==='string' && ALLOWED.has(merchantId.trim().toLowerCase());
}
export function historicalOfferAllowed(offerId){
  return typeof offerId==='string' && offerId.includes(':') && priceHistoryAllowed(offerId.split(':',1)[0]);
}
