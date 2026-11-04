"""Assemble exact metadata overlay; no original scope or training modifications."""
from pathlib import Path
import gzip,hashlib,json
OUT=Path(__file__).parent;BASE=OUT.parent
def sha(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def pin(p):p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':sha(b)}
def rows(p):return list(map(json.loads,gzip.open(p,'rt',encoding='utf-8')))
def save(n,d):(OUT/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
    assert not(OUT/'RECOVERY_REVIEW.json').exists()
    nativepath=BASE/'20261029_wrd_missing_lineage_native/SOURCE_CLOSURE_CANDIDATES_02.json'
    native=load(nativepath);assert pin(nativepath)['sha256']=='53e1fa2bfe5febc17031c5691aa8a351580b5bd54b0621ec98b317fea8592b45'
    census=load(OUT/'CENSUS.json');carriers=load(OUT/'CARRIER_CHECKS.json');readers=load(OUT/'ALL_ACTUAL_SOURCE_READER_BINDINGS_V2.json')
    targets={x['id']:x for x in rows(OUT/'HOLD_TARGETS_9096.metadata.jsonl.gz')}
    make=[x for x in rows(OUT/'MAKE_100_EPISODE_CLUSTERS.metadata.jsonl.gz')];all1050={i for x in make for i in x['held_target_ids']}
    dep=native['docx_actual_omitted_dependencies'];newprotected=dep['newly_proven_protected_descendant_held_target_ids'];early=dep['earlier_still_missing_producer_held_target_ids']
    assert len(set(newprotected))==36 and len(early)==5 and set(newprotected)|set(early)==next(set(x['held_target_ids']) for x in make if x['episode_id']=='ep_5de7f066feaed4c4b254')
    for i in newprotected:assert i in targets and i in all1050 and targets[i]['source_message_index']>=13
    original_meta={x['id']:x for x in rows(BASE/'20261026_wrd_dataset_v9/outcomes/recomputed_scope_overlay/target_outcome_labels.jsonl.gz')}
    producers=[]
    for head in dep['head_views_metadata_only_no_protected_body_copied']:
        proof=head['matching_original_write_proof']
        if proof is None:continue
        expected=proof['target_metadata'];actual=original_meta[expected['id']];assert actual==expected
        assert actual['source_admission']=='HOLD_PROTECTED' and actual['original226']
        assert any(x['content_sha256']==head['source_file']['sha256'] for x in actual['exact_produced_file_write_proofs'])
        producers.append({'target_id':actual['id'],'episode_id':actual['episode_id'],'scope_proof_id':actual['scope_proof_id'],'source_admission':actual['source_admission'],'original226':actual['original226'],
            'exact_produced_file_write_proofs':actual['exact_produced_file_write_proofs'],'actual_received_head_sha256':head['head_bytes_sha256'],'head_view_partial':not head['whole_file_visible_within_head']})
    assert len(producers)==3
    save('CURRENT_ANCESTRY_OVERLAY_CANDIDATE.json',{'schema':'wrd-v9-current-evidence-overlay-candidate-v1','base_9096_unchanged':True,
        'native_actual_read_proof':pin(nativepath),'independent_producer_scope_metadata_check':'Each of3 copied producer target metadata equals final v9 row, each has original226 and matching whole-file original write SHA.',
        'protected_ancestor_producers_metadata_only':producers,'target_updates':[{'id':i,'base_status':'HOLD_MISSING_EVIDENCE','candidate_current_status':'HOLD_PROTECTED_ACTUAL_ANCESTOR_READ_RECOVERED',
            'reason':'Original DOCX tool observation12 actually includes3 previous-skill head views whose actual producer write prefixes are original226-protected.','evidence':pin(nativepath),'positive_loss':0} for i in newprotected],
        'earlier5_still_unknown_target_ids':early,'not_an_applied_reclassification_or_train_admission':True,'no_protected_text_copied_or_semantically_reviewed':True,'training_started':False})
    overview={'schema':'wrd-v9-missing-evidence-recovery-review-v1','status':'COMPLETE_METADATA_CENSUS_AND_PARTIAL_REAL_EDGE_RECOVERY_NO_NEW_TRAIN_ADMISSION',
        'final_v9_HOLD_targets':9096,'make_and_legacy_skill_make':1434,'known_source_TRAIN_only_maker_targets':1050,'known_source_TRAIN_only_maker_episodes':100,
        'key_interpretation':'These are potential action positions with unresolved ancestry, not1050 ready examples. 96 final trees/89 with code/247 program references104 distinctSHA are snapshots and reuse, not247 independently correct creation sequences.',
        'physical_carriers':carriers['summary'],'prior_resource_graph':{'ep_node_pairs':1264,'with_exact_frozen_identity_and_at_least_one_matching_carrier':1144,'variable_or_malformed_or_dynamic_old_identity_gaps':69,'other_no_exact_old_identity':51,
            'not_exhaustive_actual_reads':'DOCX for-loop head command reveals3 actual SKILL dependencies absent from old resource graph. Thus this1264 inventory cannot certify full context closure.'},
        'actual_bounded_source_runtime_edges':{'current_receipt':pin(OUT/'ALL_ACTUAL_SOURCE_READER_BINDINGS_V2.json'),'command_mentions':readers['command_mentions'],'actual_invocations':readers['actual_matching_invocations'],
            'passed_actual_payloads':readers['passed_calls'],'episodes':readers['passed_distinct_episodes'],'actual_chunks':readers['actual_passed_chunks'],'actual_UTF8bytes':readers['actual_passed_received_UTF8bytes'],
            'one_redirected_file_not_yet_model_receipt':1,'script_reads_or_mentions_not_invocations':8,'specific_invocation_edges_not_blanket_script_or_whole_episode_admission':True},
        'real_complete_original_program_recovery':{'receipt':pin(OUT/'scheduled_program_recovery/ORIGINAL_WRITE_RECOVERY.json'),'programs':2,'original_characters':9001,'real_native_writes_and_success_acks':True,'sameSHA_as_final_tree':True,'scope_and_quality':'HOLD; not semantically reviewed'},
        'selected_large_clusters':[
            {'episode_id':'ep_04149c237fc7afb2bd67','route':'scheduled-task-config','held_targets':56,'progress':'22actual source-reader calls/140original chunks87488UTF8bytes bound to4TRAIN files;2full originalnativewrite programs recovered.','remaining':'Route/new_route/contract/merge/reuse producers, dynamic actual path identities, per-function code/QA semantics; current scope remainsHOLD.'},
            {'episode_id':'ep_df95d2f3cf09628aa3ac','route':'teaching-html-demo','held_targets':46,'progress':'Independent actual2TRAIN source-reader1call/6chunks2507UTF8bytes; dynamic boundaryfile originalSHA restored; nonexistent/error-only cases distinguished.','remaining':'Exact route/value-plan/framework producer ancestry and later per-call versions; all46HOLD.'},
            {'episode_id':'ep_5de7f066feaed4c4b254','route':'docx-standardize-export','held_targets':41,'progress':'Actual omitted3SKILL head reads matched protected originalwriteproducers.','remaining':'36newprotected descendants; earlier5route/previousproducer gap. No body material from protected sources used for labels.'},
            {'episode_id':'ep_5b5e58ac2499ea46957b','route':'remotion-explainer-video','held_targets':13,'progress':'21exact sameSHA metadata aliases locate priorSKILL producer ep_daae809463dd396b475b and archive automaticfeedback.','remaining':'Unique actual route dispatch and feedback/trial provenance/runtime inputs; previousbyte identity alone not wholeTRAIN.'}],
        'newly_proven_protected_targets':36,'old_9096_not_rewritten':True,'full_current_TRAIN_closure_candidates_admitted':0,'new_positive_tokens':0,'training_started':False,
        'remaining_work':'Continue100episode actual read/exec/path/oldskill producer closure beyond graph approximation, then fullprogram/repair semantic review and real-state compilation under root admission. Do not infer positive loss from write success, green tests, final tree, current source tags or source-file existence.',
        'v1_reader_scan_history':'V1 was preliminary:8mentions are not actual reader invocations and2valid payloads had directory-list prefixes. V2 explicitly fixes framing and labels one local redirected output as not received. OriginalV1 preserved as history; V2 is current.',
        'frozen05_main529_146069_unchanged':True,'no_protected_source_text_semantically_read_or_printed':True,'no_new_native_Agent_model_business_or_training_run':True,'curation_cost':'UNKNOWN_NOT_ZERO'}
    save('RECOVERY_REVIEW.json',overview)
    report='''本轮对v9最终9096个HOLD_MISSING_EVIDENCE目标完成元数据全量分桶，没有把旧版本11432口径混入。

其中制作相关1434个；已知来源ID全部为当前TRAIN的有1050个，分布在100个原episode。这1050只是需要继续闭合的候选位置。96个episode有最终资源树、89个有程序，247个程序引用只有104种SHA；不能把复制版本或最终快照直接算成独立正确训练动作。

实际核对2409个路径全部存在、2397同SHA。12个原路径版本发生变化，但各冻结文件身份都有其他同SHA载体。旧图1264个episode-resource节点中1144个有冻结身份，全部找到匹配载体；剩余69动态/变量/畸形路径和51无精确身份，不能由旧图缺键推成文件丢失。

已落实际证据：9个episode的48次原source-reader返回、354个原chunk、163140 UTF8字节逐原会话message/leaf/区间/SHA核验通过。另1次只写本地batch文件，尚不能算模型收到正文。scheduled-task-config原两次完整nativewrite共9001字符，连同原参数、成功回执及同SHA最终资源都已恢复到scheduled_program_recovery/；其来源祖先和程序语义仍HOLD，未授正。

并行深审还发现旧图漏依赖：DOCX真实for/head返回3份旧SKILL首页，其真实原write祖先含原226保护来源，使36个原暂扣位置新证为保护派生。已另建候选overlay，旧9096/主集/05完全未改。HTML46个位置也仅补实具体source-reader和动态路径边，未闭合整条祖先链。Remotion13个位置已定位前版同SHA和反馈载体，仍需producer及试跑来源证明。

当前新增全闭合TRAIN目标0、新正监督tokens0。下一步应从上述真实程序/运行时边继续做资源祖先、旧SKILL与反馈来源、实际版本和局部代码正确性审核，再构造和编译新状态样本。成功写入、文件存在或测试绿均不是整体正loss。未启动模型、业务或训练；整理费用未知而非0。
'''
    (OUT/'REPORT.md').write_text(report,encoding='utf-8')
    save('DELIVERY_MANIFEST.json',{'files':[pin(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='DELIVERY_MANIFEST.json'],
        'external_independent_evidence':[pin(nativepath)],'current_census_entry':'RECOVERY_REVIEW.json','current_reader_edge_entry':'ALL_ACTUAL_SOURCE_READER_BINDINGS_V2.json','all_other_V1_outputs_history_not_new_labels':True,
        'positive_loss':0,'frozen05_modified':False,'new_native_or_training':False})
    print(json.dumps({'status':overview['status'],'recovery_review_sha256':pin(OUT/'RECOVERY_REVIEW.json')['sha256'],'manifest_sha256':pin(OUT/'DELIVERY_MANIFEST.json')['sha256'],'files':len(load(OUT/'DELIVERY_MANIFEST.json')['files'])}))

if __name__=='__main__':main()
