"""Freeze explicit evidence/training members after all producers have stopped."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[3]
DATA=ROOT/'output/20261027_wrd_main_v10'
GAP=ROOT/'output/20261030_wrd_gap08'
DEL=ROOT/'output/20261030_wrd_gap08_delivery'
BASE=ROOT/'output/wrd07root02'
POLICY=DEL/'secret_scan_diagnostics'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode())

def main():
 assert load(GAP/'MAIN569_QA.json')['status']=='PASS'
 assert load(GAP/'CANONICAL_ARRAYS08_QA.json')['status'].startswith('PASS')
 assert load(GAP/'corpus_independent/ROOT_PEER_QA.json')['status'].startswith('PASS')
 assert load(GAP/'process_bank03/INDEPENDENT_TOKEN_AND_SCOPE_QA.json')['status'].startswith('PASS')
 entries={};aliases=[];exports=[]
 def add(name,p,category,public=None):
  p=Path(p).resolve();assert p.is_file()and name not in entries
  assert not any(x in p.parts for x in ['__pycache__','.git','private','local_delivery_key'])
  assert p.suffix!='.pyc'
  entries[name]={'path':name,'source':str(p),'bytes':p.stat().st_size,'sha256':sha(p),'category':category}
  aliases.append({'original_absolute_path':str(p),'archive_path':name,'sha256':sha(p)})
  if public:exports.append({'archive_path':name,'path':public,'root_reviewed_public':True})
 def tree(prefix,p,category):
  for q in sorted(p.rglob('*')):
   if q.is_file()and '__pycache__'not in q.parts and q.suffix!='.pyc':add(prefix+'/'+q.relative_to(p).as_posix(),q,category)
 for n in ['TRAINING_MANIFEST.json','ACTUAL_DATA_STATISTICS.json']:add(n,DATA/n,'TRAINING',n)
 tree('compiled/gap08_process_01',DATA/'compiled/gap08_process_01','TRAINING')
 tree('canonical_arrays08',DATA/'canonical_arrays08','CANONICAL_ARRAY')
 tree('evidence08/gap08',GAP,'CONTROLLED_AUDIT')
 tree('source_tooling/wrd_gap08',ROOT/'research/data_prep/wrd_gap08','TOOLING')
 tree('design_reference/gap_plan',ROOT/'research/plans/20261030_wrd_gap_completion','DESIGN')
 for n in ['A_B_MODULES.md','PIPELINE.md']:add('design_reference/'+n,ROOT/'research/designs'/n,'DESIGN')
 for prefix,p in [('design_reference/history47',ROOT/'research/designs/history/5.0.47/gap08_20261030'),('design_reference/history48_start',ROOT/'research/designs/history/5.0.48/gap08_before_final_summary'),('design_reference/history48_URL_policy',ROOT/'research/designs/history/5.0.48/gap08_encrypted_archival_policy')]:tree(prefix,p,'DESIGN')
 add('design_reference/MEMORY08.md',ROOT/'research/memory/2026-10-30_wrd_gap08_processing.md','DESIGN')
 add('quality08/REDACTION_MARKER_CANARIES08.json',DEL/'REDACTION_MARKER_CANARIES08.json','QA')
 for n in ['ENCRYPTED_AUDIT_URL_EXCEPTIONS_PROPOSED.json','ENCRYPTED_AUDIT_URL_POLICY_CONTRACT.md','URL_EXCEPTION_CANARIES_QA.json','URL_POLICY_PREPARATION_RECEIPT.json','SIGNED_URL_DIAGNOSTICS.json']:
  add('quality08/URL_policy/'+n,POLICY/n,'QA',('ENCRYPTED_AUDIT_URL_POLICY.md' if n.endswith('_CONTRACT.md') else 'URL_EXCEPTION_CANARIES_QA.json' if n=='URL_EXCEPTION_CANARIES_QA.json' else None))
 public_refs={
  'evidence08/gap08/REPORT.md':'RECOVERY_REPORT.md',
  'design_reference/gap_plan/TRAINING_PLAN_08.md':'TRAINING_PLAN.md',
  'evidence08/gap08/MAIN569_QA.json':'MAIN569_QA.json',
  'evidence08/gap08/CANONICAL_ARRAYS08_QA.json':'CANONICAL_ARRAYS08_QA.json',
  'evidence08/gap08/FULL_SOURCE_SCOPE_QA08.json':'FULL_SOURCE_SCOPE_QA08.json',
  'evidence08/gap08/CURRENT_DATA_AND_EXPOSURE08.json':'CURRENT_DATA_AND_EXPOSURE08.json',
  'evidence08/gap08/process_bank03/INDEPENDENT_TOKEN_AND_SCOPE_QA.json':'NEW17_INDEPENDENT_QA.json',
  'evidence08/gap08/corpus_independent/ROOT_PEER_QA.json':'CORPUS_INDEPENDENT_QA.json',
  'evidence08/gap08/semantic_peer/ACTUAL_CORRECTED_DOCX_INDEPENDENT_QA.json':'DOCX_SOURCE_CORRECTIONS_QA.json',
  'evidence08/gap08/semantic_peer_html/PEER.json':'RESOURCE_REPAIR_PEER_QA.json',
  'evidence08/gap08/WITHIN_STATE_RETRY_AUDIT08.json':'WITHIN_STATE_RETRY_AUDIT08.json',
  'evidence08/gap08/corpus/SUMMARY.json':'CORPUS_BASE01_SUMMARY.json',
  'evidence08/gap08/corpus/DIRECT_QA_AND_OVERLAY02.json':'CORPUS_DIRECT_QA_AND_OVERLAY02.json',
  'evidence08/gap08/lineage/RECOVERY_SUMMARY.json':'LINEAGE196_SUMMARY.json',
  'evidence08/gap08/corpus_independent/ROOT_PEER_QA.json':'CORPUS_INDEPENDENT_QA.json',
 }
 for name,public in public_refs.items():assert name in entries;exports.append({'archive_path':name,'path':public,'root_reviewed_public':True})
 for name,p,public in [
  ('tooling/merge_delta08.py',ROOT/'research/data_prep/wrd_gap08/merge_delta08.py','tooling/merge_delta08.py'),
  ('tooling/checkpoint_loader.py',ROOT/'research/data_prep/wrd_main_v10/verify_main05.py','tooling/checkpoint_loader.py'),
  ('tooling/restore_checkpoint.py',ROOT/'output/20261025_wrd_training_dataset/git_release/dataset/20261029_v10_checkpoint05/tooling/restore_checkpoint.py','tooling/restore_checkpoint.py')]:add(name,p,'TOOLING',public)
 restore_sha=sha(ROOT/'output/20261025_wrd_training_dataset/git_release/dataset/20261029_v10_checkpoint05/tooling/restore_checkpoint.py')
 readme=f'''# WRD实际数据检查点08

本次是实际数据、原件与训练数组交付，不是只有候选清单。完整自主训练仍NOT_READY，未训练。

- 默认主集569目标／177562监督／3496949序列tokens；484≤16K＋85在16–32K。
- 契约436＋过程133；新增17个资源／修订组件26888监督，原R新正loss0，5条新作者R单列226。
- 22坏代码区间精确mask0，初版错误测试整条隔离。原程序、原思考、工具、失败和修订均在认证audit实体内保全。
- 原件账1871 native／34616 owner，另1536 provider组；1871原native和2990原API carrier齐全，781旧缺件exactSHA恢复。保护数据不作默认训练。
- [具体训练计划](TRAINING_PLAN.md)、[实际处理报告](RECOVERY_REPORT.md)、[实际数据统计](ACTUAL_DATA_STATISTICS.json)。
- 3份潜在敏感URL原始载体仅保全于加密审计包，禁止明文导出与默认训练；有限例外按源SHA、匹配SHA、层、次数绑定，密钥不入Git，其他凭据检查仍无条件拒绝。

## 还原与读取

先按检查点05、06、07的README恢复真实07合并根。再下载本目录LFS实际实体，不能只取LFS pointer。本地原AES密钥沿用，密钥不在Git，不要求重新生成。

```text
python tooling/merge_delta08.py --base <RESTORED07_ROOT> --cipher controlled/wrd-v10-delta08.tar.gz.aesgcm --receipt ENCRYPTED_DELIVERY_REPORT.json --key <EXISTING_LOCAL_KEY> --delta-out <NEW_DELTA08_DIR> --out <NEW_MERGED08_DIR> --restore-tool tooling/restore_checkpoint.py --restore-tool-sha256 {restore_sha}
```

只读取新合并根的TRAINING_MANIFEST.json.actual_train_files。标准loader生成input_ids／attention_mask／labels／loss_weights；或用canonical_arrays08/binary_loader.py及ARRAY_INDEX08.json读取相同569行、1707真实数组。旧行内binary_arrays字段属legacy，不默认跟随。不得通配audit、候选、旧准备或整个还原目录训练。

08合并保留旧冲突版本到history/pre_delta08，旧分片不改。实际根还原及远端字节回读状态以本目录CHECKPOINT_QA.json和REMOTE_VERIFICATION.json为准；生成加密receipt本身不证明上传或模型效果。

## 适用边界

原226／H12／static评测隔离。56新恢复原R共52823字符来自正式评测，保全audit且loss0。新增17是局部资源和修订子能力，含已有全文的重试，不是17独立任务或完整skills。KEEP、自主A—D和独立学生dev/test数组仍0。14B主／8B对照组件候选62／最多130更新，Spark训练未验机，无权重加载或训练。
'''
 rp=DEL/'prepared_public/README_DATA08.md';rp.parent.mkdir(parents=True,exist_ok=True);rp.write_bytes(readme.encode())
 add('quality08/README_DATA08.md',rp,'QA','README.md')
 alias=DEL/'EVIDENCE_PATH_ALIASES08.json';save(alias,{'schema':'wrd-original-source-to-restored08-paths','aliases':aliases,'audit_never_default_training':True})
 add('EVIDENCE_PATH_ALIASES08.json',alias,'QA')
 m=load(DATA/'TRAINING_MANIFEST.json')
 policy=load(POLICY/'ENCRYPTED_AUDIT_URL_EXCEPTIONS_PROPOSED.json')
 policy_list=policy['encrypted_audit_url_exceptions']
 policy_sha=hashlib.sha256(json.dumps(policy_list,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
 assert policy_sha==policy['policy_sha256']=='0c54b072cebe54a2c84d98005c25ce8f6bdd2aa4b78cc84924b66f63a27622fc'
 allow={'schema':'wrd-delta08-root-frozen-allowlist-v1','base_checkpoint_required':'05_plus_06_plus_07_authenticated_merged_root',
  'base_payload_manifest_sha256':sha(BASE/'PAYLOAD_MANIFEST.json'),'base_training_manifest_sha256':sha(BASE/'TRAINING_MANIFEST.json'),
  'current_training_manifest_sha256':sha(DATA/'TRAINING_MANIFEST.json'),'canonical_index_relative_path':'canonical_arrays08/ARRAY_INDEX08.json',
  'canonical_pin_relative_path':'canonical_arrays08/INDEX_PIN08.json','canonical_index_sha256':sha(DATA/'canonical_arrays08/ARRAY_INDEX08.json'),
  'encrypted_audit_url_policy':policy['encrypted_audit_url_policy'],'encrypted_audit_url_exceptions':policy_list,
  'files':list(entries.values()),'public_exports':exports,'actual_counts':m['actual_counts'],'training_started':False,'is_training_launcher':False}
 path=DEL/'ROOT_ALLOWLIST08_03.json';assert not path.exists();save(path,allow)
 freeze={'status':'ROOT_FROZEN_ALLOWLIST_APPROVED_FOR_PACKAGE08','allowlist_sha256':sha(path),
  **{k:allow[k]for k in ['base_payload_manifest_sha256','base_training_manifest_sha256','current_training_manifest_sha256','canonical_index_sha256']},
  'root_approval_scope':'Authenticated data delivery only; original226/H12/static isolation, no model training or new business collection',
  'encrypted_audit_url_policy':policy['encrypted_audit_url_policy'],'encrypted_audit_url_exceptions_sha256':policy_sha,
  'source_code_sha256':sha(__file__),'training_started':False}
 save(DEL/'ROOT_FREEZE_RECEIPT08_03.json',freeze)
 print(json.dumps({'frozen_files':len(entries),'source_bytes':sum(x['bytes']for x in entries.values()),'allowlist_sha256':sha(path),'public_exports':len(exports)},ensure_ascii=False))

if __name__=='__main__':main()
