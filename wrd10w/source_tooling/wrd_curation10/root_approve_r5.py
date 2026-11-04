"""Freeze root-scoped semantic approval of the explicit five R/A projections.

This only creates compiler staging input. Main activation still requires the
separate frozen manifest, isolation, independent tokenizer/mask and restore QA.
"""
from pathlib import Path
import gzip,hashlib,json
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/20261031_wrd_curation10/reasoning_semantic10'
PIN='b26347fbeef8408980ff06f60964f82fb1885a0ece94256cb3213e3b88495b84'
def h(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def pin(p):p=Path(p);b=p.read_bytes();return{'path':str(p),'bytes':len(b),'sha256':h(b)}
def main():
 p=OUT/'CANDIDATES.proposed.raw.jsonl.gz';assert pin(p)['sha256']==PIN
 rs=[json.loads(l)for l in gzip.open(p,'rt',encoding='utf-8')if l.strip()]
 expected={'recontext10-B_revision_report_01-0017','recontext10-B_revision_report_01-0024','recontext10-B_revision_report_01-0025','recontext10-B_make_report_02-0014','recontext10-B_make_report_02-0016'}
 assert {r['id']for r in rs}==expected and len(rs)==5
 sources=[OUT/'FROZEN5_SEMANTIC_STATE_AND_SOURCE_QA.json',OUT/'CPU_RESOURCE_CHECKS.json',OUT/'OLD_VS_REVISED_REAL_COUNTEREXAMPLES.json',OUT/'COMPONENT_CREDIT_AND_OWNER_LEDGER.json']
 assert all(p.is_file()for p in sources)
 for r in rs:
  assert r['training_admitted']is False and r['root_main_admission']is False
  assert r['original_R_provenance']['kind']=='RECONTEXTUALIZED_ORIGINAL_COMPAT_R'
  assert r['A_original_action_arguments_identical']is True and r['loss_multiplier']==.25
  assert r['approved_components']==['A'] and r['approved_field_ranges']
 receipt={'status':'ADMIT_ROOT_SCOPED_RECONTEXTUALIZED_ORIGINAL_COMPAT_R_AND_RECORDED_API_A_ONLY','record_ids':sorted(expected),
  'proposed_raw':pin(p),'evidence':[pin(x)for x in sources],
  'root_read_scope':'Read all five complete selected R excerpts, local current-state premises and tested before/after checks; retained unknown/procedural R zero ranges. Artifact/code behavior supported by independent resource reviewer and actual CPU old21/revised21+12 plus same-input before/after counterexamples.',
  'admitted_scope':'Current-state local diagnosis/test design/resource action only; no full original native request, hidden upstream private CoT, complete autonomous parent, business Q, skill utility or KEEP approval.',
  'original_R_verbatim_contiguous_excerpt_and_separate_origin_required':True,
  'original_A_identity_basis':'Exact decoded captured compatible API args, not equality of redacted native export where exception is declared',
  'all_post_target_tests_credit_only_not_earlier_prompt':True,'no_prior_R_or_A_credit_duplicate_per_owner':True,
  'loss_multiplier':.25,'full_pipeline_training_ready':False,'main_not_activated':True,'training_started':False,'script':pin(__file__)}
 dest=OUT/'ROOT_R5_SCOPED_SEMANTIC_APPROVAL.json';assert not dest.exists();dest.write_bytes((json.dumps(receipt,ensure_ascii=False,indent=2)+'\n').encode())
 for r in rs:
  r.update(training_admitted=True,root_semantic_staging_approval=pin(dest),root_main_admission=False,requires_external_root_admission=True)
 out=OUT/'ROOT_APPROVED_STAGING.raw.jsonl.gz';assert not out.exists()
 with out.open('wb')as f:
  with gzip.GzipFile(filename='',fileobj=f,mode='wb',mtime=0)as g:
   for r in rs:g.write((json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n').encode())
 print(json.dumps({'root_staged_rows':len(rs),'original_proposed_unmodified':pin(p)['sha256']==PIN,'staging':pin(out),'main_not_activated':True}))
if __name__=='__main__':main()
