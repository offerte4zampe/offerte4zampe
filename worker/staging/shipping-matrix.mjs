import trade from '../../site/assets/trade.js';
import {readShippingRows} from '../shipping-source.mjs';
export function matrix(source){
 const cases=[],now=Math.max(...Object.values(source.merchants).map(r=>Date.parse(r.checked_at||source.checked_at)))+12*3600000;
 for(const [id,r] of Object.entries(source.merchants)){
  const threshold=r.free_from??r.free_above??69;
  for(const price of [threshold-.01,threshold,threshold+.01,1,100])for(const weight of [undefined,1,35,35.001])for(const quantity of [1,2,3])for(const territory of ['standard','special'])cases.push({id,price,weight,quantity,territory,now});
  const until=Date.parse(r.verified_until);for(const time of [until,until+1])cases.push({id,price:20,weight:1,quantity:1,territory:'standard',now:time});
 }
 return cases;
}
export async function verifyMatrix(db,source){
 const cache=new Map(),differences=[];let rowsRead=0,queries=0;
 for(const c of matrix(source)){
  const key=c.id+':'+c.now;let data=cache.get(key);
  if(!data){data=await readShippingRows(db,[c.id],c.now);cache.set(key,data);rowsRead+=data.meta.rows_read;queries+=data.meta.queries;}
  const o={merchant_id:c.id,price:c.price,shipping_weight_kg:c.weight,checked_at:new Date(c.now).toISOString()};
  const left=trade.shipping(o,source,c.quantity,c.territory,c.now),right=trade.shipping(o,trade.shippingRulesFromRows(data.rows,c.now),c.quantity,c.territory,c.now);
  if(left.fee!==right.fee||left.total!==right.total||left.subtotal!==right.subtotal||left.reason!==right.reason)differences.push({shop_id:c.id,price:c.price,quantity:c.quantity,territory:c.territory,weight:c.weight??null,time:new Date(c.now).toISOString(),json_total:left.total??null,d1_total:right.total??null});
 }
 return {cases:matrix(source).length,differences,meta:{rows_read:rowsRead,queries},clock:'Historical fixture timestamps derived from the unchanged JSON verification dates; not invented current observations'};
}
