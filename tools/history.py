"""Append known historical WRD library evidence to an existing offline archive.

This module never runs an Agent, model, skill, business task, or training job.
Run it only after the primary Archive writer has closed. Historical roots remain
quarantined; this inventory does not claim exhaustive recovery of early WRD work.
"""
from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from pathlib import Path

from build import Archive, read_json, write_json


SCOPE = 'historical_library_evidence_only'
TEXT_SUFFIXES = {'.json', '.jsonl', '.md', '.csv', '.tsv'}
PRUNE = {
    '.git', '.claude', 'node_modules', '__pycache__', '.venv', '.cache',
    'private', 'credentials', 'inputs', 'sources', 'resources',
}
PRIVATE_FILES = {
    '.env', '.env.local', '.env.production', 'auth-profiles.json',
    'model_credentials.json',
}
PACKAGE_PRUNE = {'.git', '.claude', 'node_modules', '__pycache__', '.venv', '.cache', 'private', 'credentials'}
NATIVE_TEXT_FILES = {'system-prompt.txt'}


def safe_files(directory: Path):
    """Yield package files without following links or including credential stores."""
    for base, dirs, files in os.walk(directory, followlinks=False):
        dirs[:] = sorted(
            n for n in dirs
            if n not in PACKAGE_PRUNE and not (Path(base) / n).is_symlink()
        )
        for name in sorted(files):
            p = Path(base) / name
            if name in PRIVATE_FILES or p.is_symlink():
                continue
            if p.is_file():
                yield p


def append_history(archive_root: Path, inventory_path: Path | None = None):
    """Append metadata, original native transcripts, and historical skill files.

    Workspace input caches and business output files are omitted. A workspace's
    outputs/skill directory is the explicit exception. Historical native metadata
    is retained as evidence, without asserting native execution equivalence or
    per-action correctness for all historical records.
    """
    if not (archive_root / 'file_index.jsonl').is_file():
        raise FileNotFoundError('Primary archive file_index.jsonl must exist first')
    inventory_path = inventory_path or Path(__file__).parent / 'resources' / 'history_inventory.json'
    inventory = read_json(inventory_path, {})
    prior_errors = read_json(archive_root / 'missing_or_excluded.json', [])
    archive = Archive(archive_root, resume=True)
    archive.errors.extend(prior_errors if isinstance(prior_errors, list) else [])
    before = Counter(archive.stats)
    roots = []

    def add(path, logical, source_root, artifact_role):
        archive.add(
            path, logical, SCOPE,
            historical_source_root=str(source_root),
            historical_artifact_role=artifact_role,
            training_split='quarantine',
            native_verification='per_episode_evidence_required',
        )

    for entry in inventory.get('roots', []):
        if entry.get('role') != 'history_only':
            continue
        source = Path(entry['path'])
        row = {'source_root': str(source), 'exists': source.exists(), 'role': 'history_only'}
        root_stats = Counter(archive.stats)
        if not source.is_dir():
            row['status'] = 'missing_root'
            roots.append(row)
            continue
        drive = source.drive.rstrip(':').lower() or 'root'
        logical_root = Path('history') / drive / source.name
        for base, dirs, files in os.walk(source, followlinks=False):
            base = Path(base)
            # Entire historical skill packages retain scripts/templates/assets.
            # Source corpora and workspace caches are never traversed here.
            if 'SKILL.md' in files:
                for p in safe_files(base):
                    add(p, logical_root / p.relative_to(source), source, 'historical_skill_package')
                dirs[:] = []
                continue
            if 'workspace' in dirs:
                skill = base / 'workspace' / 'outputs' / 'skill'
                if skill.is_dir() and not skill.is_symlink():
                    for p in safe_files(skill):
                        add(p, logical_root / p.relative_to(source), source, 'historical_episode_skill_output')
                # Do not archive business artifacts or repeated input caches.
                dirs.remove('workspace')
            dirs[:] = sorted(
                n for n in dirs
                if n not in PRUNE and not (base / n).is_symlink()
            )
            for name in sorted(files):
                p = base / name
                if name in PRIVATE_FILES or name.startswith('.') or p.is_symlink():
                    continue
                # Only recorded textual evidence, not business media/binaries.
                if p.suffix.lower() not in TEXT_SUFFIXES and name not in NATIVE_TEXT_FILES:
                    continue
                add(p, logical_root / p.relative_to(source), source, 'historical_metadata_or_native_transcript')
        row['status'] = 'archived_with_explicit_exclusions'
        row['logical_files_added'] = archive.stats['logical_files'] - root_stats['logical_files']
        row['referenced_bytes_added'] = archive.stats['referenced_bytes'] - root_stats['referenced_bytes']
        roots.append(row)

    add(inventory_path, 'history/history_inventory.json', inventory_path.parent, 'historical_scope_inventory')
    final_stats = archive.close()
    summary = {
        'schema_version': 'wrd-history-archive-addendum-v1',
        'scope': SCOPE,
        'training_split': 'quarantine',
        'roots': roots,
        'logical_files_added': final_stats.get('logical_files', 0) - before.get('logical_files', 0),
        'referenced_bytes_added': final_stats.get('referenced_bytes', 0) - before.get('referenced_bytes', 0),
        'archive_stats_after_append': final_stats,
        'limitations': [
            'Known library roots only; not exhaustive recovery of every early WRD iteration.',
            'Per-episode native equivalence and action correctness are not inferred from directory names.',
            'Formal evaluation roots, workspace inputs, credential stores, and business media outputs excluded.',
            'Prior primary-archive missing/excluded evidence is preserved.',
        ],
    }
    write_json(archive_root / 'history_addendum.json', summary)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive_root', type=Path)
    parser.add_argument('--inventory', type=Path)
    args = parser.parse_args()
    print(json.dumps(append_history(args.archive_root, args.inventory), ensure_ascii=False))
