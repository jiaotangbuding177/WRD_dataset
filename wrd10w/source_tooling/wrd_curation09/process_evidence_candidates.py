"""Metadata-only explicit audit candidate snapshot, never freeze/build/upload.

Root must independently rehash and apply its final allowlist/credential/URL policy.
"""
import hashlib,json,os,re,stat
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'output/20261031_wrd_curation09'
DEST=ROOT/'output/20261031_wrd_curation09_delivery/EXPLICIT_EVIDENCE_CANDIDATES09.json'
DIRECTORIES={
    'coverage','writers','process','resource_qa','resource_qa02','extra_resource_qa',
    'lesson_qa','process_peer_qa','reasoning','holdout','eval_input_arrays09',
    'eval_input_arrays09_independent','token_peer','followup_peer',
    'protection_followup09','protection_followup09_independent',
    'full_stage_qa02','admission','report_peer',
}

def reparse(path):
    info=path.lstat()
    return path.is_symlink()or bool(getattr(info,'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',0x400))

def hashfile(path):
    digest=hashlib.sha256()
    with path.open('rb')as stream:
        while block:=stream.read(8*1024*1024):digest.update(block)
    return digest.hexdigest()

def excluded(path):
    parts=[p.lower()for p in path.relative_to(BASE).parts]
    if '__pycache__'in parts or path.suffix.lower()in{'.pyc','.pyo'}:return 'PYTHON_CACHE'
    if any(p in{'fixture','fixtures','fakekey','fakekeys','fake_keys'}or'fakekeys'in p or'fake_keys'in p for p in parts):return 'FIXTURE_OR_FAKEKEY_PATH'
    return None

def walk(directory,rejects):
    for root,dirs,files in os.walk(directory,followlinks=False):
        parent=Path(root);kept=[]
        for name in dirs:
            p=parent/name;reason=excluded(p)
            if reason:rejects[reason+'_DIRECTORY_PRUNED']+=1
            elif reparse(p):rejects['REPARSE_DIRECTORY_NOT_FOLLOWED']+=1
            else:kept.append(name)
        dirs[:]=sorted(kept)
        for name in sorted(files):
            p=parent/name;reason=excluded(p)
            if reason:rejects[reason]+=1
            elif reparse(p):rejects['REPARSE_FILE_NOT_FOLLOWED']+=1
            else:yield p

def latest_report(directory,prefix,name):
    choices=[]
    for p in directory.glob(prefix+'*/'+name):
        match=re.fullmatch(re.escape(prefix)+r'(\d+)(?:_[A-Za-z0-9_-]+)?',p.parent.name)
        if match:choices.append((int(match.group(1)),p))
    return max(choices,key=lambda v:(v[0],v[1].parent.name))[1]if choices else None

def main():
    started=datetime.now(timezone.utc).isoformat()
    selected=set(DIRECTORIES)
    selected.update(p.name for p in BASE.iterdir()if p.is_dir()and p.name.startswith('compiled_'))
    assert all((BASE/name).is_dir()for name in selected)
    rejects=Counter();candidates=[]
    for dirname in sorted(selected):candidates.extend(walk(BASE/dirname,rejects))
    candidates.extend([BASE/'ROOT_ADDITIONAL_CODE_EXCLUSIONS09.json',BASE/'ACTUAL_DATA_AND_COVERAGE09.json'])
    candidates.extend(sorted((BASE/'package_preparation/history').glob('*.py')))
    candidates.extend(sorted((BASE/'package_preparation/history').glob('*.md')))
    # These two trees contain deliberate fixtures and fake keys: only explicit
    # final reports/contracts are considered. Do not recursively include them.
    special=[]
    for dirname in ['admit_tool_selftest','package_preparation']:
        directory=BASE/dirname;special.append(directory/'CONTRACT.md')
        final=latest_report(directory,'run','SELFTEST.json')
        assert final is not None;special.append(final)
        if dirname=='package_preparation':
            qa=latest_report(directory,'restore_policy','QA.json');assert qa is not None;special.append(qa)
            extra=final.parent/'EXACT_CRLF_QA.json';assert extra.is_file();special.append(extra)
    assert len(special)==6
    candidates.extend(special)
    assert len(candidates)==len({p.resolve()for p in candidates})
    files=[];counts=Counter();unstable=[]
    for p in sorted(candidates,key=lambda v:v.relative_to(ROOT).as_posix()):
        assert p.is_file()and not reparse(p)and excluded(p)is None
        absolute=p.resolve();assert absolute.is_relative_to(BASE.resolve())
        before=p.stat();digest=hashfile(p);after=p.stat()
        changed=(before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns)
        rel=p.relative_to(ROOT).as_posix();group=p.relative_to(BASE).parts[0]
        files.append({'path':rel,'absolute_path':str(absolute),'bytes':after.st_size,'sha256':digest,
            'category':'CONTROLLED_AUDIT','evidence_directory':group,'observed_mtime_ns':after.st_mtime_ns,
            'changed_during_hash':changed})
        counts[group]+=1
        if changed:unstable.append(rel)
    report={'schema_version':'wrd09-explicit-evidence-candidate-snapshot-v1',
        'status':'CANDIDATE_SNAPSHOT_ONLY_ROOT_REHASH_REQUIRED_NOT_FROZEN',
        'started_at_utc':started,'completed_at_utc':datetime.now(timezone.utc).isoformat(),
        'source_root':str(BASE.resolve()),'all_files_category':'CONTROLLED_AUDIT',
        'files':files,'file_count':len(files),'total_bytes':sum(r['bytes']for r in files),
        'by_evidence_directory':dict(counts),'selected_evidence_directories':sorted(selected),
        'special_report_allowlist':[p.relative_to(ROOT).as_posix()for p in special],
        'excluded_path_rule_counts':dict(rejects),'changed_during_hash':unstable,
        'excluded_from_two_selftest_trees':'ALL_MEMBERS_EXCEPT_SIX_EXPLICIT_FINAL_SELFTEST_QA_CONTRACT_REPORTS',
        'no___pycache___pyc_fixtures_fakekeys_selected':True,
        'no_enterprise_body_copied':True,'no_public_repository_mutation':True,
        'freeze_performed':False,'build_performed':False,'credential_scan_completed':False,
        'final_allowlist_main_sourcecode_design_QA_aliases_controlled_URL_Git_owner':'ROOT_TASK',
        'root_must_rehash_any_file_or_scope_that_changes':True,
        'script_sha256':hashfile(Path(__file__))}
    DEST.parent.mkdir(parents=True,exist_ok=True)
    if DEST.exists():
        old=DEST.read_bytes();oldsha=hashlib.sha256(old).hexdigest()
        historical=DEST.parent/'history'/('EXPLICIT_EVIDENCE_CANDIDATES09_'+oldsha+'.json')
        historical.parent.mkdir(exist_ok=True)
        if historical.exists():assert historical.read_bytes()==old
        else:historical.write_bytes(old)
        report['preserved_previous_snapshot']={'path':str(historical),'bytes':len(old),'sha256':oldsha}
    package_reports=[p for p in special if 'package_preparation'in p.parts and p.suffix=='.json']
    safe_tests=[]
    for p in package_reports:
        data=json.loads(p.read_text(encoding='utf8'))
        count=data.get('test_count',data.get('count',data.get('additional_tests')))
        safe_tests.append({'path':p.relative_to(ROOT).as_posix(),'count':count,'sha256':hashfile(p)})
    assert sum(r['count']for r in safe_tests)==60
    report['package_preparation_final_safe_tests']={'count':60,'reports':safe_tests}
    DEST.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'path':str(DEST),'sha256':hashfile(DEST),'files':len(files),'bytes':report['total_bytes'],
        'changed_during_hash':len(unstable),'special_reports':report['special_report_allowlist']},ensure_ascii=False))

if __name__=='__main__':main()
