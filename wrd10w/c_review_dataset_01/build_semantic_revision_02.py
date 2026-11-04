"""Preserve v1 and deterministically rebuild a separate, narrowed v2 dataset."""
from pathlib import Path
import hashlib,json

HERE=Path(__file__).resolve().parent
source=HERE/'build_dataset.py'
code=source.read_text(encoding='utf-8')
replacements=[
    ("OUT=BASE/'c_review_dataset_01'", "SOURCE_OUT=BASE/'c_review_dataset_01'\nOUT=SOURCE_OUT/'semantic_revision_02'\nOUT.mkdir(parents=True,exist_ok=True)\nshutil.copyfile(SOURCE_OUT/'C_review.original_responses.jsonl.gz',OUT/'C_review.original_responses.jsonl.gz')"),
    ("process_review_path=OUT/'independent_process_review/PROCESS_CANDIDATES.json'", "process_review_path=SOURCE_OUT/'independent_process_review/PROCESS_CANDIDATES.json'"),
    ("approve(9,'Condensing is allowed','those are preserved.',", "approve(9,'Condensing is allowed','five headings not mandatory if semantics preserved.',"),
    ("approve(9,'1. Five reasons preserved:','both preserve.',", "approve(9,'1. Five reasons preserved:','both yes.',"),
    ("Actual E outputs cover the five reasons and retain current need/candidate readiness; this does not approve the E_A added superlative.", "Actual E outputs cover the five reasons. No blanket qualifier fidelity is credited: E_A strengthens other source modalities."),
    ("native_C_review_partial_01", "native_C_review_partial_02"),
    ("native_C_execution_local_01", "native_C_execution_local_02"),
    ("new_real_state_cost_stop_01", "new_real_state_cost_stop_02"),
    ("NEW_AUTHORED_REAL_STATE_COST_STOP_01", "NEW_AUTHORED_REAL_STATE_COST_STOP_02"),
    ("{label:{'dimensions':quality['cases'][c][label]['dimensions'],'weighted_total':quality['cases'][c][label]['weighted_total']} for label in ['A','B']}", "{label:deepcopy(quality['cases'][c][label]) for label in ['A','B']}"),
    ("'original_artifacts_are_preserved_separately':True,", "'functional_Q_projection':{'retained':'All four original per-label objects including primary_deduction_note; original length observations; explicit AI-uncalibrated identity','omitted_from_functional_state':'Repeated source IDs and requirements already available as full original user content; capture/read-order attestation fields represented as independently verified plain facts. The full unmodified original report remains separately pinned.'},'original_artifacts_are_preserved_separately':True,"),
    ("reason='该版本", "state['quality_identity']['independent_semantic_correction']='原AI盲Q对E_A限定词保真评价过宽：原文学生难以持续承担责任，被改写为无法承担；贵州工作随着相关工作从探索转向建设，被写成已从探索转向建设。新增最合适人选也超出原文。以上是具体语义加强，不据此擅改原Q数值；原AI条目及分数作为可错的观察保留。'\nreason='该版本"),
]
for before,after in replacements:
    assert before in code,before
    code=code.replace(before,after)
exec(compile(code,str(source)+'::semantic_revision_02','exec'))
out=HERE/'semantic_revision_02'
(out/'DETERMINISTIC_REVISION_RECEIPT.json').write_text(json.dumps({
    'schema':'v10-C-semantic-revision-source-transform-v1','parent_builder':str(source),
    'parent_builder_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
    'revision_wrapper':str(Path(__file__).resolve()),'revision_wrapper_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'transformed_source_sha256':hashlib.sha256(code.encode()).hexdigest(),'replacements':replacements,
    'previous_draft_and_compilation_preserved':True,'root_main_admission':False,
    'semantic_change':'withdraw two overly broad qualifier-preservation clauses; explain the known original AI-Q omission in the newly authored state; preserve original Q scores unchanged',
    'not_an_alternative_agent_or_native_tool_loop':True},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
