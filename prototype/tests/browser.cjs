// Real browser -> local HTTP -> PostgreSQL acceptance. Credentials never logged.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const fs=require('fs'),path=require('path'),assert=require('assert');
const root=path.resolve(__dirname,'..');
const config=JSON.parse(fs.readFileSync(path.join(root,'.local/connection.json')));
const output=path.resolve(root,'../验证记录/browser');fs.mkdirSync(output,{recursive:true});
(async()=>{const browser=await chromium.launch({headless:true,...(process.env.PLAYWRIGHT_EXECUTABLE_PATH?{executablePath:process.env.PLAYWRIGHT_EXECUTABLE_PATH}:{})});const checks=[];const stamp=Date.now();const demoCaption='Final demo · Relational data in motion '+stamp;const collectionName='Final demo '+stamp;try{
const page=await browser.newPage({viewport:{width:1440,height:1000}});const errors=[];page.on('pageerror',e=>errors.push(String(e)));
await page.goto('http://127.0.0.1:5413');await page.screenshot({path:path.join(output,'01_login.png')});
await page.locator('[name=password]').fill(config.users['1'].password);await page.getByRole('button',{name:'Enter workspace'}).click();await page.locator('.card').first().waitFor({timeout:15000});checks.push('Database-authenticated browser login');
await page.screenshot({path:path.join(output,'02_feed.png'),fullPage:false});
await page.waitForFunction(()=>document.querySelector('video')?.readyState>=1);const media=await page.locator('video').first().evaluate(v=>({ready:v.readyState,error:v.error?.message||null}));assert(!media.error);checks.push('Bundled original demo media loads');
// Browser caller cannot substitute identity or write to another user's object.
const csrf=await page.evaluate(async()=> (await (await fetch('/api/session')).json()).csrf);
async function raw(action,payload,token=csrf){return page.evaluate(async({action,payload,token})=>{const r=await fetch('/api/action',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':token},body:JSON.stringify({action,payload})});return {status:r.status,body:await r.json()}},{action,payload,token})}
assert.equal((await raw('profile',{actor_id:2})).status,403);checks.push('Actor substitution rejected over HTTP');
assert.equal((await raw('hide',{video_id:2})).status,403);checks.push('Cross-owner mutation rejected over HTTP');
assert.equal((await raw('like',{video_id:4})).status,409);checks.push('Hidden-video interaction rejected over HTTP');
assert.equal((await raw('profile',{},'wrong-token')).status,403);checks.push('CSRF token enforced');
await page.getByRole('button',{name:'Publish a video',exact:false}).click();await page.locator('#publish-form').waitFor();await page.locator('#publish-form [name=caption]').fill(demoCaption);await page.locator('#publish-form button').click();await page.locator('.card h3').filter({hasText:demoCaption}).first().waitFor();checks.push('Publish form creates a database video');
const card=page.locator('.card').filter({hasText:demoCaption}).first();
const id=await card.locator('[data-action=comments]').getAttribute('data-id');
await card.locator('[data-action=comments]').click();await page.locator('#comment-form textarea').fill('This comment was posted through the verified prototype.');await page.locator('#comment-form button').click();await page.getByText('This comment was posted through the verified prototype.',{exact:true}).waitFor();checks.push('Comment form persists and re-reads a comment');
await page.screenshot({path:path.join(output,'03_comments.png')});await page.locator('dialog .close').click();
await card.locator('[data-action=like]').click();await page.locator('.card').filter({hasText:demoCaption}).first().locator('[data-action=unlike]').waitFor();checks.push('Like action persists and updates the visible state');
await page.getByRole('button',{name:'My collections'}).click();await page.getByRole('button',{name:'New collection'}).click();await page.locator('#new-collection-form [name=name]').fill(collectionName);await page.locator('#new-collection-form button').click();await page.locator('.collection').filter({hasText:collectionName}).first().waitFor();checks.push('Collection form persists a collection');
const collections=await raw('collections',{});const collection=collections.body.data.find(c=>c.name===collectionName);
const collected=await raw('collect',{collection_id:collection.collection_id,video_id:Number(id)});assert.equal(collected.status,200);checks.push('Collection item saved with allocated number');
await page.getByRole('button',{name:'My collections'}).click();await page.locator('.collection').filter({hasText:collectionName}).first().getByText(demoCaption,{exact:false}).waitFor();await page.screenshot({path:path.join(output,'04_collections.png'),fullPage:false});
await page.getByRole('button',{name:'SQL reports'}).click();await page.locator('#report-form select').selectOption('Q03');await page.locator('#report-form button').click();await page.locator('#report-output tbody tr').first().waitFor();checks.push('Report UI executes the live SELECT whitelist');await page.screenshot({path:path.join(output,'05_report.png')});
await page.setViewportSize({width:390,height:844});await page.getByRole('button',{name:'Explore'}).click();await page.locator('.card').first().waitFor();await page.screenshot({path:path.join(output,'06_mobile.png')});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));checks.push('390px layout has no horizontal overflow');
assert.deepEqual(errors,[]);checks.push('No browser JavaScript exceptions');
fs.writeFileSync(path.join(output,'browser_results.json'),JSON.stringify({passed:true,checks,created_video_id:Number(id),created_collection_id:collection.collection_id,retention:'New demonstration records retained; no pre-existing records deleted.'},null,2));console.log(JSON.stringify({passed:true,checks:checks.length,created_video_id:Number(id)}));
}finally{await browser.close()}})().catch(e=>{console.error(e);process.exit(1)});
