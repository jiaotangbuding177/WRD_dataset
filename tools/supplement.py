"""Append recorded execution logs and tool-schema provenance after archive closes."""
import argparse
import json
from pathlib import Path

from build import Archive, read_json, write_json


def supplement(bundle):
    bundle = Path(bundle).resolve()
    archive = Archive(bundle / 'archive', resume=True)
    archive.errors.extend(read_json(bundle / 'archive/missing_or_excluded.json', []))
    count_before = archive.stats['logical_files']
    names = ['stderr.log', 'stdout.log', 'openclaw_transport/stderr.log', 'openclaw_transport/stdout.log', 'openclaw_transport/gateway.stderr.log', 'openclaw_transport/gateway.stdout.log', 'openclaw_transport/export.stderr.log', 'openclaw_transport/export.stdout.log']
    with (bundle / 'catalog/episodes.jsonl').open(encoding='utf-8') as src:
        for line in src:
            row = json.loads(line)
            for name in names:
                p = Path(row['source_path']) / name
                if p.is_file() and p.stat().st_size:
                    archive.add(p, row['archive_path'] + '/' + name, 'recorded_execution_logs', episode_id=row['episode_id'])
    resources = Path(__file__).resolve().parent / 'resources'
    archive.tree(resources, 'protocol/recovery_resources', 'native_schema_and_history_scope_provenance')
    stats = archive.close()
    result = {'schema': 'wrd-recorded-logs-addendum-v1', 'logical_files_added': stats['logical_files'] - count_before, 'archive_stats_after_append': stats, 'new_model_calls': 0}
    write_json(bundle / 'archive/logs_addendum.json', result)
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bundle', type=Path, required=True)
    supplement(p.parse_args().bundle)
