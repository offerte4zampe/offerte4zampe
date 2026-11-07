(function(root){'use strict';
const money=new Intl.NumberFormat('it-IT',{style:'currency',currency:'EUR'});
function name(value){
 let text=String(value||'').replace(/(\d)\s*gr\b/gi,'$1g').replace(/\bgr\b/gi,'g').replace(/\s+/g,' ').trim();
 const amount='\\d+(?:[.,]\\d+)?',unit='(?:kg|g|ml|l)';
 const repeated=new RegExp('('+amount+')\\s*('+unit+')\\b(?:\\s*[·|/]\\s*|\\s+)('+amount+')\\s*('+unit+')\\b','gi');
 for(let i=0;i<3;i++)text=text.replace(repeated,(all,a,u,b,v)=>Number(a.replace(',','.'))===Number(b.replace(',','.'))&&u.toLowerCase()===v.toLowerCase()?a+' '+u:all);
 return text.replace(/(\d+(?:[.,]\d+)?)\s*(kg|g|ml|l)\b/gi,(_,amount,unit)=>amount.replace('.',',')+' '+unit.toLowerCase());
}
function withoutFormat(text,format){
 const wanted=/^(\d+(?:[.,]\d+)?)\s*(kg|g|ml|l)$/i.exec(format);
 if(!wanted)return text;
 return text.replace(/(?<![\w.,])\d+(?:[.,]\d+)?\s*(?:kg|g|ml|l)\b/gi,(all,offset)=>{
  const value=/^(\d+(?:[.,]\d+)?)\s*(kg|g|ml|l)$/i.exec(all);
  // Preserve multipacks and alternative sizes rather than rewriting identity.
  if(/[x×/]\s*$/.test(text.slice(0,offset))||/^\s*[x×/]/.test(text.slice(offset+all.length)))return all;
  return Number(value[1].replace(',','.'))===Number(wanted[1].replace(',','.'))&&value[2].toLowerCase()===wanted[2].toLowerCase()?'':all;
 }).replace(/\s+/g,' ').replace(/[\s·|,:;—-]+$/,'').trim();
}
function title(value,brand='',format=''){
 let text=name(value),unit=name(format);
 if(/^(?:Unità di vendita|Formato da verificare)$/i.test(unit))unit='';
 if(brand&&!text.toLocaleLowerCase('it').includes(String(brand).toLocaleLowerCase('it')))text=brand+' '+text;
 // Preserve source taste, texture and size rather than enforce a character budget.
 const escaped=unit.replace(/[.*+?^${}()|[\]\\]/g,'\\$&').replace(/\s+/g,'\\s*');
 const hasFormat=unit&&new RegExp('(^|[^\\w.,])'+escaped+'(?![\\w])','i').test(text);
 return text+(unit&&!hasFormat?' · '+unit:'')+' | Prezzi e offerte';
}
function description(offers,shops){
 const rows=(offers||[]).filter(o=>o.available&&Number.isFinite(o.price)&&o.price>0);if(!rows.length)return 'Offerte recenti non disponibili. Verifica la disponibilità direttamente nel negozio.';
 const low=rows.reduce((a,b)=>a.price<=b.price?a:b),unit=Number.isFinite(low.unit_price)&&low.unit_price>0&&low.unit_price_unit?' ('+money.format(low.unit_price)+'/'+low.unit_price_unit+')':'';
 return (shops>=2?'Confronta '+shops+' negozi: da ':'Prezzo rilevato: ')+money.format(low.price)+unit+'. Spedizione da verificare nel negozio.';
}
const api={name,title,description};if(typeof module!=='undefined')module.exports=api;else root.O4ZProductMetadata=api;
})(typeof window!=='undefined'?window:null);
