"""Seal this bounded file-only audit; never run old tools or mutate banks."""
from pathlib import Path
import hashlib,json
from recover_two_lineage import DEST, safe_file, pin, sha

def load(n):return json.loads((DEST/n).read_text(encoding='utf-8'))
def save(n,v):(DEST/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def main():
    a=load('TWO_EPISODE_IDENTITY_RECOVERY_01.json')
    b=load('SOURCE_CLOSURE_CANDIDATES_02.json')
    c=load('HTML_ROUTE_CARD_PROTECTED_PRODUCER_CLOSURE_03.json')
    actual=[]
    for ep in a['episodes'].values():
        for r in ep['resource_identities']:
            if r['expected_identity']:
                assert len(r['carriers'])==2
                for p in r['carriers']:
                    assert p['exact_expected_SHA'] and sha(safe_file(p['path']))==p['sha256']
                    actual.append(p)
        for p in ep['native_carriers']:
            assert p['exact_expected_SHA'] and sha(safe_file(p['path']))==p['sha256']
            actual.append(p)
    protected=set(b['docx_actual_omitted_dependencies']['newly_proven_protected_descendant_held_target_ids'])
    protected.update(c['downstream_impact']['newly_proven_protected_descendant_held_target_ids'])
    held={t for e in a['episodes'].values() for t in e['held_target_ids']}
    assert len(held)==87 and len(protected)==81 and protected<=held
    assert sum(e['identity_coverage']['exact_identity'] for e in a['episodes'].values())==44
    verification={'status':'PASS_BOUNDED_IDENTITY_AND_CLASSIFICATION_ARITHMETIC_NOT_TRAINING_ADMISSION',
      'independent_carrier_SHA_rechecks':len(actual),'two_episode_held_targets':87,
      'newly_proven_protected_descendant_target_ids':sorted(protected),'protected_target_count':81,
      'remaining_missing_producer_target_ids':sorted(held-protected),'remaining_unknown_count':6,
      'new_admitted_targets':0,'actual_unknown_physical_file_identity_not_filled':True,
      'source_or_training_banks_modified':False,'new_native_or_training':False}
    save('LOCAL_VERIFICATION_04.json',verification)
    names=['inventory_selected.py','SELECTED_METADATA_01.json','recover_two_lineage.py',
      'TWO_EPISODE_IDENTITY_RECOVERY_01.json','resolve_evidence_edges.py','SOURCE_CLOSURE_CANDIDATES_02.json',
      'resolve_html_card_03.py','HTML_ROUTE_CARD_PROTECTED_PRODUCER_CLOSURE_03.json',
      'README.md','seal_recovery.py','LOCAL_VERIFICATION_04.json']
    files=[]
    for name in names:
        p=safe_file(DEST/name);files.append({'path':name,**pin(p),'role':'audit_only_not_automatic_supervision'})
    for folder in ['metadata_objects','recovered_objects']:
        for p in sorted((DEST/folder).iterdir()):
            assert p.is_file() and len(p.name)==64 and sha(safe_file(p))==p.name
            files.append({'path':folder+'/'+p.name,**pin(p),'role':'audit_only_exact_metadata_or_synthetic_original_bytes'})
    ap=DEST/'FINAL_LOCAL_ALLOWLIST.jsonl'
    ap.write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in files),encoding='utf-8')
    manifest={'schema':'wrd-two-maker-lineage-final-local-v1','status':'ACTUAL_FILES_SEALED_NOT_NEW_TRAINING_BANK_OR_GIT_UPLOAD',
      'files':len(files),'source_bytes':sum(r['bytes'] for r in files),'allowlist_sha256':sha(ap),
      'held_targets_examined':87,'newly_proven_protected_descendant_targets':81,'still_missing_producer':6,
      'exact_identity_resource_references':44,'same_SHA_carriers_rechecked':len(actual),
      'exact_old_resource_distinct_SHA':41,'omitted_actual_old_skill_reads_found':3,
      'new_admitted_training_targets':0,'frozen05_and_current_manifest_unchanged':True,
      'all_original_external_ancestor_pins_are_references_not_a_new_full_ancestor_pack':True,
      'no_protected_conversation_body_inspected_or_copied':True,'no_old_command_or_helper_executed':True,
      'new_native_or_training':False}
    save('FINAL_LOCAL_MANIFEST.json',manifest)
    print(json.dumps({'manifest':pin(DEST/'FINAL_LOCAL_MANIFEST.json'),'allowlist':pin(ap),
      'files':len(files),'bytes':manifest['source_bytes'],'protected':81,'unknown':6,'new_admitted':0}))

if __name__=='__main__':main()
