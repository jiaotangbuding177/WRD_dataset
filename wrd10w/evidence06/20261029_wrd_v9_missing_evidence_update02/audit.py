"""Metadata-only correction overlay; old recovery report remains historical."""
from pathlib import Path
import gzip,hashlib,json
BASE=Path('D:/skillloop/output');OUT=Path(__file__).parent
def sha(b):return hashlib.sha256(b).hexdigest()
def pin(p):p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':sha(b)}
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def main():
    assert not(OUT/'ANCESTRY_CORRECTION_OVERLAY.json').exists()
    old=BASE/'20261029_wrd_v9_missing_evidence_recovery/RECOVERY_REVIEW.json'
    docx_path=BASE/'20261029_wrd_missing_lineage_native/SOURCE_CLOSURE_CANDIDATES_02.json'
    html_path=BASE/'20261029_wrd_missing_lineage_native/HTML_ROUTE_CARD_PROTECTED_PRODUCER_CLOSURE_03.json'
    assert pin(html_path)['sha256']=='1189782a9682617279e3a64f2fcbc5c8b30a8c2735ad83aa650e511f9a5991aa'
    docx=load(docx_path);html=load(html_path)
    v9path=BASE/'20261026_wrd_dataset_v9/outcomes/recomputed_scope_overlay/target_outcome_labels.jsonl.gz'
    allrows={x['id']:x for x in map(json.loads,gzip.open(v9path,'rt',encoding='utf-8'))}
    proof=html['original_producer']['scope_proof_at_actual_write'];assert proof==allrows[proof['id']] and proof['source_admission']=='HOLD_PROTECTED' and len(proof['protected_source_ids'])==17 and len(proof['original226'])==16 and len(proof['holdout12'])==1
    assert html['input_card_read']['observation_index']==4 and html['input_card_read']['entire_actual_observation_exactly_equals_input_file_bytes']
    assert html['card_derivation']['all_original_card_fields_preserved_exactly'] and html['card_derivation']['additional_input_field_only']=='candidate_gate'
    d=docx['docx_actual_omitted_dependencies'];h=html['downstream_impact']
    a=set(d['newly_proven_protected_descendant_held_target_ids']);b=set(h['newly_proven_protected_descendant_held_target_ids'])
    early=set(d['earlier_still_missing_producer_held_target_ids'])|set(h['earlier_still_missing_producer_held_target_ids'])
    assert len(a)==36 and len(b)==45 and not a&b and len(early)==6
    for target in a|b:
        row=allrows[target];assert row['source_admission']=='HOLD_MISSING_EVIDENCE'
        assert row['source_message_index']>(12 if target in a else 4)
        assert row['episode_id']==('ep_5de7f066feaed4c4b254' if target in a else 'ep_df95d2f3cf09628aa3ac')
    overlay={'schema':'wrd-missing-lineage-evidence-correction-overlay-v2','status':'81_NEW_PROTECTED_ANCESTRY_DESCENDANTS_6_STILL_UNKNOWN_0_TRAIN_ADMISSION',
        'supersedes_only_later_ancestry_count_not_original_bytes':pin(old),'new_external_HTML_producer_receipt':pin(html_path),'external_DOCX_receipt':pin(docx_path),
        'independent_checks':'HTML originalwrite scope metadata exactly equals finalv9 row, with17 protected sources:16 original226 plus1 newH. 81targets are all in final9096 and disjoint36DOCX+45HTML; each strictly follows actual receipt. No protected body semantically read.',
        'HTML_original_producer':{'episode_id':proof['episode_id'],'target_id':proof['id'],'original226':proof['original226'],'holdout12':proof['holdout12'],'protected_source_ids':proof['protected_source_ids'],'scope_proof_id':proof['scope_proof_id']},
        'newly_proven_protected_total':81,'DOCX_protected':36,'HTML_protected':45,'remaining_unknown_in_selected87':6,'remaining_unknown_target_ids':sorted(early),
        'target_overlays':[{'id':i,'base_v9_status':'HOLD_MISSING_EVIDENCE','evidence_current_status':'HOLD_PROTECTED_ACTUAL_ANCESTOR_RECEIVED','source_message_index':allrows[i]['source_message_index'],
            'evidence':pin(docx_path if i in a else html_path),'positive_loss':0} for i in sorted(a|b)],
        'old9096_old32files_original226_and_checkpoint05_unmodified':True,'not_applied_to_original_manifest':True,'new_TRAIN_closures':0,'new_positive_tokens':0,'new_native_or_training':False,'curation_cost':'UNKNOWN_NOT_ZERO'}
    (OUT/'ANCESTRY_CORRECTION_OVERLAY.json').write_text(json.dumps(overlay,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    manifest={'files':[pin(OUT/'ANCESTRY_CORRECTION_OVERLAY.json'),pin(Path(__file__))],'source_pins':[pin(old),pin(docx_path),pin(html_path),pin(v9path)],'old_frozen_files_modified':False,'positive_loss':0}
    (OUT/'MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'protected_descendant_targets':81,'still_unknown_in87':6,'new_ADMIT':0,'overlay_sha256':pin(OUT/'ANCESTRY_CORRECTION_OVERLAY.json')['sha256'],'manifest_sha256':pin(OUT/'MANIFEST.json')['sha256']}))

if __name__=='__main__':main()
