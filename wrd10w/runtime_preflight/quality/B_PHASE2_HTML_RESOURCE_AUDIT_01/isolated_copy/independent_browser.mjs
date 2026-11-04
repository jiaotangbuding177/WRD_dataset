import {createRequire} from 'node:module';
import fs from 'node:fs';
const require=createRequire(import.meta.url);const {chromium}=require('playwright');
const root='/workspace/independent_results';const results=[];
const browser=await chromium.launch({executablePath:'/usr/bin/chromium',args:['--no-sandbox']});
try{
 for(const name of ['maker.html','ball.html','resume_disabled_canary.html']){
  const page=await browser.newPage({viewport:{width:1100,height:760}});let errors=[];page.on('pageerror',e=>errors.push(String(e)));
  await page.goto('file://'+root+'/'+name);const time=()=>page.evaluate(()=>{for(const r of document.querySelectorAll('.wrd-hud-row'))if(r.children[0]?.textContent.includes('时间'))return parseFloat(r.children[1].textContent);return null;});
  await page.waitForTimeout(300);const a=await time();await page.waitForTimeout(450);const b=await time();
  await page.click('.wrd-btn-toggle');await page.waitForTimeout(100);const c=await time();await page.waitForTimeout(400);const d=await time();
  await page.click('.wrd-btn-toggle');await page.waitForTimeout(100);const e=await time();await page.waitForTimeout(450);const f=await time();
  await page.click('.wrd-btn-reset');await page.waitForTimeout(80);const g=await time();await page.waitForTimeout(450);const h=await time();
  results.push({name,errors,actual_times:{a,b,c,d,e,f,g,h},initial_time_advances:b>a,paused_time_frozen:c===d,resumed_time_actually_advances:f>e,reset_time_near_zero:g<0.4,reset_then_time_advances:h>g,canvas_visible:await page.locator('canvas').isVisible()});
  await page.screenshot({path:root+'/'+name+'.independent.png',fullPage:true});await page.close();
 }
}finally{await browser.close();}
fs.writeFileSync(root+'/INDEPENDENT_BROWSER.json',JSON.stringify(results,null,2));console.log(JSON.stringify(results));
