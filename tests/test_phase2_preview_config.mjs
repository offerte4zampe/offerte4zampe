import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const read=path=>fs.readFileSync(new URL('../'+path,import.meta.url),'utf8');
const preview=JSON.parse(read('wrangler.phase2-preview.jsonc'));
const production=JSON.parse(read('wrangler.jsonc'));
const workflow=read('.github/workflows/phase2-isolated-preview.yml');

test('phase2 preview only includes asset build and JSON vars, without bound production resources',()=>{
 assert.deepEqual(Object.keys(preview).sort(),['name','main','compatibility_date','assets','build','workers_dev','preview_urls','routes','vars'].sort());
 assert.equal(preview.name,'zampachiara');assert.equal(preview.main,'worker/index.mjs');
 assert.deepEqual(preview.assets,production.assets);assert.deepEqual(preview.build,production.build);
 assert.deepEqual(preview.routes,[]);assert.equal(preview.workers_dev,false);assert.equal(preview.preview_urls,true);
 assert.deepEqual(preview.vars,{SHIPPING_RULES_SOURCE:'json',SHIPPING_SHADOW:'false'});
 for(const forbidden of ['durable_objects','migrations','triggers','analytics_engine_datasets','d1_databases','kv_namespaces','r2_buckets','services','secrets','keep_vars','env'])assert(!Object.hasOwn(preview,forbidden));
});
test('preview workflow is restricted to exact same-repository PR branch and read-only GitHub permissions',()=>{
 assert.match(workflow,/head\.repo\.full_name == github\.repository/);
 assert.match(workflow,/head\.ref == 'phase2\/shipping-metadata-preview-20261104'/);
 assert.match(workflow,/ref: \$\{\{ github\.event\.pull_request\.head\.sha \}\}/);
 assert.match(workflow,/persist-credentials: false/);
 assert.match(workflow,/permissions:\s*\n  contents: read/);
 assert(!/pull_request_target|workflow_dispatch|contents: write|id-token: write/.test(workflow));
 assert.match(workflow,/environment: cloudflare-staging/);
});
test('only the native preview upload step receives Cloudflare secrets after all checks',()=>{
 const steps=workflow.split(/\n      - /);
 const secretSteps=steps.filter(step=>step.includes('secrets.'));
 assert.equal(secretSteps.length,1);assert.match(secretSteps[0],/^name: Upload native preview only/);
 assert.match(secretSteps[0],/secrets\.CLOUDFLARE_API_TOKEN/);assert.match(secretSteps[0],/secrets\.CLOUDFLARE_ACCOUNT_ID/);
 assert.equal((workflow.match(/secrets\./g)||[]).length,2);
 const upload=workflow.indexOf('name: Upload native preview only');
 for(const command of ['wrangler deploy --dry-run','python -m unittest discover -s tests','node --test tests/test_*.mjs'])assert(workflow.indexOf(command)<upload);
 assert.match(workflow,/npm install --global wrangler@4\.154\.0/);
 assert.match(secretSteps[0],/wrangler preview --config wrangler\.phase2-preview\.jsonc --ignore-base-config --name "\$PREVIEW_NAME" --json/);
 assert.match(workflow,/PREVIEW_NAME: phase2-\$\{\{ github\.event\.pull_request\.number \}\}/);
 assert(!/wrangler (?:versions|secret|d1|kv|r2|delete|publish)\b/.test(workflow));
 for(const line of workflow.split('\n').filter(line=>line.includes('wrangler deploy')))assert(line.includes('--dry-run')&&line.includes('wrangler.phase2-preview.jsonc'));
});
