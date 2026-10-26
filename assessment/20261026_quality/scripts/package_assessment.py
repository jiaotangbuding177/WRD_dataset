"""Publish the bounded v8 assessment, never a replacement SFT dataset."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'output/20261026_wrd_quality_v8'
RELEASE = ROOT / 'output/20261025_wrd_training_dataset/git_release'
DEST = RELEASE / 'assessment/20261026_quality'


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def publish():
    review = json.loads((OUT / 'V8_SYNTHESIS_REVIEW.json').read_text(encoding='utf-8'))
    assert review['status'] == 'PASS_BOUNDED_SYNTHESIS'
    assert all(row['pass'] for row in review['checks'])
    assert digest(OUT / 'QUALITY_ASSESSMENT.md') == review['reviewed_report']['sha256']
    assert digest(OUT / 'ASSESSMENT_SUMMARY.json') == review['reviewed_summary_sha256']
    for row in review['source_pins_verified']:
        p = Path(row['path'])
        assert digest(p) == row['sha256'] and p.stat().st_size == row['bytes']
    assert not DEST.exists(), 'Do not overwrite an earlier published packet'
    DEST.mkdir(parents=True)
    public_names = {
        'QUALITY_ASSESSMENT.md', 'ASSESSMENT_SUMMARY.json', 'V8_SYNTHESIS_REVIEW.json',
        'NATIVE_QUALITY.json', 'NATIVE_COMPUTABLE_QA.json', 'NATIVE_REVIEW_SAMPLE_MANIFEST.json',
        'NATIVE_FOCUSED_REVIEW_MANIFEST.json', 'CHAIN_QUALITY.json', 'CHAIN_LOCAL_QA.json',
        'CASE_REVIEWS.jsonl', 'RAW_RECOVERABILITY.json', 'ARTIFACT_STATIC_QUALITY.json',
        'SEMANTIC_SAMPLE_PROTOCOL.json', 'LOCAL_SEMANTIC_FINDINGS.jsonl',
        'NUMERIC_CONTENT_COUNTEREXAMPLE.json', 'LITERATURE_EVIDENCE.json',
    }
    for name in sorted(public_names):
        shutil.copyfile(OUT / name, DEST / name)
    for p in sorted((OUT / 'controlled').glob('*.jsonl.gz')):
        target = DEST / 'controlled' / p.name
        target.parent.mkdir(exist_ok=True)
        shutil.copyfile(p, target)
    scripts = DEST / 'scripts'
    scripts.mkdir()
    for p in sorted(Path(__file__).parent.glob('*.py')):
        shutil.copyfile(p, scripts / p.name)
    shutil.copyfile(ROOT / 'research/data_prep/wrd_raw_census_v7/verify_remote_index.py', scripts / 'shared_v7_verify_remote_index.py')
    references = DEST / 'design_reference'
    references.mkdir()
    for name in ('A_B_MODULES.md', 'PIPELINE.md'):
        shutil.copyfile(ROOT / 'research/designs' / name, references / name)
    shutil.copyfile(ROOT / 'research/memory/2026-10-26_wrd_quality_sufficiency_v8.md', DEST / 'RESEARCH_MEMORY.md')
    (DEST / 'README.md').write_text('''# WRD数据质量与训练充分性评估v8

[完整评估](QUALITY_ASSESSMENT.md) · [结构化结论](ASSESSMENT_SUMMARY.json) · [独立综合复核](V8_SYNTHESIS_REVIEW.json) · [文件清单](MANIFEST.json)

原始规模值得认真准备领域SFT；当前尚不能保证14B独立完成完整WRD、教师等效或更低的每合格技能总成本。原226继续隔离，未训练、未加载权重、未启动新Teacher/Actor或业务复跑。

本包是已经完成的质量评估与证据，不是新SFT正文/数组或最终准入清单。32,014个非空助手位置、约1067万目标tokens不是32,014个独立完整任务；历史93/106只是窄子集。全量语义和资源祖先交集后的最终训练数仍未知，旧训练实包原样保留。

`controlled/`沿用本地证据目录名称，公开内容为质量/身份/哈希/来源/计数元数据；不是原API正文，也不是可以直接喂给模型的样本。语义原文局部窗口及修订草稿保留在本地，不复制到本包。可读思考、加密体、进度字段和可见说明分开统计。

本轮核查旧1763会话的32342目标、30438工具块；121路线链、29终包/154文件；18个固定排序局部语义窗口和20链案例（可能重叠），不能据此推算总体语义合格率。静态通过与原retain不等于运行/领域Q/完整自主成功。

`scripts/`保存实际使用的审计脚本。它们依赖原D/E/C布局及报告所绑定原件，不能只克隆元数据仓库就假装重跑原始数据审计；运行只读审计仍需按各脚本核对源路径。生成资源未执行。`design_reference/`为非执行5.0.34双稿快照，原并行消融保持其冻结5.0.33合同。

远端读取验证需在原项目布局执行 `python research/data_prep/wrd_quality_v8/verify_remote_assessment.py --commit <本次40位提交>`，对普通Git与LFS真实字节分别核SHA；不会启动训练。原始数据入口沿用仓库 `census/20261026/RAW_DATA_LOCATIONS.md`。
''', encoding='utf-8')
    rows = []
    for p in sorted(DEST.rglob('*')):
        if p.is_file():
            rows.append({'path': p.relative_to(DEST).as_posix(), 'bytes': p.stat().st_size, 'sha256': digest(p)})
    assert not any('SEMANTIC_SAMPLE_WINDOWS' in row['path'] or row['path'].startswith('history/') for row in rows)
    manifest = {
        'schema_version': 'wrd-quality-assessment-v8-manifest-1.0',
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'kind': 'completed_quality_assessment_not_new_SFT_compilation',
        'payload_files': len(rows), 'payload_bytes': sum(row['bytes'] for row in rows),
        'training_started': False, 'weights_loaded': False, 'new_business_runs': 0,
        'original226_training_boundary_unchanged': True,
        'old_training_arrays_and_manifests_unchanged': True,
        'final_new_admitted_training_count_established': False,
        'report_sha256': review['reviewed_report']['sha256'],
        'summary_sha256': review['reviewed_summary_sha256'],
        'independent_synthesis_check_count': len(review['checks']),
        'private_raw_semantic_windows_excluded': True, 'files': rows,
    }
    (DEST / 'MANIFEST.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    readme = RELEASE / 'README.md'
    readme.write_text('''# 最新评估：数据质量、数据量与14B目标可达性v8

[完整质量评估与调研](assessment/20261026_quality/QUALITY_ASSESSMENT.md) · [本轮证据包入口](assessment/20261026_quality/README.md) · [独立复核](assessment/20261026_quality/V8_SYNTHESIS_REVIEW.json)

全旧1763会话、32342助手位置与30438工具块已查，32014非空目标约1067万目标tokens；29最终技能都有过程档案，113条原反馈后实际读取连接。原规模值得领域SFT准备；输入/schema保真、监督正确性、独立来源与完整自主协调仍有明确缺口，不能承诺教师等效或降本。原226继续隔离，未启动训练。

本次是完成的质量评估，不是新全量SFT正文、mask或最终准入交付；旧数组与manifest保持。报告分别披露全量可计算检查、局部语义评估和文献结论，不以32342步骤或磁盘GB充作独立工作流数量。

---

''' + readme.read_text(encoding='utf-8'), encoding='utf-8')
    entry_path = RELEASE / 'TRAINING_ENTRYPOINT.json'
    entry = json.loads(entry_path.read_text(encoding='utf-8'))
    entry['status'] = 'V8_ASSESSED_RAW_SCALE_PROMISING_FINAL_TRAINING_ADMISSION_UNRESOLVED'
    entry['current_quality_assessment'] = 'assessment/20261026_quality/QUALITY_ASSESSMENT.md'
    entry['current_quality_summary'] = 'assessment/20261026_quality/ASSESSMENT_SUMMARY.json'
    entry['quality_assessment_packet_manifest'] = 'assessment/20261026_quality/MANIFEST.json'
    entry['v8_new_SFT_compilation_completed'] = False
    entry['v8_final_admitted_training_count_established'] = False
    entry['v6_counts_are_historical_narrow_subset'] = True
    assert entry['training_ready'] is False and entry['training_started'] is False
    entry_path.write_text(json.dumps(entry, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    attrs = RELEASE / '.gitattributes'
    with attrs.open('a', encoding='utf-8', newline='\n') as handle:
        handle.write('assessment/** -text\nassessment/**/*.jsonl.gz filter=lfs diff=lfs merge=lfs -text\n')
    print(json.dumps({k: v for k, v in manifest.items() if k != 'files'}, ensure_ascii=False))


if __name__ == '__main__':
    publish()
