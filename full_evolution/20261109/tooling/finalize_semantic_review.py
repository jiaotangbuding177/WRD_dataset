"""Attach pre-execution evaluator-only semantics without changing maker inputs."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
CORPUS=ROOT/'output/20261108_wrd58_full_evolution/package/corpus'
INVENTORY=Path(__file__).resolve().parent
REVIEW=ROOT/'output/20261108_wrd58_full_evolution/lineage/SEMANTIC_REVIEW12.json'
EXPECTED_REVIEW_SHA='d7abdee6e0895d5fda01564e03d16f7f69401bd8fcb6ae50d72e06b83c1f34af'
ORIGINAL_FREEZE_SHA='dd1d306eb8538ee11c04f17c36bfe237ac54a0b2f46ba5730509d959ea97293d'
STOP_IDS={'conv_276e97b595fc','conv_34843d227bc0'}


def sha(raw):return hashlib.sha256(raw).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,o):p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
def pin(p):return {'path':p.relative_to(CORPUS).as_posix(),'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size}


def main():
    review_raw=REVIEW.read_bytes()
    assert sha(review_raw)==EXPECTED_REVIEW_SHA
    freeze_path=CORPUS/'EFFECT_FREEZE12.json'
    history_path=CORPUS/'provenance/effect_freeze_before_semantic_review.json'
    if history_path.exists():assert sha(history_path.read_bytes())==ORIGINAL_FREEZE_SHA
    else:
        old_raw=freeze_path.read_bytes();assert sha(old_raw)==ORIGINAL_FREEZE_SHA
        history_path.write_bytes(old_raw)
    evaluator=CORPUS/'evaluator_only';evaluator.mkdir(exist_ok=True)
    (evaluator/'SEMANTIC_REVIEW12.json').write_bytes(review_raw)
    (evaluator/'POSITIVE_SOURCE_AUDIT.json').write_bytes((INVENTORY/'POSITIVE_SOURCE_AUDIT.json').read_bytes())
    (evaluator/'README.md').write_text('# 仅供实验结束后独立评审\n\n本目录不得挂载到maker工作区或加入模型prompt。语义分层在任何学生执行前从原会话静态审阅产生，不是学生输出、原teacher逐源成功金标或新的SFT标签。12来源中10项允许根据历史证据提炼方法并自建新完整受控试跑；276e/348两项原任务只停在追问，预期有依据地停止，不强迫产包。全1107材料不因此删除。\n',encoding='utf-8',newline='\n')
    freeze=load(freeze_path)
    selected_ids={r['source_id'] for r in freeze['selected']}
    assert len(selected_ids)==12 and STOP_IDS<=selected_ids
    freeze.update(semantic_review=pin(evaluator/'SEMANTIC_REVIEW12.json'),
                  original_freeze_before_semantic_review=pin(history_path),
                  maker_inputs_changed_by_semantic_review=False,
                  semantic_review_basis='PRE_EXECUTION_STATIC_SOURCE_REVIEW_NOT_STUDENT_OUTCOMES_OR_TEACHER_GOLD',
                  positive_source_ids=sorted(selected_ids-STOP_IDS),rejection_source_ids=sorted(STOP_IDS),
                  evaluation_targets={'make_or_grounded_scope_sources':10,'grounded_stop_sources':2,
                                      'skill_delivery_denominator':10,'route_decision_denominator':12,
                                      'universal_12_source_skill_delivery_target_retracted':True},
                  positive_qualification='10 sources allow grounded method abstraction and new controlled complete-input trials; not certified original-business replay or teacher standalone success.',
                  evaluation_visibility='evaluator_only files and expected decisions are never maker resources or prompt')
    save(freeze_path,freeze);freeze_pin=pin(freeze_path)
    rows=[json.loads(l) for l in (CORPUS/'INDEX.jsonl').read_text(encoding='utf-8').splitlines()]
    for row in rows:
        if row['source_id'] not in selected_ids:continue
        row['student_eligibility']['new_freeze']=freeze_pin
        save(CORPUS/'cases'/row['source_id']/'case.json',row)
    (CORPUS/'INDEX.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in rows),encoding='utf-8',newline='\n')
    manifest=load(CORPUS/'MANIFEST.json')
    manifest.pop('source_and_resource_missing',None);manifest.pop('source_and_resource_hash_mismatch',None)
    manifest.update(effect_freeze=freeze_pin,declared_input_files_missing=0,declared_input_sha256_mismatch=0,
                    declared_input_check_scope='All files declared by current historical delivery records exist with matching hashes; this does not establish that every historical reference was restored.',
                    semantic_input_completeness='NOT_UNIVERSALLY_CERTIFIED',
                    effect12_maker_semantic_review=pin(evaluator/'SEMANTIC_REVIEW12.json'),
                    effect12_make_or_grounded_scope_sources=10,effect12_grounded_stop_sources=2,
                    effect12_semantic_review_is_original_teacher_gold=False,
                    evaluator_only_never_maker_input=True)
    save(CORPUS/'MANIFEST.json',manifest)
    files=sorted(p for p in CORPUS.rglob('*') if p.is_file() and p.name!='SHA256SUMS')
    (CORPUS/'SHA256SUMS').write_text(''.join(sha(p.read_bytes())+'  '+p.relative_to(CORPUS).as_posix()+'\n' for p in files),encoding='utf-8',newline='\n')
    result={'file_count':len(files)+1,'total_bytes':sum(p.stat().st_size for p in files)+(CORPUS/'SHA256SUMS').stat().st_size,
            'freeze':freeze_pin,'manifest':pin(CORPUS/'MANIFEST.json'),'index':pin(CORPUS/'INDEX.jsonl'),
            'sha256sums':pin(CORPUS/'SHA256SUMS'),'resources_objects_changed':False,
            'source_prompt_or_resources_changed':False,'original_freeze':pin(history_path),
            'semantic_review':pin(evaluator/'SEMANTIC_REVIEW12.json')}
    save(INVENTORY/'FINAL_CORPUS_SIZE.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
