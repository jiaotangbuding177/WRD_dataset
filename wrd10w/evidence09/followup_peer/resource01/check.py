from pathlib import Path
import ast, hashlib, json, re, subprocess, types, urllib.parse
f=json.loads(Path('/workspace/fixtures.json').read_text())
c=f['commands']['10cb6178ac2a09e2cfbbcf23']
assert "<< 'EOF'\n" in c and '\nEOF\n' in c
source=c.split("<< 'EOF'\n",1)[1].split('\nEOF\n',1)[0]
tree=ast.parse(source)
func=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='search')
regex=next(n.args[0].value for n in ast.walk(func)if isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)and n.func.attr=='search')
video=lambda i,title:{'videoRenderer':{'videoId':i,'title':{'runs':[{'text':title}]},'ownerText':{'runs':[{'text':'OpenAI'}]},'lengthText':{'simpleText':'1:20'},'viewCountText':{'simpleText':'10 views'},'publishedTimeText':{'simpleText':'1 day ago'}}}
obj={'contents':[video('realid1','First'),{'nested':[video('realid1','Duplicate'),video('realid2','Second')]}]}
html='<html><script>var ytInitialData = '+json.dumps(obj)+';</script></html>'
assert json.loads(re.search(regex,html).group(1))==obj
class Request:
 def __init__(self,url,headers):self.url=url;self.headers=headers
class Body:
 def read(self):return html.encode()
requests=[]
def urlopen(req,timeout):
 requests.append({'url':req.url,'timeout':timeout});return Body()
fakeurllib=types.SimpleNamespace(parse=urllib.parse,request=types.SimpleNamespace(Request=Request,urlopen=urlopen))
env={'json':json,'re':re,'urllib':fakeurllib}
exec(compile(ast.Module(body=[func],type_ignores=[]),'<exact-original-function>','exec'),env)
got=env['search']('OpenAI introducing GPT-5')
assert [v['id']for v in got]==['realid1','realid2']
assert got[0]=={'id':'realid1','title':'First','channel':'OpenAI','duration':'1:20','views':'10 views','published':'1 day ago'}
assert len(requests)==1 and requests[0]['timeout']==25
# Different page syntax is explicitly unsupported; this is not a robust universal extractor.
assert re.search(regex,'<script>window["ytInitialData"] = '+json.dumps(obj)+';</script>')is None
# Execute only reviewed screenshot filename expansion, not the original Chromium command.
shell='for i in 1 2 3; do printf "%s\\n" /workspace/outputs/图${i}_$( [ $i = 1 ] && echo 封面_AI当CEO || ( [ $i = 2 ] && echo 白名单漏洞 || echo 三层防御 ) ).png; done'
p=subprocess.run(['/bin/bash','-c',shell],capture_output=True,text=True,check=True)
names=p.stdout.splitlines();assert names==['/workspace/outputs/图1_封面_AI当CEO.png','/workspace/outputs/图2_白名单漏洞.png','/workspace/outputs/图3_三层防御.png']
after=''.join(x.get('text','')for x in f['native_after_screenshot']['content'])
assert all(Path(n).name in after for n in names)
shots=json.loads(f['storyboard'])['shots']
assert len(shots)==8 and [x['id']for x in shots]==list(range(1,9))
assert [x['dur']for x in shots[:7]]==[5,10,5,15,10,10,5]
assert sum(x['dur']for x in shots[:7])==60
assert all(x['narration']in f['storyboard_before_text']for x in shots)
assert sum(len(x['images'])for x in shots)==12
result={'status':'PASS_BOUNDED_PURE_RESOURCE_FIXTURES','exact_regex_source_sha256':hashlib.sha256(source.encode()).hexdigest(),
 'regex_matches_exact_supported_var_assignment':True,'ast_selected_original_function_executed_with_fake_HTTP':True,
 'metadata_extracted_and_deduplicated':True,'alternate_assignment_unsupported_explicit':True,
 'original_historical_feedback_contains_nonempty_metadata':bool(f['native_after_regex'].get('content')),
 'screenshot_filenames_exact_native_match':True,'screenshot_names':names,
 'storyboard_shots':len(shots),'first7_duration_sum_seconds':60,'images':12,'narrations_exact_source_matches':True,
 'live_network':False,'business_Agent':False,'weights_loaded':False,'training_started':False,
 'not_claimed':['all_YouTube_pages_supported','videos_visually_qualified','screenshot_visual_content_pass','whole_WRD_or_KEEP']}
Path('/workspace/RESULT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':result['status'],'checks':8}))
