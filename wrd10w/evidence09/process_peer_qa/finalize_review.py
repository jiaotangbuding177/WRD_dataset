"""Bind independent source/range/resource findings without editing process data."""
import gzip, hashlib, json
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
PROCESS=ROOT/'output/20261031_wrd_curation09/process'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def hs(s):return hashlib.sha256(s.encode('utf-8')).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def text(m):
 c=m.get('content','')
 return c if isinstance(c,str)else '\n'.join(b.get('text','')for b in c if b.get('type')=='text')

def main():
 source=PROCESS/'FUNCTIONAL_CANDIDATES05.jsonl.gz'
 rows=[json.loads(l)for l in gzip.open(source,'rt',encoding='utf-8')if l.strip()]
 reservation_path=ROOT/'output/20261031_wrd_curation09/holdout/holdout_reservation.json';reservation=load(reservation_path)
 scope={r['source_id']:r for r in(json.loads(l)for l in gzip.open(ROOT/'output/20261027_wrd_main_v10/clean_inputs/source_scope.metadata.jsonl.gz','rt',encoding='utf-8'))}
 checks=[]
 for row in rows:
  packet_path=Path(row['source_context']['path']);assert sha(packet_path)==row['source_context']['sha256']
  packet=load(packet_path);given=[]
  for ref in row.get('source_material_messages_provided_in_new_state',[]):
   i=ref['message_index'];assert i<row['original_message_index']
   body=text(packet['original_context']['messages'][i]);assert hs(body)==ref['text_sha256']
   assert body in row['messages'][1]['content'];given.append(i)
  assert row['message_loss_mask']==[0,0,1]and row['supervision_message_indices']==[2]
  assert row['teacher_original_R_supervised']is False and row['messages'][-1].get('reasoning_content','')==''
  assert not set(row['source_ids']).intersection(reservation['reserved_source_ids'])
  components={scope[s]['component_id']for s in row['source_ids']}
  assert not components.intersection(reservation['reserved_source_scope_components'])
  assert all(scope[s]['status']=='TRAIN'for s in row['source_ids'])
  checks.append({'owner_id':row['owner_id'],'source_ids':row['source_ids'],'source_components':sorted(components),
    'prior_source_message_indices_exactly_delivered_in_new_state':given,
    'original_system_incomplete_and_new_state_disclosed':row['original_native_prompt_equivalence_claimed']is False,
    'actual_tool_or_projection_scope':row['output_content_provenance'],
    'source_reserved_intersection':[],'component_reserved_intersection':[]})
 slide=next(r for r in rows if r['owner_id']=='0f1603b601613eac2fecb014')
 code=slide['messages'][-1]['tool_calls'][0]['function']['arguments']['content']
 needle=" <div class='layer' style='width:640px;background:linear-gradient(90deg,#00b8cf,#3fc9dc);'>商业模式原生</div>"
 assert code.count(needle)==1; a=code.index(needle)
 extra={'owner_id':slide['owner_id'],'target_original_code_sha256':hs(code),
     'start':a,'end':a+len(needle),'text_sha256':hs(needle),
     'reason':'ACTUAL_SLIDE24_TOP_LAYER_WHITE_TEXT_ON_CYAN_CONTRAST_2_398_TO_1_981_BELOW_LARGE_TEXT_3_1',
     'evidence':'workspace/qa_outputs/RESULT.json#slide24_known_contrast_failure_reproduced',
     'source_unchanged':True,'required_before_positive_admission':True}
 save(OUT/'ADDITIONAL_REQUIRED_NEGATIVE_RANGE.json',{'status':'NEW_INDEPENDENTLY_VERIFIED_ERROR_RANGE; DO_NOT_MODIFY_ORIGINAL_PROGRAM', 'ranges':[extra]})
 result=load(OUT/'workspace/qa_outputs/RESULT.json');assert not result['failed_check_names']
 negatives=load(OUT/'INDEPENDENT_108_RANGE_CHECK.json')['ranges']
 receipt=load(OUT/'DOCKER_RECEIPT.json');assert receipt['exit_code']==0
 report={'schema':'wrd_curation09_independent_process_resource_peer_v1',
   'status':'CONDITIONAL_SCOPED_RESOURCE_PASS; ADD_SLIDE24_NEGATIVE_BEFORE_ADMISSION',
   'reviewed_candidate_pin':{'path':str(source.relative_to(ROOT)),'sha256':sha(source),'targets':len(rows)},
   'reviewed_semantics_pin':{'path':str((PROCESS/'SEMANTIC_REVIEW05.json').relative_to(ROOT)),'sha256':sha(PROCESS/'SEMANTIC_REVIEW05.json')},
   'reservation_sha256':sha(reservation_path),'source_state_checks':checks,
   'original_code_complete':True,'all_4_programs_completely_read_before_execution':True,
   'safety_scope':'Only local document/image/browser resource code and public font reads; no external service/API calls or unknown private input access. Fixed container network disabled.',
   'original_108_ranges':{'exact_code_character_SHA_pass':True,'by_owner':dict(Counter(r['owner_id']for r in negatives)),
       'semantic_assessment':'Matrix assignment unvalidated; organization role/governance labels unvalidated; tax/director/currency narrative unverified; legal body includes wrong or unverified notice/relationship terms. Exclusions are justified; no success/exit0 promotion.',
       'proof_pin':{'path':'INDEPENDENT_108_RANGE_CHECK.json','sha256':sha(OUT/'INDEPENDENT_108_RANGE_CHECK.json')},
       'actual_token_mask_qa_performed_by_this_review':False},
   'resource_run':{'image':receipt['image'],'network':'none','memory':'6g','cpus':4,'shm_size':'1g',
      'elapsed_seconds':receipt['elapsed_seconds'],'checks':len(result['checks']),'operation_or_negative_reproduction_checks_failed':[],
      'result_pin':{'path':'workspace/qa_outputs/RESULT.json','sha256':sha(OUT/'workspace/qa_outputs/RESULT.json')},
      'outputs':'36 actual3840x2160 PNGs;3417x2417 organization PNG;22-row5-column XLSX/13 merges reopened;DOCX reopened. No PPTX is emitted by these4 programs and none is claimed.',
      'generated_file_validity_is_not_business_correctness':True},
   'new_confirmed_error':extra,
   'five_scope_verdicts':[
      {'owner':'0f1603b601613eac2fecb014','verdict':'PASS_LOCAL_RENDERER_ONLY_AFTER_EXTRA_NEGATIVE','limit':'36 PNG render/dimensions and text viewport bounds pass. Page19 region semantics and page24 top-layer style are zero-loss. No image-model generation, full deck visual/design-source fidelity or KEEP claim.'},
      {'owner':'b1be5b288ae637de175154a5','verdict':'PASS_LOCAL_DIAGRAM_RENDERER_WITH37_BUSINESS_LABELS_EXCLUDED','limit':'Render reviewed; readable diagram. Governance/headcount/medical-regulation optimum and accounting/cashier role compatibility are not positive business labels.'},
      {'owner':'43280ee97c7e5a3da3c9053c','verdict':'PASS_XLSX_EXPORT_MECHANISM_WITH8_EXCLUSIONS','limit':'Valid reopened XLSX, original user fee literals preserved. No formulas/external links. Tax/director/currency/timing assertions and newline-based row-height visibility do not become positive business facts; no one-page print guarantee.'},
      {'owner':'45444e97188d392abd301d94','verdict':'PASS_DOCX_EXPORT_MECHANISM_WITH62_LEGAL_LITERALS_EXCLUDED','limit':'Valid reopened DOCX. Three-day termination notice in a non-full-time relationship is inconsistent with official Article71; that body is already masked. Full legal correctness is not admitted.'},
      {'owner':'890556c82086d7fd1b896de3','verdict':'PASS_EXACT_FIVE_CHARACTER_LABEL_REPAIR_ONLY','limit':'Exact before/after differs by5 stray b characters; full JavaScript byte-identical. The draw-side physics mutation and wrong static arrow remain, so this edit does not approve physics.'}],
   'new_R_or_original_R_credit':0,'full_autonomous_A_D_credit':0,'qualified_KEEP_credit':0,
   'source_refs':[{'url':'https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum','scope':'SC1.4.3 normal4.5:1/large3:1; directly supports confirmed style error'},
                  {'url':'https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/bgt/art/2023/art_0abfdd261c03417b949df19d869add8d.html','scope':'Article71 permits notice at any time for non-full-time employment; no full contract legal review'}],
   'execution_scope':{'no_process_source_or_training_main_mutation':True,'business_Teacher_Actor_calls':0,'model_weights_loaded':False,'training_started':False,'ai_cpu_curation_resource_cost':'UNKNOWN_NOT_ZERO'}}
 save(OUT/'INDEPENDENT_PEER_REVIEW.json',report)
 print(json.dumps({'report_sha256':sha(OUT/'INDEPENDENT_PEER_REVIEW.json'),'extra_range_sha256':sha(OUT/'ADDITIONAL_REQUIRED_NEGATIVE_RANGE.json'),'checks':len(result['checks'])}))

if __name__=='__main__':main()
