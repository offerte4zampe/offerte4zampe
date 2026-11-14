import test from 'node:test';
import assert from 'node:assert/strict';
import {verifyRedirectResponse} from './check_matching_contract.mjs';
const url='https://merchant.example/a?x=1&b=%2F';
const response=(status=302,location=url,robots='noindex, nofollow')=>new Response(null,{status,headers:{Location:location,'X-Robots-Tag':robots}});
test('matching contract accepts byte-exact affiliate redirect',()=>verifyRedirectResponse(response(),url));
test('matching contract rejects changed status, Location bytes, missing or weak robots',()=>{
 for(const r of [response(301),response(307),response(302,url.replace('%2F','%2f')),response(302,url,'index'),response(302,url,'noindex'),new Response(null,{status:302,headers:{Location:url}})])assert.throws(()=>verifyRedirectResponse(r,url));
});
