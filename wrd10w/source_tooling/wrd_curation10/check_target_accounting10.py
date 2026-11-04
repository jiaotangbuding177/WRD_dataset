"""Regression: a retained failed assistant call is context, not a new target."""
from pathlib import Path
from array import array
import hashlib,importlib.util,json
ROOT=Path(__file__).resolve().parents[3]
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def main():
 m=module('count10',ROOT/'research/data_prep/wrd_curation10/admit10.py')
 old=module('count09_reference_only',ROOT/'research/data_prep/wrd_curation09/admit09.py')
 ids=[11,12,13,14];spans=[[2,3,'D',.25]]
 r={'id':'synthetic-target-count','bank':'source_contract_main','stage':'synthetic','split':'train','source_ids':['synthetic-source'],
  'source_group_id':'synthetic-only','input_ids':ids,'total_tokens':4,'input_ids_sha256_u32le':hashlib.sha256(array('I',ids).tobytes()).hexdigest(),
  'supervision_spans':spans,'supervision_spans_sha256':m.hs(m.js(spans)),'supervised_tokens':1,'supervised_tokens_by_component':{'D':1},
  'messages':[{'role':'user','content':'fixture'},{'role':'assistant','content':'previous failed action'},{'role':'assistant','content':'new target'}],
  'targets':[{'message_index':1,'owned_supervision_spans':[]},{'message_index':2,'owned_supervision_spans':spans}],
  'original_record_metadata':{'owner_id':'synthetic-target-count','training_admitted':True,'source_admission':'ADMIT','supervision_message_indices':[2],
   'actual_native_tool_dispatch':False,'teacher_original_R_supervised':False}}
 prior=old.report_for([r],{'counts':{}},[]);now=m.report_for([r],{'counts':{}},[])
 assert prior['counts']['targets']==2 and now['counts']['targets']==1
 assert m.recount([r])['actual_counts']['targets']==1
 assert now['counts']['supervised_tokens']==1
 out=ROOT/'output/20261031_wrd_curation10/admit_tool_selftest/TARGET_ACCOUNTING_QA.json'
 m.save(out,{'status':'PASS_CONTEXT_ONLY_ASSISTANT_METADATA_NOT_COUNTED_AS_NEW_TARGET',
   'rendered_assistant_metadata':2,'positive_targets':1,'positive_tokens':1,'old_report_only_would_count':2,
   'main_mask_and_old_checkpoint_not_modified':True,'training_started':False,'script':m.pin(__file__)})
 print(json.dumps(m.load(out)))
if __name__=='__main__':main()
