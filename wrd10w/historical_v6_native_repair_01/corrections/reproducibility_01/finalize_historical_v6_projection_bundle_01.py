"""Finalize local bundle metadata; preserve a superseded metadata-only draft."""
from collections import Counter
from build_historical_v6_native_repair_01 import ROOT,OUT,load,rows,dump,save,digest,sha,js,pin

def main():
    old=OUT/'native_adaptation.full53.conditional64k.compiled.jsonl.gz'
    source={r['id']:r for r in rows(OUT/'native_adaptation.full53.jsonl.gz')};updated=[]
    for r in rows(old):
        item=source[r['id']]
        for t in r['targets']:
            t['owned_supervision_spans']=[[a,b,c,w*.25]for a,b,c,w in t['owned_supervision_spans']if c in {'R','A'}]
            t['supervised_tokens']=sum(b-a for a,b,c,w in t['owned_supervision_spans'])
        r['supervision_spans_sha256']=sha(js(r['supervision_spans']).encode())
        r.update({k:item[k]for k in ['bank','stage','split','source_ids','source_group_id','annotation_provenance']})
        r['original_record_metadata']={k:v for k,v in item.items()if k not in {'messages','tools'}}
        assert r['supervision_spans']==[s for t in r['targets']for s in t['owned_supervision_spans']]
        assert r['supervised_tokens']==sum(t['supervised_tokens']for t in r['targets'])
        assert set(r['supervised_tokens_by_component'])=={'R','A'}
        updated.append(r)
    final=OUT/'native_adaptation.full53.conditional64k.compiled.v2.jsonl.gz';assert not final.exists();dump(final,updated)
    save(OUT/'CONDITIONAL_TARGET_METADATA_CORRECTION.json',{'status':'METADATA_CORRECTED_BEFORE_ROOT_REVIEW',
        'superseded_candidate':pin(old),'selected_v2':pin(final),
        'cause':'Draft full53 global masks/arrays were correctly R/A0.25, but per-target owned_spans still carried old compiler format labels/weights1 and basic provenance fields were missing.',
        'correction':'Synchronize per-target masks to verified global masks; retain bank/source/projection metadata. All input_ids/global labels/weights and1098counts unchanged.',
        'per_target_equals_global_masks_actual_check':'PASS','old_draft_not_default_or_selected':True})
    qa=load(OUT/'DIRECT_TOKEN_AND_RESOURCE_QA.json');cost=load(OUT/'RESOURCE_QA_COST_LEDGER.json')
    text=f'''# 历史报告局修与测试隔离的新作者原生动作训练视图

已实际构建3个有实质目标的样本：报告两证据局修、根据真实覆盖失败纠正批测隔离并重跑、重开实际产物独立复算。core7实际42727输入tokens／1098监督（新作者短理由155、动作投影943），三条均≤16K，系数0.25。原思考和可见解释没有冒充新作者理由或被自动授loss。原始上下文、动作、反馈及版本继续由旧Git实包和本目录精确来源引用保全。

这是`wrd-historical-semantic-native-adaptation-v1`／双稿5.0.41的新状态候选；动作状态是`NEW_AUTHORED_NATIVE_ACTION_PROJECTION_VERIFIED_OFFLINE`。未真实派发OpenClaw Agent、未运行模型、未训练，不能称历史原生调用或完整自主链。内部training_admitted仅使作者局部银标可以CPU编译，root_main_admission=false，等待根独立语义准入。

数据入口为native_adaptation.core7.jsonl.gz，真实编译分片位于../compiled/historical_v6_native_repair_01/。18个独立bin包含两视图各3样本的input_ids/u32le、labels/i64le和weights/f32le。labels在获准R/A范围等于input_ids，其余-100；权重分别0.25和0。双tokenizer直接逐token、offset、独立字符范围、label与weight均核验通过。

完整53工具视图也实际编译为native_adaptation.full53.conditional64k.compiled.v2.jsonl.gz，输入分别38930／38366／40311，监督仍同1098；它们超32K而未截断，条件64K、非默认。初版*.compiled.jsonl.gz仅是保留的metadata纠错草稿，不能选用。完整53与核心7同3个原action owner，只择一曝光；旧v6同原动作及其他新投影也互斥，不能算6个独立训练目标。

完整实际文件快照在states/report_edit、states/runner_fix、states/verify_local。每个都包含合成DEV二进制、相应完整程序／请求／测试资源。早期编辑输入只有旧程序与当时失败，未含未来patch或PASS；runner状态只有坏代码、请求和失败摘要；末状态有真实重跑进程记录与实际产物，尚未执行独立证据检查。原反馈只曾局部送达的事实保留，本次完整程序与功能摘要是明确新状态补充，不宣称原request等价。

固定镜像97a0…／Python实际纯CLI核验，网络关闭、6GiB／4CPU／1GiB shm，进入前宿主≥7GiB且native<8。原bad runner虽然7个进程exit0，却因../outputs合流覆盖而被独立检查检出；按原0ef两处真实修订（输出根与run_meta写入位置）后，7有效／2拒绝及有限逐格值、计数、类型、表名／范围／样式名核验通过。故意破坏check5哈希或check6计数时均FAIL。此为有限资源正确性信用，无Excel视觉／公式引擎／五维Q／技能保留或成本收益证明。

作者第一版只映射输出根，遗漏metadata写位置，首轮独立检查失败；随后一次受Windows换行接线影响的重试也失败，均完整保留在resource_qa及resource_qa_attempt02和corrections。成功版本在resource_qa_attempt03。没有降低检查条件来制造PASS。3次工具QA累计容器墙钟{cost['measured_total_container_wall_seconds']:.3f}秒；CPU user/system、现金与Codex标注成本UNKNOWN_NOT_ZERO。它们是数据整理费用，不是模型训练成本或合格技能成本。

来源仅当前TRAIN的conv_b5e6f3d3bab9及既核177逻辑节点／93CAS闭包，仍隔离原226、新H和静态dev-test。旧251.7MB实包已有Git精确成员SHA引用，本轮不重新复制母包。原坏runner及首次失败、累计解释错误、所有未来信用分开保存；成功退出不自动授正loss。

复现：依次运行build_historical_v6_native_repair_01.py prepare、resource-qa、finalize，compile_main.py编core7，verify_historical_v6_native_repair_01.py独立验证并编条件full53。首次开发失败历史不要求重演；当前脚本已同时包括两处修订，原失败和成本收据仍在交付内。所有产物是科研数据处理，不执行旧Agent循环。
'''
    (OUT/'README.md').write_text(text,encoding='utf-8')
    compiled=ROOT/'output/20261027_wrd_main_v10/compiled/historical_v6_native_repair_01'
    # Explicit final selection, not a glob of all old candidate drafts.
    selection={'default_candidate_source':pin(OUT/'native_adaptation.core7.jsonl.gz'),
        'default_candidate_compilation_report':pin(compiled/'COMPILATION_REPORT.json'),
        'default_candidate_arrays':[r for r in qa['all_binaries_written_and_checked']if '/core7/'in r['path']],
        'full53_conditional_same_owners':pin(final),'full53_conditional_arrays':[r for r in qa['all_binaries_written_and_checked']if '/full53/'in r['path']],
        'current_root_main_admission':False,'main_training_quantity_added_before_root_admission':0,
        'candidate_sequences':3,'candidate_supervised_tokens':1098,'candidate_origins':qa['core_origins']}
    save(OUT/'FINAL_SELECTION.json',selection)
    files=[pin(p)for p in sorted(OUT.rglob('*'))if p.is_file()and p.name!='DELIVERY_MANIFEST.json']
    for name in ['build_historical_v6_native_repair_01.py','historical_v6_local_evidence_check.py','verify_historical_v6_native_repair_01.py','finalize_historical_v6_projection_bundle_01.py']:
        files.append(pin(ROOT/'research/data_prep/wrd_main_v10'/name))
    files.extend(pin(p)for p in sorted(compiled.iterdir())if p.is_file())
    save(OUT/'DELIVERY_MANIFEST.json',{'schema_version':'wrd-historical-semantic-native-adaptation-v1','status':'ACTUAL_ARRAYS_RESOURCE_QA_PASS_PENDING_ROOT',
        'files':files,'root_main_admission':False,'training_started':False,'native_agent_sessions':0,'model_calls':0})
    for entry in files:
        p=__import__('pathlib').Path(entry['path']);assert p.stat().st_size==entry['bytes']and digest(p)==entry['sha256']
    print(js({'status':'PASS','files':len(files),'bytes':sum(r['bytes']for r in files),'manifest_sha256':digest(OUT/'DELIVERY_MANIFEST.json')}))
if __name__=='__main__':main()
