(async()=>{
let chromium;
try{chromium=require('playwright');}catch(e){chromium=require('/usr/lib/node_modules/playwright');}
const b=await chromium.launch({executablePath:'/usr/bin/chromium',args:['--no-sandbox']});
const pg=await b.newPage({viewport:{width:1024,height:660}});
const errs=[];
pg.on('pageerror',e=>errs.push('PAGEERROR: '+e.message));
pg.on('console',m=>{if(m.type()==='error')errs.push('CONSOLE: '+m.text());});
await pg.goto('file:///workspace/outputs/contra.html');
await pg.waitForTimeout(700);
await pg.screenshot({path:'/workspace/tmp/shot_title.png'});
const st=await pg.evaluate(()=>({state:window.state===undefined?'n/a':'has', canvas:!!document.getElementById('game')}));
console.log('TITLE loaded:',JSON.stringify(st));
// start game
await pg.keyboard.press('Enter');
await pg.waitForTimeout(400);
// gameplay: move right, shoot, jump
await pg.keyboard.down('ArrowRight');
for(let i=0;i<8;i++){await pg.keyboard.press('j');await pg.waitForTimeout(250);}
await pg.keyboard.press('k');
await pg.waitForTimeout(700);
await pg.keyboard.up('ArrowRight');
await pg.waitForTimeout(300);
await pg.screenshot({path:'/workspace/tmp/shot_play.png'});
const px1=await pg.evaluate(()=>{const c=document.getElementById('game');const x=c.getContext('2d');const d=x.getImageData(0,0,c.width,c.height).data;let s=0,n=0;for(let i=0;i<d.length;i+=997){s+=d[i]+d[i+1]+d[i+2];n++;}return s/n;});
console.log('PIXEL_AVG_PLAY:',px1.toFixed(1));
// longer play to catch delayed errors
await pg.keyboard.down('ArrowRight');
for(let i=0;i<12;i++){await pg.keyboard.press('j');await pg.waitForTimeout(220);}
await pg.keyboard.up('ArrowRight');
await pg.waitForTimeout(400);
await pg.screenshot({path:'/workspace/tmp/shot_play2.png'});
const px2=await pg.evaluate(()=>{const c=document.getElementById('game');const x=c.getContext('2d');const d=x.getImageData(0,0,c.width,c.height).data;let s=0,n=0;for(let i=0;i<d.length;i+=997){s+=d[i]+d[i+1]+d[i+2];n++;}return s/n;});
console.log('PIXEL_AVG_PLAY2:',px2.toFixed(1));
console.log('ERRORS:',errs.length?errs.join(' | '):'none');
await b.close();
})().catch(e=>{console.error('TESTFAIL',e);process.exit(1);});
