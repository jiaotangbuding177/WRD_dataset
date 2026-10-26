"""Read back the explicit v9 commit and actual remote authenticated LFS bytes."""
import argparse
import importlib.util
import json
from pathlib import Path


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--commit',required=True);args=parser.parse_args()
    root=Path(__file__).resolve().parents[3]
    spec=importlib.util.spec_from_file_location('wrd_v9_remote',root/'research/data_prep/wrd_raw_census_v7/verify_remote_index.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.OUT=root/'output/20261026_wrd_dataset_v9';module.PREFIX='dataset/20261026_v9/'
    module.PRIOR='70cd1325d8616b6d8d0459be6f1aeead50f07b77'
    module.verify(args.commit)
    path=module.OUT/'REMOTE_GIT_VERIFICATION.json';r=json.loads(path.read_text(encoding='utf-8'))
    r.update(schema_version='wrd-v9-actual-dataset-remote-readback',full_goal_main_training_ready=False,actual_data_delivered_in_authenticated_archive=True)
    path.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
