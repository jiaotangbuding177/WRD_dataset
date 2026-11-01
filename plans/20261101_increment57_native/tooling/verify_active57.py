"""Re-read a saved active57 dataset and test mask guards. Never trains."""
from pathlib import Path
from decimal import Decimal
import argparse
import collections
import copy
import hashlib
import importlib.util
import json
import subprocess
import sys

def load_module(path):
    spec=importlib.util.spec_from_file_location("wrd57_active_verify_module",path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--root",type=Path,required=True)
    parser.add_argument("--base-root",type=Path,required=True)
    parser.add_argument("--package11-root",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--optimization-guard-only",action="store_true")
    args=parser.parse_args()
    loader=load_module(args.root/"tooling/active_loader57.py")
    if args.optimization_guard_only:
        try:loader.validated_manifest(args.root)
        except ValueError as error:
            if "OPTIMIZED_PYTHON" in str(error):print("EXPECTED_OPTIMIZATION_GUARD_REJECTION");return
            raise
        raise ValueError("Optimized Python incorrectly allowed")
    if sys.flags.optimize:raise ValueError("Normal verifier requires assertions enabled")
    manifest=json.loads((args.root/"ACTIVE_DATASET_MANIFEST57.json").read_text(encoding="utf-8-sig"))
    records={};counts={}
    for profile in manifest["profiles"]:
        values=[]
        for row in loader.iter_features(args.root,args.base_root,args.package11_root,profile=profile,with_metadata=True):
            features=row["features"];positive=[v for v in features["labels"] if v!=-100]
            values.append({"id":row["id"],"pool":row["pool"],"sequence":len(features["input_ids"]),"positive":len(positive),
                "mass":sum((Decimal(str(w)) for l,w in zip(features["labels"],features["loss_weights"]) if l!=-100),Decimal(0)),
                "positive_token_hash":hashlib.sha256(json.dumps(positive,separators=(",",":")).encode()).hexdigest()})
        expected=manifest["actual_counts"][profile]
        observed={"unique_targets":len(values),"positive_tokens":sum(v["positive"] for v in values),
            "sequence_tokens":sum(v["sequence"] for v in values),"weighted_mass":str(sum((v["mass"] for v in values),Decimal(0))),
            "le16k_targets":sum(v["sequence"]<=16384 for v in values),"long16to32k_targets":sum(16384<v["sequence"]<=32768 for v in values),
            "by_pool":dict(collections.Counter(v["pool"] for v in values))}
        if any(observed[k]!=expected[k] for k in observed):raise ValueError("Saved active manifest count mismatch")
        if len({v["id"] for v in values})!=len(values):raise ValueError("Active duplicate IDs")
        records[profile]={v["id"]:v["positive_token_hash"] for v in values};counts[profile]=observed
    if len({json.dumps(v,sort_keys=True) for v in records.values()})!=1:raise ValueError("Cross-profile positive payload differs")
    row={"supervised_tokens":1,"supervision_spans":[[1,2,"A",0.25]]}
    valid={"input_ids":[1,2],"labels":[-100,2],"loss_weights":[0.0,0.25],"attention_mask":[1,1]}
    loader.validate_features(row,valid)
    negatives=[]
    for name,key,index,value in [("positive_position0","labels",0,1),("bad_label","labels",1,99),
            ("zero_weight_positive","loss_weights",1,0.0),("positive_weight_ignore","labels",1,-100),
            ("nonone_unpadded_attention","attention_mask",1,0)]:
        bad=copy.deepcopy(valid);bad[key][index]=value
        try:loader.validate_features(row,bad)
        except ValueError:negatives.append({"name":name,"rejected":True})
        else:raise ValueError("Invalid mask accepted: "+name)
    command=[sys.executable,"-O",str(Path(__file__).resolve()),"--root",str(args.root),"--base-root",str(args.base_root),
        "--package11-root",str(args.package11_root),"--out",str(args.out),"--optimization-guard-only"]
    probe=subprocess.run(command,capture_output=True,text=True)
    if probe.returncode or "EXPECTED_OPTIMIZATION_GUARD_REJECTION" not in probe.stdout:raise ValueError("Optimization guard failed")
    result={"schema":"wrd57-saved-active-dataset-independent-style-reread","status":"PASS_SAVED_ACTIVE_BOTH_PROFILES_FEATURES_AND_MASK_GUARDS",
        "actual_reread":counts,"cross_profile_positive_payload_equal":True,"negative_mask_guards":negatives,
        "python_O_actual_subprocess_rejected_before_data":True,"manifest_sha256":hashlib.sha256((args.root/"ACTIVE_DATASET_MANIFEST57.json").read_bytes()).hexdigest(),
        "verifier_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),"weights_loaded":False,"forward_or_backward":False,"training_started":False}
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":result["status"],"profiles":counts,"qa_sha256":hashlib.sha256(args.out.read_bytes()).hexdigest()}))

if __name__=="__main__":main()
