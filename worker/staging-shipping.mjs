import source from '../site/data/shipping-rules.json' with {type:'json'};
import {verifyMatrix} from './staging/shipping-matrix.mjs';
import {RULE_QUERY,readShippingRows} from './shipping-source.mjs';
function usage(results){return results.reduce((n,r)=>({rows_read:n.rows_read+(r.meta?.rows_read||0),rows_written:n.rows_written+(r.meta?.rows_written||0)}),{rows_read:0,rows_written:0});}
export async function seed(db,data){
 if(data.shops?.length!==6||data.rules?.length!==6||data.shops.some(s=>!Object.hasOwn(source.merchants,s.id)))throw Error('Unexpected seed');
 const statements=[];
 for(const s of data.shops)statements.push(db.prepare('INSERT INTO shop(id,name) VALUES(?1,?2) ON CONFLICT(id) DO UPDATE SET name=excluded.name').bind(s.id,s.name));
 const keys=['shop_id','zone','std_cents','free_from_cents','threshold_mode','max_weight_g','over_weight_note','status','source_url','notes','verified_at','verified_until','valid_from','valid_to'];
 const sql='INSERT INTO shipping_rule('+keys.join(',')+') VALUES('+keys.map((_,i)=>'?'+(i+1)).join(',')+') ON CONFLICT(shop_id,zone,valid_from) DO UPDATE SET '+keys.filter(k=>!['shop_id','zone','valid_from'].includes(k)).map(k=>k+'=excluded.'+k).join(',');
 for(const r of data.rules)statements.push(db.prepare(sql).bind(...keys.map(k=>r[k]??null)));
 const results=await db.batch(statements);if(results.some(r=>!r.success))throw Error('Seed failed');
 const counts=await db.prepare('SELECT (SELECT count(*) FROM shop) AS shops,(SELECT count(*) FROM shipping_rule) AS rules').first();
 return {counts,meta:usage(results),statements:results.length};
}
export async function capabilities(db){
 const name='probe_'+crypto.randomUUID().replaceAll('-','');let generated=false,check=false,trigger=false,trigram=false;
 const meta=[];
 try{
  meta.push(await db.prepare(`CREATE TABLE ${name}(id INTEGER PRIMARY KEY,price_cents INTEGER CHECK(price_cents>0),quantity INTEGER CHECK(quantity>0),unit_price REAL GENERATED ALWAYS AS(price_cents/100.0/(quantity/1000.0)) VIRTUAL,touched INTEGER DEFAULT 0)`).run());
  meta.push(await db.prepare(`CREATE INDEX ${name}_unit ON ${name}(unit_price)`).run());
  meta.push(await db.prepare(`CREATE TRIGGER ${name}_update AFTER UPDATE OF price_cents ON ${name} BEGIN UPDATE ${name} SET touched=1 WHERE id=new.id; END`).run());
  await db.prepare(`INSERT INTO ${name}(id,price_cents,quantity) VALUES(1,1500,1500)`).run();
  try{await db.prepare(`INSERT INTO ${name}(price_cents,quantity) VALUES(-1,1500)`).run();}catch{check=true;}
  await db.prepare(`UPDATE ${name} SET price_cents=1800 WHERE id=1`).run();
  const row=await db.prepare(`SELECT unit_price,touched FROM ${name} WHERE id=1`).first();generated=row.unit_price===12;trigger=row.touched===1;
  try{
   await db.prepare(`CREATE VIRTUAL TABLE ${name}_fts USING fts5(title,tokenize='trigram')`).run();
   await db.prepare(`INSERT INTO ${name}_fts(title) VALUES('Fortiflora cani')`).run();
   const found=await db.prepare(`SELECT count(*) AS n FROM ${name}_fts WHERE ${name}_fts MATCH 'forti'`).first();trigram=found.n===1;
  }catch{trigram=false;}
  let sqlite;try{sqlite=await db.prepare('SELECT sqlite_version() AS version').first();}catch{sqlite={version:null,available_through_binding:false};}
  return {generated_columns_and_index:generated,check_constraints:check,triggers:trigger,fts5_trigram:trigram,sqlite};
 }finally{await db.prepare(`DROP TABLE IF EXISTS ${name}_fts`).run();await db.prepare(`DROP TABLE IF EXISTS ${name}`).run();}
}
export default {async fetch(request,env){
 if(!env.STAGING_TOKEN||request.headers.get('Authorization')!=='Bearer '+env.STAGING_TOKEN)return new Response(null,{status:404});
 if(request.method!=='POST')return new Response(null,{status:405});
 const path=new URL(request.url).pathname,db=env.SHIPPING_DB_STAGING;
 try{
  let result;
  if(path==='/seed'){
   const text=await request.text();if(text.length>65536)return new Response(null,{status:413});result=await seed(db,JSON.parse(text));
  }else if(path==='/verify'){
   const matrix=await verifyMatrix(db,source),now=Math.max(...Object.values(source.merchants).map(r=>Date.parse(r.checked_at||source.checked_at)))+12*3600000;
   const productRead=await readShippingRows(db,Object.keys(source.merchants),now);
   const plans=await db.batch(Object.keys(source.merchants).map(id=>db.prepare('EXPLAIN QUERY PLAN '+RULE_QUERY).bind(id,'IT',new Date(now).toISOString())));
   result={matrix,product_request:{shops:6,meta:productRead.meta},plans:plans.flatMap(r=>r.results),capabilities:await capabilities(db)};
  }else return new Response(null,{status:404});
  return Response.json({runtime:env.STAGING_LOCATION||'local',...result},{headers:{'Cache-Control':'no-store'}});
 }catch(error){return Response.json({error:String(error.message).slice(0,300)},{status:500,headers:{'Cache-Control':'no-store'}});}
}};
