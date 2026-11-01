"""Read only tool schemas and positive target argument keys. No tool execution."""
from pathlib import Path
import collections
import hashlib
import importlib.util
import json
import re
import sys

sys.dont_write_bytecode=True
ROOT=Path('D:/skillloop')
ACTIVE=ROOT/'output/20261101_wrd_increment57/active_dataset57/native_bfc_checkpoint01'
PRODUCER=ROOT/'output/20261101_wrd_increment57/collection57/bfc_producer/api_audit'
OUT=Path(__file__).resolve().parent
FOCUS={'exec','read','write','edit','process','sessions_spawn','subagents','ls'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(n,x):(OUT/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def schemas(tools):
 result={}
 for item in tools or []:
  f=item.get('function',item);name=f.get('name');schema=f.get('parameters',f.get('input_schema'))
  if name and isinstance(schema,dict):result[name]=schema
 return result
def semantic(x):
 if isinstance(x,dict):return {k:semantic(v) for k,v in sorted(x.items()) if k not in {'description','title','examples','$comment'}}
 if isinstance(x,list):return [semantic(v) for v in x]
 return x
def key_signature(s):
 return {'required':sorted(s.get('required',[])),'properties':sorted(s.get('properties',{})),
  'property_semantics':{k:semantic(v) for k,v in sorted(s.get('properties',{}).items())}}
def issues(value,schema,path='$'):
 errors=[];kind=schema.get('type');types=kind if isinstance(kind,list) else [kind] if kind else []
 valid={'object':isinstance(value,dict),'array':isinstance(value,list),'string':isinstance(value,str),
        'boolean':isinstance(value,bool),'integer':isinstance(value,int) and not isinstance(value,bool),
        'number':isinstance(value,(int,float)) and not isinstance(value,bool),'null':value is None}
 if types and not any(valid.get(t,True) for t in types):return [{'kind':'TYPE','path':path,'expected':kind,'observed_type':type(value).__name__}]
 if 'enum' in schema and value not in schema['enum']:errors.append({'kind':'ENUM','path':path,'expected':schema['enum'],'observed_scalar':value if isinstance(value,(int,float,bool)) else str(value)[:80]})
 if 'const' in schema and value!=schema['const']:errors.append({'kind':'CONST','path':path,'expected':schema['const']})
 if isinstance(value,dict):
  for k in schema.get('required',[]):
   if k not in value:errors.append({'kind':'MISSING_REQUIRED','path':path+'.'+k})
  props=schema.get('properties',{});patterns=schema.get('patternProperties',{})
  for k,v in value.items():
   if k in props:errors+=issues(v,props[k],path+'.'+k)
   elif any(re.match(p,k) for p in patterns):
    for pattern,sub in patterns.items():
     if re.match(pattern,k):errors+=issues(v,sub,path+'.'+k)
   elif props and k not in props:errors.append({'kind':'UNDECLARED_PARAMETER_KEY','path':path+'.'+k,'additionalProperties':schema.get('additionalProperties','UNSPECIFIED')})
 if isinstance(value,list) and 'items' in schema:
  for i,v in enumerate(value):errors+=issues(v,schema['items'],path+f'[{i}]')
 if isinstance(value,(int,float)) and not isinstance(value,bool):
  for limit,op in [('minimum',lambda x,y:x<y),('maximum',lambda x,y:x>y)]:
   if limit in schema and op(value,schema[limit]):errors.append({'kind':limit.upper(),'path':path,'expected':schema[limit],'observed_scalar':value})
 return errors
def argument(value):
 if isinstance(value,str):
  try:return json.loads(value)
  except (ValueError,TypeError):return None
 return value
def explicit_calls(message):
 result=[]
 for item in message.get('tool_calls',[]) or []:
  f=item.get('function',item);name=f.get('name');args=argument(f.get('arguments',{}))
  if name:result.append({'name':name,'arguments':args,'kind':'assistant_tool_call'})
 return result
def intents(value,pointer='$'):
 result=[]
 if isinstance(value,dict):
  name=value.get('tool_name',value.get('tool',value.get('name')))
  args=value.get('arguments',value.get('params',value.get('input')))
  if isinstance(name,str) and args is not None:
   result.append({'name':name,'arguments':argument(args),'kind':'positive_JSON_tool_intent','pointer':pointer})
  for k,v in value.items():result+=intents(v,pointer+'.'+k)
 elif isinstance(value,list):
  for i,v in enumerate(value):result+=intents(v,pointer+f'[{i}]')
 return result

actual_versions=collections.defaultdict(dict);actual_source=[]
for request in sorted(PRODUCER.glob('*/request.raw.json')):
 d=load(request);actual_source.append({'path':request.relative_to(ROOT).as_posix(),'sha256':sha(request)})
 for name,schema in schemas(d.get('tools')).items():
  if name in FOCUS:
   body=json.dumps(key_signature(schema),sort_keys=True,ensure_ascii=False)
   actual_versions[name][hashlib.sha256(body.encode()).hexdigest()]=schema
assert len(actual_source)==33 and all(len(actual_versions[n])==1 for n in FOCUS)
actual={n:next(iter(v.values())) for n,v in actual_versions.items()}
spec=importlib.util.spec_from_file_location('reviewed_ABI_active57',ACTIVE/'tooling/active_loader57.py')
loader=importlib.util.module_from_spec(spec);spec.loader.exec_module(loader)
profiles={};violations=[];declaration_risks=[];all_calls=[];intent_keys=collections.Counter()
for profile in ['budget_projection','full_native53']:
 counts=collections.Counter();decl=collections.Counter()
 for pool,source,entry,row in loader.iter_records(ACTIVE,ROOT/'output/wrd10root01',ROOT/'output/wrd11publicroot01',profile=profile):
  counts['rows']+=1;declared=schemas(row.get('tools'))
  for name,s in declared.items():
   if name not in FOCUS:continue
   obsolete=sorted(set(s.get('properties',{}))-set(actual[name].get('properties',{})))
   if obsolete:
    decl[name]+=1;declaration_risks.append({'profile':profile,'id':row['id'],'pool':pool,'tool':name,'obsolete_declared_keys':obsolete,
      'current_properties':sorted(actual[name].get('properties',{})),'declaration_is_input_zero_loss_not_itself_positive_action':True})
  for target in row.get('targets',[]):
   mi=target.get('message_index');owned=target.get('owned_supervision_spans',[])
   components=collections.Counter()
   for lo,hi,c,w in owned:components[c]+=hi-lo
   if not isinstance(mi,int) or mi>=len(row.get('messages',[])):continue
   msg=row['messages'][mi];calls=explicit_calls(msg) if components.get('A',0)>0 else []
   content=msg.get('content')
   if isinstance(content,str) and (components.get('A',0)>0 or components.get('D',0)>0):
    try:parsed=json.loads(content)
    except (ValueError,TypeError):parsed=None
    if parsed is not None:calls+=intents(parsed)
   for call in calls:
    name=call['name'];counts['all_positive_calls_or_intents']+=1
    if pool=='synthetic':counts['aux_positive_calls_or_intents']+=1
    if name not in FOCUS:continue
    counts['focused_positive_calls_or_intents']+=1
    if pool=='synthetic':counts['aux_focused_positive_calls_or_intents']+=1
    args=call['arguments'];current_errors=issues(args,actual[name]);declared_errors=issues(args,declared[name]) if name in declared else [{'kind':'TOOL_NOT_DECLARED_IN_ROW'}]
    record={'profile':profile,'id':row['id'],'pool':pool,'target_message_index':mi,'tool':name,'kind':call['kind'],
     'argument_keys':sorted(args) if isinstance(args,dict) else None,'positive_components':dict(components),
     'current_schema_violations':current_errors,'row_declared_schema_violations':declared_errors,
     'current_required':actual[name].get('required',[]),'current_properties':sorted(actual[name].get('properties',{})),
     'row_declared_required':declared.get(name,{}).get('required',[]),'row_declared_properties':sorted(declared.get(name,{}).get('properties',{})),
     'field_positive_mask_requires_confirmation_if_partial_A':True}
    all_calls.append(record)
    if pool=='synthetic' and isinstance(args,dict):
     for k in args:intent_keys[(name,k)]+=1
    if current_errors or declared_errors:violations.append(record)
 profiles[profile]={'counts':dict(counts),'rows_with_obsolete_declared_keys_by_tool':dict(decl)}
summary={'status':'READ_ONLY_ABI_KEY_COMPARISON_COMPLETE','current_actual_catalog_requests':len(actual_source),
 'current_focus_schema_semantic_versions':{n:len(v) for n,v in actual_versions.items()},'profiles':profiles,
 'potential_target_violation_records_across_profiles':len(violations),'declaration_risk_records_across_profiles':len(declaration_risks),
 'auxiliary_positive_focus_argument_key_counts_across_profiles':{f'{n}.{k}':v for (n,k),v in intent_keys.items()},
 'description_and_property_order_changes_not_treated_as_conflicts':True,'data_modified':False,'models_or_business_tools_run':False}
save('CURRENT_ABI_SCHEMAS57.json',{'source_requests':actual_source,'semantic_required_properties_enum':{n:key_signature(s) for n,s in actual.items()}})
save('POSITIVE_ARGUMENT_CHECKS57.json',{'summary':summary,'potential_violations':violations,'declaration_risks':declaration_risks,'all_focus_calls':all_calls})
save('ABI_SUMMARY57.json',summary)
print(json.dumps(summary,ensure_ascii=True))
