"""Preserve draft01 and create explicit source-only projection revision02."""
from pathlib import Path
from copy import deepcopy
import gzip
import hashlib
import json

HERE=Path(__file__).resolve().parent;BATCH=HERE.parent
OLD=BATCH/'remotion/source_only/source_only_controller.raw.jsonl.gz'
OUT=BATCH/'remotion/source_only02'
def sha(b):return hashlib.sha256(b).hexdigest()
def pin(p):return {'path':str(p),'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size}
def js(v):return json.dumps(v,ensure_ascii=False,separators=(',',':'))

def main():
    assert not OUT.exists();OUT.mkdir(parents=True)
    with gzip.open(OLD,'rt',encoding='utf-8')as f:original=[json.loads(s)for s in f]
    rows=deepcopy(original);changes=[]
    old_intro='以下为按导出出现顺序保留的原始会话前缀。助手陈述是历史自述，不能代替原始工具观察；未提供的文件和工具状态仍未知。'
    new_intro='以下为现有会话投影的前缀，保留该投影顺序；它结合用户出现顺序与语义响应阶段重构，原生历史先后和回复对应未经认证。助手陈述是历史自述，不能代替原始工具观察；未提供的文件和工具状态仍未知。'
    for old,r in zip(original,rows):
        user=r['messages'][1]['content'];assert user.count(old_intro)==1
        r['messages'][1]['content']=user.replace(old_intro,new_intro)
        r.pop('input_contains_no_future_messages',None)
        r.update(prefix_is_projection_not_authenticated_native_order=True,
            input_contains_no_messages_after_selected_projection_prefix=True,
            native_historical_order_and_reply_to_verified=False,
            projection_order_disclaimer_in_model_input=True)
        if r['id']=='source_only_remotion:reported_failure_evidence':
            d=json.loads(r['messages'][2]['content']);assert '相互矛盾的404归因'in d['retain']
            d['retain'][d['retain'].index('相互矛盾的404归因')]='不同404归因及其未核实状态'
            r['messages'][2]['content']=json.dumps(d,ensure_ascii=False,indent=2)
        if r['id']=='source_only_remotion:resume_timeout':
            s=r['messages'][2]['reasoning_content'];needle='用户要求接续同一制作任务，超时只说明前次运行未正常继续。'
            assert needle in s
            r['messages'][2]['reasoning_content']=s.replace(needle,'用户要求接续同一制作任务；用户报告前次失败或超时，实际进程终态未知，需核原进程与文件状态。')
        assert r['original_input_prefix_sha256']==old['original_input_prefix_sha256']
        # Same canonical new-label owner; revision01 and revision02 are exclusive.
        r['supersedes_revision01_same_owner']=True;r['revision01_and_revision02_not_both_trainable']=True
        changes.append({'id':r['id'],'prefix_end_exclusive':r['prefix_end_exclusive'],
            'original_projected_prefix_SHA_unchanged':r['original_input_prefix_sha256'],
            'old_new_rationale_SHA256':[sha(x['messages'][2]['reasoning_content'].encode())for x in[old,r]],
            'old_new_decision_SHA256':[sha(x['messages'][2]['content'].encode())for x in[old,r]],
            'old_new_user_input_SHA256':[sha(x['messages'][1]['content'].encode())for x in[old,r]],
            'projection_order_disclaimer_added_to_input':True})
    new=OUT/'source_only_controller.raw.jsonl.gz'
    with new.open('wb')as raw:
        with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0)as f:
            for r in rows:f.write((js(r)+'\n').encode())
    receipt={'status':'REVISION02_EXPLICIT_PROJECTION_ORDER_AND_TWO_BOUNDED_SEMANTIC_CORRECTIONS',
        'old_raw_preserved':pin(OLD),'new_raw':pin(new),'changed_targets':changes,
        'source_original_bytes_and_selected_prefix_JSON_unchanged':True,
        'no_new_independent_sources_or_original_R_actions':True,'root_main_admission':False,
        'review_basis':'Root approved scheduled independent peer corrections and requested explicit unauthenticated projection order; old raw/compiled must not also be exposed.',
        'source_ancestry_unchanged':'TRAIN conv_eaf2e429a225; protected maker route/code/feedback remains excluded.',
        'training_started':False,'new_Agent_calls':0,'script_SHA256':sha(Path(__file__).read_bytes())}
    (OUT/'CHANGE_RECEIPT.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    builder=(BATCH/'controller_compilation/build_all.py').read_text(encoding='utf-8')
    assert "BATCH/'remotion/source_only/source_only_controller.raw.jsonl.gz'"in builder
    builder=builder.replace("BATCH/'remotion/source_only/source_only_controller.raw.jsonl.gz'","BATCH/'remotion/source_only02/source_only_controller.raw.jsonl.gz'")
    (HERE/'build_all.py').write_text(builder,encoding='utf-8')
    print(json.dumps({'new_raw':pin(new),'new_builder':pin(HERE/'build_all.py'),'targets':len(rows)}))

if __name__=='__main__':main()
