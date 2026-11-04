"""Admit one bounded mathematical program; preserve checkpoint05 bytes."""
from pathlib import Path
from copy import deepcopy
from collections import Counter,defaultdict
import gzip,hashlib,json,shutil,math,re
ROOT=Path(__file__).resolve().parents[3]
DATA=ROOT/'output/20261027_wrd_main_v10'
MATH=ROOT/'output/20261029_wrd_ewi_probe_recovery'
PEER=ROOT/'output/20261029_wrd_ewi_probe_peer_01/PEER.json'
WORK=ROOT/'output/20261029_wrd_delivery06'
PLAN=ROOT/'research/plans/20261027_wrd_main_v10'
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def rows(p):
 with gzip.open(p,'rt',encoding='utf-8')as f:
  for l in f:
   if l.strip():yield json.loads(l)

def main():
 WORK.mkdir(exist_ok=False)
 peer=load(PEER);assert peer['status']=='PASS_SCOPED_MATHEMATICAL_CONSTRUCTION_PENDING_ROOT'
 base=load(DATA/'TRAINING_MANIFEST.json');assert base['actual_counts']['targets']==529
 h=DATA/'manifest_history/pre_delta06_529_20261029';h.mkdir(exist_ok=False)
 for n in ['TRAINING_MANIFEST.json','ACTUAL_DATA_STATISTICS.json']:(h/n).write_bytes((DATA/n).read_bytes())
 portable=load(MATH/'PORTABLE_SELECTION.json')
 for r in portable['all_actual_files']:
  p=MATH/r['path'];assert p.stat().st_size==r['bytes'] and sha(p)==r['sha256']
 raw=MATH/portable['profiles']['core7']['compiled']['path'];original=list(rows(raw))[0];r=deepcopy(original)
 structural={'messages','tools','input_ids','supervision_spans','targets','total_tokens','supervised_tokens','supervised_tokens_by_component','input_ids_sha256_u32le','supervision_spans_sha256','rendered_sha256','assistant_generation_spans','second_tokenizer_independently_called','tokenizer_pair_proof','label_definition','label_ignore_index','binary_arrays'}
 meta={k:deepcopy(v)for k,v in r.items()if k not in structural}
 meta.update(training_admitted=True,source_admission='ADMIT',root_main_admission=False,requires_external_root_admission=True,
             original226=False,holdout12=False,protected_sources_visible_prefix=False,
             owner_id=meta['target_owner']['canonical_original_action_owner_id'],supervision_message_indices=[2])
 r['original_record_metadata']=meta;r['schema_version']='wrd-verified-main-v10'
 for k in structural:
  if k in original:assert r[k]==original[k]
 bank='compiled/ewi_math_resource_construction_01';dest=DATA/bank;dest.mkdir(exist_ok=False)
 name='ewi_math_resource_construction_01.train.16k.jsonl.gz'
 with gzip.open(dest/name,'wt',encoding='utf-8',newline='\n')as f:f.write(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n')
 with gzip.open(dest/'held.jsonl.gz','wt',encoding='utf-8'):pass
 (dest/'CAUSAL_TEMPLATE.json').write_bytes((MATH/'native_construction_01/CAUSAL_TEMPLATE.json').read_bytes())
 counts={'sequences':1,'targets':1,'input_tokens':3350,'supervised_tokens':930,'16k_sequences':1,'train_sequences':1,'train_supervised_tokens':930,'component_A':930}
 files=[{'path':name,'bytes':(dest/name).stat().st_size,'sha256':sha(dest/name)}]
 save(dest/'COMPILATION_REPORT.json',{'schema_version':'wrd-main-v10-compiled-bank-v06','counts':counts,'banks':{r['bank']:counts},'files':files,
  'held_file':{'path':'held.jsonl.gz','bytes':(dest/'held.jsonl.gz').stat().st_size,'sha256':sha(dest/'held.jsonl.gz')},
  'immutable_inputs':[{'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}for p in [raw,PEER,MATH/'PORTABLE_SELECTION.json']],
  'messages_target_arrays_spans_weights_unchanged':True,'training_started':False,'script_sha256':sha(__file__)})
 proof={'status':'ADMIT_SCOPED_BOUNDED_MATH_COMPLETE_RESOURCE_NEW_ACTION_ONLY','record_ids':[r['id']],
  'compilation_report_sha256':sha(dest/'COMPILATION_REPORT.json'),'independent_peer_sha256':sha(PEER),
  'root_semantic_review':'Read entire ordinary task, complete module, field scope and peer, checked both original function identities, CLI dispatch, bounded arithmetic assumptions and actual finite QA. Not financial/accounting/legal policy or qualified skill utility.',
  'new_action_projection_tokens':930,'original_R_repeated_tokens':0,'original_R_of_same_response_remains_in_existing26_only':True,
  'R_and_A_owners_are_nonoverlapping_components_not_two_independent_teacher_tasks':True,
  'actual_native_tool_dispatch':False,'finite_model_only':peer['validity_scope'],'training_started':False}
 save(dest/'ROOT_SEMANTIC_ADMISSION.json',proof)
 m=deepcopy(base);m['actual_train_files']+=[{**f,'path':bank+'/'+f['path']}for f in files]
 m['active_compilation_reports'].append({'path':bank+'/COMPILATION_REPORT.json','sha256':sha(dest/'COMPILATION_REPORT.json')})
 m['external_root_admission_receipts'].append({'path':bank+'/ROOT_SEMANTIC_ADMISSION.json','sha256':sha(dest/'ROOT_SEMANTIC_ADMISSION.json'),'compiled_bank':bank,'scope':'bounded_mathematics_complete_code_not_financial_or_skill_gold'})
 allrows=[row for f in m['actual_train_files']for row in rows(DATA/f['path'])]
 total=Counter();banks=defaultdict(Counter);stages=defaultdict(Counter)
 for row in allrows:
  for c in [total,banks[row['bank']],stages[row['stage']]]:
   c.update(sequences=1,targets=len(row['original_record_metadata']['supervision_message_indices']),input_tokens=row['total_tokens'],supervised_tokens=row['supervised_tokens'],le16k_sequences=int(row['total_tokens']<=16384),le32k_sequences=int(row['total_tokens']<=32768))
   for k,v in row['supervised_tokens_by_component'].items():c['component_'+k]+=v
 m.update(design_revision='5.0.44',change_id='ALG-20261029-02',actual_counts=dict(total),by_bank={k:dict(v)for k,v in banks.items()},by_stage={k:dict(v)for k,v in stages.items()},
          new_authored_projected_action_owners=11,script_sha256=sha(__file__),training_started=False)
 m['supervision_origin_tokens']['new_authored_native_action_projection_A_tokens']+=930
 m['component_ownership_may_pair_nonoverlapping_original_R_with_new_authored_A_without_repeating_R']=True
 assert total['targets']==530 and total['supervised_tokens']==146999
 save(DATA/'TRAINING_MANIFEST.json',m)
 save(DATA/'ACTUAL_DATA_STATISTICS.json',{k:m[k]for k in ['status','actual_counts','by_stage','by_bank','supervision_origin_tokens','distinct_source_ids','source_connected_components_across_banks','missing_main_stages','full_WRD_main_training_ready','training_started']})
 # Extend exactly the old one-owner exposure sequence, no old bank repetition.
 old=load(ROOT/'output/20261029_wrd_delivery05/OWNER_EXPOSURE_SCHEDULE.json')
 source_by_id={row['id']:set(row['source_ids'])for row in allrows if row['id']!=r['id']}
 shared_components={x['joined_component']for x in old['schedule']if set(r['source_ids'])&source_by_id[x['id']]}
 assert len(shared_components)==1
 shared_component=next(iter(shared_components))
 grouped=defaultdict(list)
 for x in old['schedule']:grouped[(x['phase'],x['pass'])].append(x)
 schedule=[];update=0
 for phase,epoch,acc in [('A_contract',1,16),('process',1,4),('process',2,4),('process',3,4)]:
  seq=grouped[(phase,epoch)]
  if phase=='process':seq=seq+[{'id':r['id'],'owner':meta['owner_id'],'joined_component':shared_component,'bank':r['bank'],'tokens':3350,'supervised_tokens':930,'weighted_labels':232.5}]
  for i,x in enumerate(seq):schedule.append({**x,'phase':phase,'pass':epoch,'optimizer_update':update+i//acc+1,'microbatch':i%acc+1})
  update+=math.ceil(len(seq)/acc)
 denominators=defaultdict(Counter)
 for x in schedule:denominators[x['optimizer_update']].update(sequences=1,tokens=x['tokens'],valid_labels=x['supervised_tokens'])
 save(WORK/'OWNER_EXPOSURE_SCHEDULE.json',{'status':'PROPOSED_NOT_RUN','is_launch_configuration':False,'manifest_sha256':sha(DATA/'TRAINING_MANIFEST.json'),
  'primary_stop_after_update':52,'additional_passes_require_dev_evidence':True,'schedule':schedule,'per_update_valid_label_denominators':dict(denominators),'training_started':False})
 inv=load(ROOT/'output/20261029_wrd_delivery05/CURRENT_DATA_AND_EXPOSURE.json');inv['design_revision']='5.0.44'
 for key in ['process','all']:
  v=inv['inventory'][key];v['targets']+=1;v['input_tokens']+=3350;v['supervised_tokens']+=930;v['weighted_label_mass']+=232.5;v['le16K']+=1;v['le32K']+=1
 inv['one_extra_A_only_target_not_extra_independent_original_source_or_response']=True
 save(WORK/'CURRENT_DATA_AND_EXPOSURE.json',inv)
 # Snapshot design and plan before current non-executing data amendment.
 hist=ROOT/'research/designs/history/5.0.43/delta06_20261029';hist.mkdir(parents=True,exist_ok=False)
 note='''本轮5.0.44／ALG-20261029-02（2026-10-29，仅数据增量）：05已按75064b0实际Git上传，7250成员／189578320B认证实体及439普通＋3LFS冷核通过，原件不改。新增1份跨域完整数学资源动作930A／0R，当前530目标／146999监督／3240662输入，450≤16K／80长桶；契约436与过程94／72241分报，来源／component不增加。两原函数保持，标准CLI入口和数学域为新作者明确委托／修订；原同response的R已在26，仅对新A授loss，R字段与A字段分别管理曝光，不能当两个独立原任务或重复R。414有限数学检查不授财务／会计／法律或技能收益gold。

9096缺证目标已全元数据分桶；2409路径2397同SHA／12后版本，已恢复354真实来源chunks及两个原native完整write9001字符。87重点目标的祖先复核证明81派生保护（DOCX36＋HTML45），6仍未闭，新增TRAIN准入0；不把缺证当丢失、不因顶层TRAIN洗掉资源祖先、不用后验树补原输入。实际证据与新银行一并06增量，默认train只主manifest20分片。

14B／8B组件主预算仍52／最多100更新；LoRA／损失／Spark／53工具验收、完整自主与合格保留0、原226/H/static隔离及0训练保持。两设计同版复核，修改前history/5.0.43/delta06_20261029；不变原native环境／循环／黄金／奖励／生产及已结束实验。

以下保留5.0.43和更早历史，数量以本轮实际manifest为准：

'''
 for n in ['A_B_MODULES.md','PIPELINE.md']:
  file=ROOT/'research/designs'/n;shutil.copyfile(file,hist/n);s=file.read_text(encoding='utf-8-sig')
  s=s.replace('设计版本：5.0.43','设计版本：5.0.44',1).replace('变更编号：ALG-20261029-01','变更编号：ALG-20261029-02',1)
  pos=s.index('\n',s.index('更新日期：'))+1;file.write_text(s[:pos]+'\n'+note+s[pos:],encoding='utf-8')
 ph=PLAN/'history/pre_delta06_20261029';ph.mkdir(exist_ok=False)
 for f in PLAN.iterdir():
  if f.is_file():shutil.copyfile(f,ph/f.name)
 for n in ['TRAINING_PLAN.md','MODEL_CONTEXT_REQUIREMENTS.md','COVERAGE_EXPANSION.md']:
  file=PLAN/n;s=file.read_text(encoding='utf-8-sig')
  s=s.replace('5.0.43／ALG-20261029-01','5.0.44／ALG-20261029-02').replace('新增或接入34目标、21617','新增或接入35目标、22547')
  for before,after in [('529','530'),('146069','146999'),('3237312','3240662'),('449','450'),('93','94'),('71311','72241'),('18406.25','18638.75'),('60768.75','61001.25'),('1783030','1786380')]:
   s=re.sub(r'(?<![0-9A-Za-z])'+re.escape(before)+r'(?![0-9A-Za-z])',after,s)
  s+='\n06增量新增一份有界数学整程序930A／0R（旧同response R不重复），原529数据文件字节不改。原R与原A分别管曝光；完整pipeline仍未就绪。详细数学域／原CLI错误／原函数和新入口作者及414有限QA见06资源银行与根外置准入。05及其冷核保持历史原件。\n'
  file.write_text(s,encoding='utf-8')
 save(WORK/'ROOT_MATH_ADMISSION.json',proof)
 config=load(ROOT/'output/20261029_wrd_delivery05/TRAINING_CANDIDATES.json');config['data_manifest_sha256']=sha(DATA/'TRAINING_MANIFEST.json');save(WORK/'TRAINING_CANDIDATES.json',config)
 record={'design_revision':'5.0.44','change_id':'ALG-20261029-02','files':[{'path':str(p.resolve()),'bytes':p.stat().st_size,'sha256':sha(p)}for p in [ROOT/'research/designs/A_B_MODULES.md',ROOT/'research/designs/PIPELINE.md',PLAN/'TRAINING_PLAN.md',DATA/'TRAINING_MANIFEST.json',Path(__file__),ROOT/'research/data_prep/wrd_main_v10/verify_main05.py']],
         'previous_record_preserved_in_history':True,'training_started':False}
 save(PLAN/'IMPLEMENTATION_RECORD.json',record)
 print(json.dumps({'counts':dict(total),'default_new_A':930,'new_R':0,'training_started':False}))

if __name__=='__main__':main()
