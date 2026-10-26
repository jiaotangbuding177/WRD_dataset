"""Materialize clean conversation inputs and byte-verified real attachments.

This creates replay resources, not new agent executions or trial outcomes.
"""
import gzip
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/20261026_wrd_dataset_v9'


def digest(p):
    h=hashlib.sha256()
    with Path(p).open('rb')as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()


def main():
    source=OUT/'coordination/entrypoint_controller.native_paths.source_closed.jsonl.gz'
    dest=OUT/'replay_inputs'
    dest.mkdir(exist_ok=True)
    aliases=[]; seen=set(); counts={'conversations':0,'material_aliases':0,'material_unique_sha256':0,'material_bytes_with_aliases':0}
    with gzip.open(source,'rt',encoding='utf-8')as f:
        for line in f:
            row=json.loads(line);state=json.loads(row['messages'][1]['content']);sid=row['source_id']
            refs=[r for r in row['source_evidence_refs'] if r.get('path','').endswith('conversation.json')]
            assert len(refs)==1
            ref=refs[0];original=Path(ref['path']);assert digest(original)==ref['sha256']
            target=dest/'conversations'/(sid+'.json');target.parent.mkdir(exist_ok=True)
            shutil.copyfile(original,target)
            aliases.append({'source_id':sid,'kind':'conversation','native_path':'/workspace/inputs/conversations/'+sid+'.json','path':target.relative_to(OUT).as_posix(),'bytes':target.stat().st_size,'sha256':digest(target),'original_path':str(original)})
            counts['conversations']+=1
            for item in state['file_inputs']:
                expected=item.get('declared_pin_sha256')
                if not item.get('eligible_real_input') or item.get('eligible_file_current_sha256_verified') is not True or not isinstance(expected,str):continue
                original=Path(item['resolved_existing_path']);assert original.is_file() and digest(original)==expected
                native=item['declared_native_path'];assert native.startswith('/workspace/inputs/materials/')
                relative=PurePosixPath(native.removeprefix('/workspace/inputs/'))
                assert not relative.is_absolute() and '..' not in relative.parts
                target=dest/Path(*relative.parts);assert target.resolve().is_relative_to(dest.resolve())
                target.parent.mkdir(parents=True,exist_ok=True)
                if target.exists():assert digest(target)==expected
                else:shutil.copyfile(original,target)
                aliases.append({'source_id':sid,'kind':'material','native_path':native,'path':target.relative_to(OUT).as_posix(),'bytes':target.stat().st_size,'sha256':expected,'original_path':str(original),'actual_current_bytes_verified':True,'historical_identity_claimed':False})
                counts['material_aliases']+=1;counts['material_bytes_with_aliases']+=target.stat().st_size;seen.add(expected)
    counts['material_unique_sha256']=len(seen)
    report={'schema_version':'wrd-v9-materialized-clean-input-resources','counts':counts,'entrypoint_source_sha256':digest(source),'training_started':False,'new_business_runs':0,'missing_files_not_fabricated':True,'synthetic_or_unverified_attachments_not_materialized':True,'files':aliases}
    (OUT/'REPLAY_INPUT_MANIFEST.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(counts))


if __name__=='__main__':main()
