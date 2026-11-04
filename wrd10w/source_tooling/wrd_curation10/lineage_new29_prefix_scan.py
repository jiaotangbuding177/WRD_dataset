"""Supplement compiled-state isolation with original recorded input prefixes.
No protected thought, Q or assistant body is used as a matching basis.
"""
from pathlib import Path
import collections,gzip,hashlib,importlib.util,json,sys
ROOT=Path('D:/skillloop');WORK=ROOT/'output/20261031_wrd_curation10';OUT=WORK/'lineage'
def h(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def rows(p):return[json.loads(l)for l in gzip.open(p,'rt',encoding='utf-8-sig')if l.strip()]
def pin(p):p=Path(p);return{'path':str(p),'bytes':p.stat().st_size,'sha256':h(p.read_bytes())}
def module(name,p):
    s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s)
    old=sys.dont_write_bytecode;sys.dont_write_bytecode=True
    try:s.loader.exec_module(m)
    finally:sys.dont_write_bytecode=old
    return m
def main():
    helper=module('p0_prefix_pattern_basis',ROOT/'research/data_prep/wrd_curation10/lineage_recheck.py')
    protected=helper.original_user_basis();ep,einfo=helper.get_eval_basis()
    compiled=WORK/'compiled_combined29';report=load(compiled/'COMPILATION_REPORT.json')
    rr=[]
    for f in report['files']:
        p=compiled/f['path'];assert pin(p)['sha256']==f['sha256'];rr+=rows(p)
    assert len(rr)==29
    output=[];hits=[];cache={}
    for r in rr:
        md=r['original_record_metadata'];ev=md.get('evidence',{});original=[]
        req=ev.get('source_compatible_API_request')or md.get('source_API_original_request_preserved')
        if req:
            p=Path(req['path']);assert pin(p)==req
            original=load(p)['messages'];identity=req['sha256'];source={'kind':'EXACT_COMPATIBLE_API_REQUEST_MESSAGES','pin':req,
              'limits':'Full recorded compatible request; hidden provider/SDK request still not captured.'}
        else:
            ref=md.get('source_context')or ev.get('original_context')
            assert ref,(r['id'],'MISSING_DECLARED_ORIGINAL_CONTEXT')
            assert pin(ref['path'])==ref
            context=rows(ref['path'])[0];idx=md.get('original_native_message_index')
            if idx is None:idx=md.get('original_message_index')
            assert idx is None or isinstance(idx,int)and 0<=idx<len(context['messages']),(r['id'],idx,len(context['messages']))
            original=context['messages'][:idx]if idx is not None else context['messages']
            identity=ref['sha256']+':'+str(idx)
            source={'kind':'ORIGINAL_NATIVE_VISIBLE_PREFIX_STRICTLY_BEFORE_TARGET'if idx is not None else'ORIGINAL_SUPPORT_CARRIER_ISOLATION_ONLY_NO_SINGLE_RECORDED_TARGET','pin':ref,'native_target_index':idx,
              'limits':'Missing original system/API stays missing; this scan does not clear unknown code/resource ancestry.'}
        if identity not in cache:
            hh=[]
            for basis,patterns in [('PROTECTED_ORIGINAL_USER',protected['patterns']),('RESERVED26_ORIGINAL_REQUEST_OR_MATERIAL',ep)]:
                hh.extend({'basis':basis,**x}for x in helper.scan_messages(original,patterns))
            cache[identity]=hh
        for x in cache[identity]:hits.append({'view_id':r['id'],'source_kind':source['kind'],**x})
        output.append({'view_id':r['id'],'bank':r['bank'],'original_input':source,'scanned_messages':len(original),
          'matches':len(cache[identity]),'compiled_state_also_scanned_in_NEW29_PREFIX_STATE_ISOLATION_QA':True})
    d={'status':'PASS_NO_EXACT_PROTECTED_OR_EVAL_MATCH_IN_ORIGINAL_RECORDED_PREFIXES'if not hits else'REQUIRES_ROOT_MATCH_CLASSIFICATION',
      'compiled_union_report':pin(compiled/'COMPILATION_REPORT.json'),'views':len(rr),'unique_prefixes':len(cache),
      'rows':output,'matches':hits,'new_reserved_SOURCE_group_checks':pin(OUT/'NEW29_PREFIX_STATE_ISOLATION_QA.json'),
      'protected_pattern_sources':len(protected['forbidden']),'protected_original_user_messages':protected['users'],'eval_basis':einfo,
      'new_state_cannot_clear_known_original_ancestry_by_restatement':True,
      'protected_grades_Q_or_thought_used':False,'no_match_not_universal_ancestry_proof':True,
      'new_business_calls':0,'training_started':False,'script_pin':pin(__file__)}
    p=OUT/'NEW29_ORIGINAL_PREFIX_ISOLATION_QA.json';p.write_bytes((json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode())
    print(json.dumps({'status':d['status'],'views':len(rr),'unique_prefixes':len(cache),'matches':len(hits),'QA':pin(p)}),flush=True)
if __name__=='__main__':main()
