"""Recover two exact teacher functions into a complete scoped math CLI.

The source physical CRLF file, LF action string, raw request/SSE and actual
finite receipt are separately pinned. New functional input, header and CLI
entrypoint are explicitly authored; no Teacher native-write is invented.
"""
import ast
import gzip
import hashlib
import json
from pathlib import Path
import shutil
ROOT=next(p for p in Path(__file__).resolve().parents if(p/'AGENTS.md').is_file());OUT=Path(__file__).resolve().parent;SOURCE=ROOT/'output/20261015_ewi_teacher_DATA/episodes/conv_1702b763a7ee';PAIR='8856374c439400f01448d478'
def sha(b):return hashlib.sha256(b).hexdigest()
def digest(p):return sha(Path(p).read_bytes())
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,v):assert not p.exists();p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def ref(p):p=Path(p);return{'path':str(p),'bytes':p.stat().st_size,'sha256':digest(p)}
def main():
    assert not(OUT/'SOURCE_REVIEW.json').exists();original=OUT/'original';original.mkdir()
    pairs=ROOT/'output/20261026_wrd_sequences_v6/controlled/reasoning_pairs.original116.jsonl.gz'
    with gzip.open(pairs,'rt',encoding='utf-8')as f:pair=next(x for x in map(json.loads,f)if x.get('id')==PAIR)
    code=pair['observed_parsed_output']['arguments']['code'];probe=SOURCE/'M4/try_w1_valuation_conv1702b763a7ee/repair/probe.py';assert digest(probe)=='0dc9024ff3199b58dd7f4bc759722747106f3e7aa7806605519866e1be55303c';assert probe.read_text(encoding='utf-8')==code
    preserve=[probe,probe.parent/'scope.json',probe.parent/'observation.json',probe.parent/'stdout.raw',probe.parent/'stderr.raw',probe.parent/'workspace/outputs/valuation_result.json',probe.parent.parent/'operation.json',probe.parent.parent/'observation.json',probe.parent.parent/'dependency_scope.json']
    for role in('source_request','source_sse','source_stored_response','source_receipt','source_parsed'):
        pin=pair.get(role)
        if pin:p=Path(pin['path']);assert digest(p)==pin['sha256'];preserve.append(p)
    entries=[]
    for index,p in enumerate(preserve):
        target=original/f'{index:02d}_{p.name}';shutil.copyfile(p,target);entries.append({'original':ref(p),'portable_copy':ref(target)})
    (original/'original_action_code.LF.py').write_text(code,encoding='utf-8',newline='')
    save(original/'original_action.json',pair['observed_parsed_output'])
    lines=code.splitlines(keepends=True);functions={n.name:''.join(lines[n.lineno-1:n.end_lineno])for n in ast.parse(code).body if isinstance(n,ast.FunctionDef)};assert set(functions)=={'compute_valuation','main'}
    header='''"""A bounded arithmetic model, with the supplied field vocabulary.

Use finite positive numeric I, decimal s in (0,1), and optional C satisfying
0<C<=Pre, where Post=I/s and Pre=Post-I. With C absent return symbolic split
formulas instead of inventing a unique split. C<=Pre is this model's chosen
non-negative-remainder domain, not a general financial or legal requirement.
The unchanged teacher function uses ordinary Python assertions; run without
-O. Validation is basic and not a full input schema or path-safety validator.
The tol argument is supported here only at its default 1e-6. Extreme floating
point inputs are outside the promised range. Units must be consistent and s
must already be converted to a decimal fraction. No percent-string parsing.
CLI entry always parses its required flags; no fixed sample runs implicitly.
"""
import json, os


'''
    module=header+functions['compute_valuation'].rstrip('\n')+'\n\n\n'+functions['main'].rstrip('\n')+'\n\n\nif __name__ == "__main__":\n    main()\n';ast.parse(module)
    resource=OUT/'resources/proportional_split.py';resource.parent.mkdir();resource.write_text(module,encoding='utf-8',newline='')
    state=OUT/'state_before_write';(state/'outputs').mkdir(parents=True);assert not(state/'outputs/proportional_split.py').exists()
    with gzip.open(ROOT/'output/20261027_wrd_main_v10/clean_inputs/source_scope.metadata.jsonl.gz','rt',encoding='utf-8')as f:scope=next(x for x in map(json.loads,f)if x['source_id']=='conv_1702b763a7ee')
    assert scope['status']=='TRAIN'
    observation=load(probe.parent/'observation.json');product=probe.parent/'workspace/outputs/valuation_result.json';assert digest(product)==observation['products'][0]['sha256']and observation['exit_code']==0
    review={'schema':'wrd-TRAIN-original-EWI-probe-scoped-resource-semantic-review-v1','status':'FULL_CODE_REVIEWED_MATH_SCOPED_NATIVE_CONSTRUCTION_CANDIDATE','source_id':'conv_1702b763a7ee','current_source_status':'TRAIN','source_component_id':scope['component_id'],'source_scope_sha256':digest(ROOT/'output/20261027_wrd_main_v10/clean_inputs/source_scope.metadata.jsonl.gz'),'original_response_owner':PAIR,'original_action_id':pair['observed_parsed_output']['action_id'],'original_action_kind':'TRY','original_code_author':'Recorded teacher exact original TRY.arguments.code','original_action_code_LF_sha256':sha(code.encode()),'original_physical_probe_CRLF_sha256':digest(probe),'CRLF_physical_bytes_and_LF_action_string_not_same_byte_identity':True,'original_CODE_characters':len(code),'original_files':entries,'original_full_request_and_SSE_preserved':True,
        'new_complete_resource':ref(resource),'new_resource_authoring':{'verbatim_teacher_functions':[{'name':n,'original_function_LF_sha256':sha(v.rstrip('\n').encode()),'characters_without_trailing_newline':len(v.rstrip('\n'))}for n,v in functions.items()],'new_authored_parts':['Scoped mathematical module docstring','Necessary json/os imports without unused sys','Standard unconditional main entrypoint; removes episode-specific implicit sample/self-test branch'],'not_a_byte_identical_original_full_program':True},
        'mathematical_proof':{'given':'I>0, 0<s<1, Post=I/s, Pre=Post-I=I(1-s)/s>0; optional0<C<=Pre, common units.','with_C':'P=Pre/C; New=I/P=I*C/Pre; Reserve=I-New>=0. New/(C+New)=I/(Pre+I)=s, and New+Reserve=I.','without_C':'I and s uniquely fix Post/Pre but leave New=I*C/Pre dependent on the unspecified C. Return formula strings, not one invented C or numeric split.','numeric_scope':'Finite floats, 1<=I<=1e6 and0.01<=s<=0.99, optional1e-3<=C<=Pre, default tol1e-6, no -O. This is a bounded declared domain; not claimed globally robust near under/overflow.'},
        'explicit_limits':['C<=Pre is a chosen mathematical domain for a non-negative remainder, not certified financial/accounting/legal validity.','Assertions are ordinary Python assertions, not full schema/type/authorization validation; bool and optimized mode outside promised domain.','Original C<=Pre+tol accepts a tiny tolerance overage; caller promised exact C<=Pre, no universal negative-remainder rejection claim.','Unchanged main writes caller-supplied output path; filesystem permissions/overwrite safety belong to caller.','Original finite observation ran the no-flag self-verification body with C1000 and None. It did not prove CLI execution, arbitrary parameters, business correct delivery or qualified skills.'],
        'original_finite_test_evidence':{'actual_exit':observation['exit_code'],'exact_program_sha256':observation['script_sha256'],'actual_stdout_sha256':sha(observation['stdout'].encode()),'actual_product':ref(product),'function_branches_exercised':['C=1000','C=None'],'checks_are_code_authored_not_independent_Q':True,'old_bridge_or_native_Agent_execution_not_claimed':True},
        'known_original_dispatch_defect':{'condition':'Original __main__ only calls parser when the exact token --increase is in sys.argv. --increase=<value> or no flags run the fixed episode demo.','source_physical_program_preserved':True,'new_functional_resource_always_calls_main':True,'new_entrypoint_not_claimed_original_teacher_edit':True},
        'exposure_owner_policy':{'canonical_original_A_owner':'historical_EWI_action:'+PAIR,'canonical_original_R_owner':PAIR,'original_R_already_positive_in_main26':True,'new_target_R_positive_tokens':0,'new_resource_view_A_only':True,'original_old_ActionProposal_body_had_no_positive_A_in_current_main':True,'core_full_and_any_other_A_views_mutually_exclusive':True},
        'new_user_functional_state_is_not_original_request_equivalent':True,'no_original_or_future_test_results_in_prestate':True,'new_Agent_calls':0,'training_started':False,'ACTIVE_modified':False,'root_main_admission':False,'script_sha256':digest(Path(__file__))}
    save(OUT/'SOURCE_REVIEW.json',review);print(json.dumps({'status':review['status'],'resource_characters':len(module),'resource_sha256':digest(resource),'review_sha256':digest(OUT/'SOURCE_REVIEW.json'),'original_LF_sha256':sha(code.encode()),'original_CRLF_sha256':digest(probe)}))
if __name__=='__main__':main()
