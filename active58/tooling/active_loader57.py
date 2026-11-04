"""Portable stdlib active-data selector. No model imports or training.

Explicitly selects surviving old targets and reviewed incremental banks. The
old immutable curriculum loader is imported only after its fixed SHA matches.
Restored payload Python modules are never executed. Python -O is rejected.
"""
from pathlib import Path, PurePosixPath
from array import array
import gzip
import hashlib
import importlib.util
import json
import math
import sys

IMMUTABLE_LOADER_SHA256="a2d5f03fb9dec90763b238c5c499199176f1eddbf54b935475274981bc952c1c"
POOLS={"contract_optional","real_process","synthetic","increment_process"}

def require(ok,message):
    if not ok:raise ValueError(message)

def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as stream:
        for data in iter(lambda:stream.read(1048576),b""):h.update(data)
    return h.hexdigest()

def load(path):return json.loads(Path(path).read_text(encoding="utf-8-sig"))

def safe(root,name):
    require(isinstance(name,str) and name and not any(c in name for c in "\\:\x00\r\n"),"INVALID_RELATIVE_REFERENCE")
    relative=PurePosixPath(name)
    require(not relative.is_absolute() and relative.as_posix()==name and ".." not in relative.parts,"UNSAFE_REFERENCE")
    require(all(v not in {"",".",".."} and not v.endswith((" ",".")) for v in relative.parts),"UNSAFE_PATH_PART")
    root=Path(root).resolve();target=root.joinpath(*relative.parts)
    require(target.resolve().is_relative_to(root),"REFERENCE_ESCAPES_ROOT")
    for parent in [target,*target.parents]:
        require(not parent.is_symlink() and not (hasattr(parent,"is_junction") and parent.is_junction()),"LINK_REFERENCE_REJECTED")
        if parent==root:break
    return target

def verified(root,ref):
    path=safe(root,ref["path"])
    require(path.is_file() and path.stat().st_size==ref["bytes"] and sha(path)==ref["sha256"],"FILE_PIN_MISMATCH")
    return path

def immutable_module(path):
    require(not sys.flags.optimize,"OPTIMIZED_PYTHON_DISABLES_IMMUTABLE_LOADER_ASSERTIONS")
    path=Path(path).resolve()
    require(path.is_file() and not path.is_symlink() and sha(path)==IMMUTABLE_LOADER_SHA256,"UNTRUSTED_IMMUTABLE_LOADER")
    spec=importlib.util.spec_from_file_location("wrd57_reviewed_immutable11",path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def validated_manifest(root,expected_manifest_sha256=None):
    require(not sys.flags.optimize,"OPTIMIZED_PYTHON_REJECTED")
    root=Path(root).resolve();path=root/"ACTIVE_DATASET_MANIFEST57.json";pin=load(root/"ACTIVE_DATASET_PIN57.json")
    require(path.is_file() and path.stat().st_size==pin["manifest_bytes"] and sha(path)==pin["manifest_sha256"],"ACTIVE_MANIFEST_PIN_MISMATCH")
    if expected_manifest_sha256 is not None:require(sha(path)==expected_manifest_sha256,"EXPECTED_ACTIVE_MANIFEST_MISMATCH")
    require(sha(Path(__file__))==pin["active_loader_sha256"],"ACTIVE_LOADER_PIN_MISMATCH")
    manifest=load(path)
    require(manifest["schema"]=="wrd57-active-combined-selector-v1","UNKNOWN_ACTIVE_SCHEMA")
    require(manifest["profiles_are_mutually_exclusive"],"PROFILES_MUST_BE_EXCLUSIVE")
    boundary=load(verified(root,manifest["root_boundary"]))
    excluded=set(manifest["excluded_original_primary_ids"])
    require(excluded=={r["id"] for r in boundary["rows_to_exclude"]} and len(excluded)==44,"ROOT_BOUNDARY_EXCLUSIONS_DIFFER")
    selected=manifest["selected_existing_ids"]
    require(set(selected)=={"contract_optional","real_process","synthetic"},"UNEXPECTED_EXISTING_POOLS")
    all_selected=[v for values in selected.values() for v in values]
    require(len(all_selected)==len(set(all_selected)) and not excluded&set(all_selected),"INVALID_ACTIVE_EXISTING_IDS")
    freeze=load(verified(root,manifest["source_freeze"]))
    train={r["group_id"]:set(r["source_ids"]) for r in freeze["groups"] if r["role"]=="TRAIN-MINING"}
    increment_ids=[]
    for bank in manifest["incremental_banks"]:
        require(bank["target_count"]==len(bank["active_ids"])==len(set(bank["active_ids"])),"INCREMENT_BANK_CARDINALITY")
        require(set(bank["frozen_TRAIN_source_groups"])<=set(train),"INCREMENT_BANK_GROUP_NOT_FROZEN_TRAIN")
        actual_source_union={s for g in bank["frozen_TRAIN_source_groups"] for s in train[g]}
        require(set(bank["frozen_TRAIN_source_ids"])<=actual_source_union,"INCREMENT_BANK_SOURCE_NOT_FROZEN_TRAIN")
        increment_ids.extend(bank["active_ids"])
    require(len(increment_ids)==len(set(increment_ids)) and not (set(all_selected)|excluded)&set(increment_ids),"INCREMENT_ID_COLLISION")
    require(all(v["unique_targets"]==len(all_selected)+len(increment_ids) for v in manifest["actual_counts"].values()),"DECLARED_ACTIVE_CARDINALITY")
    return root,manifest

def validate_features(row,feature):
    ids=feature["input_ids"];labels=feature["labels"];weights=feature["loss_weights"];attention=feature["attention_mask"]
    require(len(ids)==len(labels)==len(weights)==len(attention) and len(ids)>1,"FOUR_FEATURE_LENGTH_MISMATCH")
    require(labels[0]==-100 and weights[0]==0,"UNTRAINABLE_POSITION_ZERO_TARGET")
    positive=0
    for token,label,weight,mask in zip(ids,labels,weights,attention):
        require(type(token)is int and token>=0 and mask==1,"INVALID_UNPADDED_INPUT_OR_ATTENTION")
        require(math.isfinite(weight) and weight>=0,"INVALID_TOKEN_WEIGHT")
        if label==-100:require(weight==0,"IGNORED_TARGET_HAS_WEIGHT")
        else:require(label==token and weight>0,"INVALID_POSITIVE_TARGET");positive+=1
    require(positive>0 and positive==row["supervised_tokens"],"POSITIVE_TARGET_COUNT_MISMATCH")
    require(sum(b-a for a,b,_,_ in row["supervision_spans"])==positive,"SPAN_COUNTS_DIFFER")
    return positive

def iter_records(root,base_root,package11_root,*,profile="budget_projection",pools=None,
                 immutable_loader_path=None,expected_manifest_sha256=None):
    """Yield (pool, source_root, binary_entry, compiled_row) for active IDs only."""
    root,m=validated_manifest(root,expected_manifest_sha256)
    require(profile in m["profiles"],"UNKNOWN_PROFILE")
    chosen=POOLS if pools is None else set(pools)
    require(chosen<=POOLS,"UNKNOWN_ACTIVE_POOL")
    if immutable_loader_path is None:immutable_loader_path=Path(__file__).with_name("immutable_curriculum_loader11.py")
    old=immutable_module(immutable_loader_path)
    profile_root=safe(package11_root,m["profiles"][profile]["package11_relative_path"])
    require(sha(profile_root/"CURRICULUM_MANIFEST11.json")==m["profiles"][profile]["manifest_sha256"],"PROFILE_MANIFEST_MISMATCH")
    selections={k:set(v) for k,v in m["selected_existing_ids"].items()}
    excluded=set(m["excluded_original_primary_ids"]);seen=set();seen_old=set();selected_seen={k:set() for k in selections}
    # Read only immutable reviewed JSON/arrays. Excluded rows are never yielded.
    for pool,source,entry,row in old.iter_records(profile_root,base_root,pools=("contract_optional","real_process","synthetic")):
        rid=row["id"];require(rid not in seen_old,"DUPLICATE_OLD_TARGET_ID");seen_old.add(rid)
        if rid in excluded:
            require(pool!="synthetic","AUXILIARY_ID_IN_PRIMARY_EXCLUSION");continue
        require(rid in selections[pool],"UNDECLARED_EXISTING_TARGET_IN_ACTIVE_SELECTOR")
        selected_seen[pool].add(rid);seen.add(rid)
        if pool in chosen:yield pool,source,entry,row
    require(all(selected_seen[k]==selections[k] for k in selections),"SELECTED_EXISTING_IDS_NOT_FOUND")
    require(len(seen_old)==m["legacy_available_targets_before_exclusion"],"OLD_INPUT_CARDINALITY_CHANGED")
    freeze=load(verified(root,m["source_freeze"]))
    train={r["group_id"]:set(r["source_ids"]) for r in freeze["groups"] if r["role"]=="TRAIN-MINING"}
    for bank in m["incremental_banks"]:
        index=load(verified(root,bank["array_index"]))
        entries={e["id"]:e for e in index["records"]}
        require(len(entries)==len(index["records"])==bank["target_count"],"BANK_INDEX_CARDINALITY")
        allowed=set(bank["active_ids"]);found=set()
        for ref in bank["train_files"]:
            path=verified(root,ref)
            with gzip.open(path,"rt",encoding="utf-8-sig") as stream:
                for ordinal,line in enumerate(stream):
                    if not line.strip():continue
                    row=json.loads(line);rid=row["id"]
                    require(rid in allowed and rid not in seen and rid not in excluded,"DUPLICATE_OR_UNDECLARED_INCREMENT_TARGET")
                    entry=entries[rid]
                    require(entry["source_train_file"]==ref["path"] and entry["source_record_index"]==ordinal,"BANK_RECORD_INDEX_MISMATCH")
                    require(set(row["source_ids"])<=set(bank["frozen_TRAIN_source_ids"]),"INCREMENT_SOURCE_OUTSIDE_FROZEN_TRAIN")
                    require(row["source_group_id"] in bank["frozen_TRAIN_source_groups"],"INCREMENT_GROUP_OUTSIDE_FROZEN_TRAIN")
                    require(set(row["source_ids"])<=train[row["source_group_id"]],"ROW_SOURCE_NOT_IN_ITS_FROZEN_GROUP")
                    require(row["split"]=="train","NONTRAIN_INCREMENT_ROW")
                    found.add(rid);seen.add(rid)
                    if "increment_process" in chosen:yield "increment_process",root,entry,row
        require(found==allowed and set(entries)==allowed,"UNREAD_OR_MISSING_INCREMENT_TARGET")
    require(len(seen)==m["actual_counts"][profile]["unique_targets"],"ACTIVE_CARDINALITY_MISMATCH")

def iter_features(root,base_root,package11_root,*,profile="budget_projection",pools=None,
                  immutable_loader_path=None,expected_manifest_sha256=None,use_binary=True,with_metadata=False):
    path=immutable_loader_path if immutable_loader_path is not None else Path(__file__).with_name("immutable_curriculum_loader11.py")
    old=immutable_module(path)
    for pool,source,entry,row in iter_records(root,base_root,package11_root,profile=profile,pools=pools,
            immutable_loader_path=path,expected_manifest_sha256=expected_manifest_sha256):
        feature=old.binary(source,entry,row) if use_binary else old.standard(row)
        validate_features(row,feature)
        if with_metadata:yield {"id":row["id"],"pool":pool,"stage":row["stage"],"bank":row["bank"],
            "source_ids":row.get("source_ids",[]),"source_group_id":row.get("source_group_id"),"features":feature}
        else:yield feature
