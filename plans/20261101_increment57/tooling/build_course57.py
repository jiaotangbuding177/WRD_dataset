"""Freeze one-pass active57 course, preserving source masks and weights.

Reads actual features; never calls a model, forward, backward, or optimizer.
"""
from pathlib import Path
from decimal import Decimal
from array import array
import argparse
import collections
import hashlib
import importlib.util
import json
import random
import shutil
import sys

SEED=20261101

def load(path):return json.loads(Path(path).read_text(encoding="utf-8-sig"))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,value):Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def require(value,message):
    if not value:raise ValueError(message)
def token_sha(ids):
    a=array("I",ids);require(a.itemsize==4,"UNSUPPORTED_UINT32")
    if sys.byteorder!="little":a.byteswap()
    return hashlib.sha256(a.tobytes()).hexdigest()

def order_source_balanced(records):
    groups=collections.defaultdict(list)
    for record in records:groups[record["ordering_group"]].append(record)
    rng=random.Random(SEED);keys=sorted(groups);rng.shuffle(keys)
    for key in keys:
        groups[key].sort(key=lambda r:r["id"]);rng.shuffle(groups[key])
    result=[];positions={k:0 for k in keys}
    while len(result)<len(records):
        for key in keys:
            index=positions[key]
            if index<len(groups[key]):result.append(groups[key][index]);positions[key]+=1
    return result

def summarise(records):
    pools=collections.Counter();components=collections.Counter();stages=collections.Counter()
    for row in records:
        pools[row["pool"]]+=1;components.update(row["positive_by_component"])
        stage=row["stage"].split("_",1)[0];stages[stage if stage in {"A","B","C","D"} else "historical_workflow_R"]+=1
    mass=sum((Decimal(r["weighted_mass"]) for r in records),Decimal(0));synth=sum((Decimal(r["weighted_mass"]) for r in records if r["pool"]=="synthetic"),Decimal(0))
    return {"unique_targets":len({r["id"] for r in records}),"sequence_exposures":len(records),
        "sequence_tokens_unpadded":sum(r["sequence_tokens"] for r in records),"positive_tokens_exposed":sum(r["positive_tokens"] for r in records),
        "valid_shifted_target_denominator":sum(r["valid_shifted_target_count"] for r in records),
        "weighted_mass_exposed":str(mass),"synthetic_weighted_mass":str(synth),
        "synthetic_fraction_of_weighted_mass":float(synth/mass) if mass else 0,
        "exposure_count_by_pool":dict(pools),"positive_by_component":dict(components),"by_stage":dict(stages),
        "le16k_exposures":sum(r["sequence_tokens"]<=16384 for r in records),
        "long16to32k_exposures":sum(16384<r["sequence_tokens"]<=32768 for r in records)}

def make_phase(records,name,acc,global_offset):
    ordered=order_source_balanced(records);steps=[]
    for start in range(0,len(ordered),acc):
        group=ordered[start:start+acc];summary=summarise(group)
        steps.append({"phase_step_one_based":len(steps)+1,"global_step_one_based":global_offset+len(steps)+1,
            "microbatches":group,"actual_accumulation_count":len(group),
            "valid_shifted_target_denominator":summary["valid_shifted_target_denominator"],
            "weighted_mass":summary["weighted_mass_exposed"],"synthetic_weighted_mass":summary["synthetic_weighted_mass"],
            "synthetic_fraction_of_weighted_mass":summary["synthetic_fraction_of_weighted_mass"],
            "has_existing_process":any(r["pool"]=="real_process" for r in group),
            "has_new_reviewed_process":any(r["pool"]=="increment_process" for r in group)})
    return {"name":name,"accumulation_max":acc,"microbatch":1,"single_pass":True,"repeat_views_to_fill_tail":False,
        "flush_final_partial_accumulation":True,"optimizer_updates_candidate":len(steps),"summary":summarise(ordered),"steps":steps}

def main():
    require(not sys.flags.optimize,"OPTIMIZED_PYTHON_REJECTED")
    parser=argparse.ArgumentParser();parser.add_argument("--root",type=Path,required=True);parser.add_argument("--base-root",type=Path,required=True)
    parser.add_argument("--package11-root",type=Path,required=True);parser.add_argument("--config55",type=Path,required=True)
    args=parser.parse_args();root=args.root.resolve()
    require(not (root/"COURSE57.json").exists() and not (root/"CONFIG57.json").exists(),"COURSE_ALREADY_FROZEN")
    spec=importlib.util.spec_from_file_location("wrd57_active_course_loader",root/"tooling/active_loader57.py")
    loader=importlib.util.module_from_spec(spec);spec.loader.exec_module(loader)
    manifest=load(root/"ACTIVE_DATASET_MANIFEST57.json")
    components=load(loader.verified(root,manifest["source_component_map"]))["source_to_component"]
    rows={}
    for profile in manifest["profiles"]:
        records=[]
        for item in loader.iter_features(root,args.base_root,args.package11_root,profile=profile,with_metadata=True):
            f=item["features"];sources=[s for s in item["source_ids"] if s in components]
            ordering_group="enterprise:"+"|".join(sorted({components[s] for s in sources})) if sources else "declared:"+str(item["source_group_id"])
            positive=[v for v in f["labels"] if v!=-100];mass=sum((Decimal(str(w)) for l,w in zip(f["labels"],f["loss_weights"]) if l!=-100),Decimal(0))
            # Component counts come from the pinned actual compiled row ledger.
            records.append({"id":item["id"],"pool":item["pool"],"stage":item["stage"],"bank":item["bank"],
                "ordering_group":ordering_group,"sequence_tokens":len(f["input_ids"]),"positive_tokens":len(positive),
                "valid_shifted_target_count":sum(v!=-100 for v in f["labels"][1:]),"weighted_mass":str(mass),
                "positive_token_ids_sha256_u32le":token_sha(positive)})
        ledger={r["id"]:r for r in load(root/"ACTIVE_TARGET_LEDGER57.json")["profiles"][profile]}
        for record in records:
            entry=ledger[record["id"]]
            require(record["positive_token_ids_sha256_u32le"]==entry["positive_token_ids_sha256_u32le"] and record["positive_tokens"]==entry["positive_tokens"],"ACTUAL_FEATURES_LEDGER_DIFFER")
            record["positive_by_component"]=entry["positive_by_component"]
        require(len(records)==manifest["actual_counts"][profile]["unique_targets"],"ACTIVE_COURSE_COUNT_MISMATCH")
        rows[profile]=records
    course={"schema":"wrd57-active-single-pass-full-pipeline-course-not-launcher","design_revision":"5.0.57","seed":SEED,
        "ordering":"each phase: ID sort inside source/declared-family groups, deterministic shuffle groups and each group with Random(seed), then round-robin without repetition",
        "same_adapter_and_optimizer_across_phases":True,"profiles_are_mutually_exclusive":True,"profiles":{},"training_started":False}
    for profile,records in rows.items():
        contract=[r for r in records if r["pool"]=="contract_optional"];process=[r for r in records if r["pool"]!="contract_optional"]
        p1=make_phase(contract,"contract",16,0);p2=make_phase(process,"process",4,p1["optimizer_updates_candidate"])
        all_ordered=[r for phase in [p1,p2] for step in phase["steps"] for r in step["microbatches"]]
        require(len(all_ordered)==len({r["id"] for r in all_ordered})==len(records),"COURSE_REPEATS_OR_DROPS_ACTIVE_TARGET")
        require(not set(manifest["excluded_original_primary_ids"])&{r["id"] for r in all_ordered},"REVOKED_ID_IN_NEW_COURSE")
        steps=p1["steps"]+p2["steps"];fractions=[s["synthetic_fraction_of_weighted_mass"] for s in steps]
        total=summarise(all_ordered)
        require(total["synthetic_fraction_of_weighted_mass"]<=0.2 and p2["summary"]["synthetic_fraction_of_weighted_mass"]<=0.2,"GLOBAL_SYNTHETIC_EFFECTIVE_MASS_CAP")
        course["profiles"][profile]={"active_manifest_sha256":sha(root/"ACTIVE_DATASET_MANIFEST57.json"),"phases":[p1,p2],
            "summary":total,"optimizer_updates_candidate":len(steps),"last_partial_contract":len(p1["steps"][-1]["microbatches"]),
            "last_partial_process":len(p2["steps"][-1]["microbatches"]),
            "batch_mass_audit":{"local_synthetic_fraction_over20percent_batches":sum(v>0.2 for v in fractions),
                "local_synthetic_fraction100percent_batches":sum(v==1 for v in fractions),"max_local_synthetic_fraction":max(fractions),
                "process_batches_without_existing_or_new_process":sum(not s["has_existing_process"] and not s["has_new_reviewed_process"] for s in p2["steps"]),
                "global20percent_is_not_a_local_batch_cap_or_gradient_norm_claim":True}}
    profiles=list(course["profiles"])
    sequence=lambda profile:[[r["id"] for r in step["microbatches"]] for phase in course["profiles"][profile]["phases"] for step in phase["steps"]]
    require(sequence(profiles[0])==sequence(profiles[1]),"CROSS_PROFILE_BATCH_IDS_NOT_IDENTICAL")
    byid=lambda profile:{r["id"]:r["positive_token_ids_sha256_u32le"] for r in rows[profile]}
    require(byid(profiles[0])==byid(profiles[1]),"CROSS_PROFILE_POSITIVE_PAYLOAD_DIFFERS")
    inherited=load(args.config55)
    config={key:inherited[key] for key in ["models","base_dtype","base_frozen","embedding_and_lm_head_frozen","preserve_gradient_through_frozen_layers",
        "lora","optimizer","scheduler","gradient_checkpointing","checkpoint_use_reentrant","use_cache","max_training_sequence_length",
        "silent_truncation","cross_example_packing","retemplate_compiled_input_ids","use_existing_token_masks_and_weights","loss"]}
    summary=course["profiles"][manifest["default_profile"]]
    config.update({"schema":"wrd57-active-single-pass-sft-config-not-launcher","design_revision":"5.0.57","seed":SEED,"microbatch":1,
        "default_profile":manifest["default_profile"],"profiles_are_mutually_exclusive":True,"dataset_manifest":"ACTIVE_DATASET_MANIFEST57.json",
        "dataset_manifest_sha256":sha(root/"ACTIVE_DATASET_MANIFEST57.json"),"dataset_loader":"tooling/active_loader57.py",
        "course_file":"COURSE57.json","same_adapter_and_optimizer_across_phases":True,"repeat_tail_views":False,
        "phases":[{"name":p["name"],"unique_targets":p["summary"]["unique_targets"],"sequence_exposures":p["summary"]["sequence_exposures"],
            "accumulation_max":p["accumulation_max"],"optimizer_updates_candidate":p["optimizer_updates_candidate"],"last_partial_flushed":True} for p in summary["phases"]],
        "candidate_optimizer_updates":summary["optimizer_updates_candidate"],"unique_targets":summary["summary"]["unique_targets"],
        "candidate_sequence_exposures":summary["summary"]["sequence_exposures"],"positive_tokens_exposed":summary["summary"]["positive_tokens_exposed"],
        "candidate_checkpoint_global_steps":[p["steps"][-1]["global_step_one_based"] for p in summary["phases"]],
        "inherited_55_config_ref":{"path":str(args.config55),"sha256":sha(args.config55)},
        "old55_schedule_must_not_be_used_for_this_active_whitelist":True,"global_aux_effective_mass_cap":0.2,
        "local_batches_over20percent_are_recorded_not_suppressed_or_claimed_compliant":True,
        "training_execution_authorized":False,"training_started":False,"weights_loaded":False,"optimizer_updates_executed":0})
    write(root/"COURSE57.json",course);write(root/"CONFIG57.json",config)
    shutil.copyfile(Path(__file__),root/"tooling/build_course57.py")
    qa={"schema":"wrd57-real-feature-single-pass-course-QA","status":"PASS_ACTIVE_SINGLE_PASS_COURSE_IDENTICAL_BATCH_IDS_NO_REVOKED_OR_REPEATED_TARGETS",
        "actual_four_features_reread_to_count_course":True,"profiles":{p:{"summary":v["summary"],"optimizer_updates_candidate":v["optimizer_updates_candidate"],
            "phase_updates":[x["optimizer_updates_candidate"] for x in v["phases"]],"phase_tail_microbatches":[v["last_partial_contract"],v["last_partial_process"]],
            "batch_mass_audit":v["batch_mass_audit"]} for p,v in course["profiles"].items()},
        "cross_profile_each_batch_ID_order_identical":True,"each_active_ID_exactly_once":True,"excluded44_IDs_absent":True,
        "global_synthetic_mass_cap_passed_both_full_and_process_phase":True,
        "model_LoRA_loss_and_scheduler_values_unchanged_from55":True,
        "course_sha256":sha(root/"COURSE57.json"),"config_sha256":sha(root/"CONFIG57.json"),"source_script_sha256":sha(Path(__file__)),
        "model_weights_loaded":False,"forward_or_backward_executed":False,"optimizer_updates_executed":0,"training_started":False}
    write(root/"COURSE_QA57.json",qa)
    print(json.dumps({"status":qa["status"],"profiles":qa["profiles"],"course_sha256":qa["course_sha256"],"config_sha256":qa["config_sha256"],"qa_sha256":sha(root/"COURSE_QA57.json")}))

if __name__=="__main__":main()
