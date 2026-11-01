"""Cold-verify seven real GitHub LFS objects; credentials/signatures never logged.

Only official GitHub LFS batch read requests and HTTPS downloads are made.
Downloaded data is never executed. This script does not change Git refs.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from datetime import datetime, timezone
from urllib.parse import urlparse
import hashlib, json, os, re, subprocess, threading, time, uuid
import requests

REPO = Path('D:/skillloop/output/20261025_wrd_training_dataset/git_release')
OUT = Path('D:/skillloop/output/20261101_wrd_git_full_delivery')
SPEC = OUT / 'DATA_DELIVERY_REVIEW.json'
ENDPOINT = 'https://github.com/jiaotangbuding177/WRD_dataset.git/info/lfs/objects/batch'
CHUNK_BYTES = 8 * 1024 * 1024
WORKERS = 4
REQUEST_TIMEOUT = (15, 40)
LOCK = threading.Lock()
WIRE_BYTES = 0
SAVED_BYTES = 0

def utc(): return datetime.now(timezone.utc).isoformat()
def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

class CheckError(Exception): pass

def credential():
    env = dict(os.environ, GIT_TERMINAL_PROMPT='0', GCM_INTERACTIVE='Never')
    result = subprocess.run(['git','credential','fill'], cwd=REPO,
        input='protocol=https\nhost=github.com\npath=jiaotangbuding177/WRD_dataset.git\n\n',
        capture_output=True, text=True, env=env)
    fields = dict(line.split('=',1) for line in result.stdout.splitlines() if '=' in line)
    if result.returncode or not fields.get('username') or not fields.get('password'):
        raise CheckError('GITHUB_CREDENTIAL_UNAVAILABLE')
    return fields['username'], fields['password']

def allowed_storage(url):
    parsed = urlparse(url)
    host = (parsed.hostname or '').lower()
    if parsed.scheme != 'https' or parsed.username or parsed.password:
        raise CheckError('UNSAFE_DOWNLOAD_URL')
    if not (host in {'github.com','github-cloud.s3.amazonaws.com','objects.githubusercontent.com',
                     'github-cloud.githubusercontent.com'} or
            host.endswith('.githubusercontent.com') or
            (host.startswith('github-') and (host.endswith('.s3.amazonaws.com') or '.s3.' in host and host.endswith('.amazonaws.com')))):
        raise CheckError('NON_GITHUB_STORAGE_HOST')
    return host

def action_for(ref, auth):
    body = {'operation':'download','transfers':['basic'],
            'objects':[{'oid':ref['sha256'],'size':ref['bytes']}]}
    for attempt in range(3):
        try:
            response = requests.post(ENDPOINT, json=body, auth=auth,
                headers={'Accept':'application/vnd.git-lfs+json','Content-Type':'application/vnd.git-lfs+json'},
                timeout=REQUEST_TIMEOUT, allow_redirects=False)
            if response.status_code != 200:
                raise CheckError('LFS_BATCH_HTTP_' + str(response.status_code))
            items = response.json().get('objects',[])
            if len(items) != 1 or items[0].get('oid') != ref['sha256']:
                raise CheckError('LFS_BATCH_OBJECT_ID_MISMATCH')
            item = items[0]
            if 'error' in item:
                raise CheckError('LFS_OBJECT_ERROR_' + str(item['error'].get('code','UNKNOWN')))
            if item.get('size') != ref['bytes']:
                raise CheckError('LFS_BATCH_SIZE_MISMATCH')
            action = item.get('actions',{}).get('download')
            if not action or not action.get('href'):
                raise CheckError('LFS_DOWNLOAD_ACTION_MISSING')
            allowed_storage(action['href'])
            return action
        except (requests.RequestException, ValueError, CheckError) as exc:
            code = str(exc) if isinstance(exc, CheckError) else type(exc).__name__
            if code == 'LFS_OBJECT_ERROR_404': raise CheckError(code)
            if attempt == 2: raise CheckError(code)
            time.sleep(1 + attempt)

def get_range(action, start, end):
    url = action['href']
    headers = dict(action.get('header') or {})
    headers.update({'Range':f'bytes={start}-{end}','Accept-Encoding':'identity'})
    for _ in range(4):
        allowed_storage(url)
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT,
                                stream=True, allow_redirects=False)
        if response.status_code in {301,302,303,307,308}:
            location = response.headers.get('Location')
            response.close()
            if not location: raise CheckError('DOWNLOAD_REDIRECT_WITHOUT_LOCATION')
            # Do not carry any service header over a redirect; the signed URL is sufficient.
            url = requests.compat.urljoin(url, location)
            headers = {'Range':f'bytes={start}-{end}','Accept-Encoding':'identity'}
            continue
        return response
    raise CheckError('DOWNLOAD_REDIRECT_LIMIT')

def download(ref, auth, run_dir):
    global WIRE_BYTES, SAVED_BYTES
    started = utc()
    action = action_for(ref, auth)
    path = run_dir / (ref['sha256'] + '.entity')
    offset, requests_count, retries, statuses, storage_hosts = 0, 0, 0, {}, set()
    storage_hosts.add(allowed_storage(action['href']))
    with path.open('xb') as target:
        while offset < ref['bytes']:
            end = min(offset + CHUNK_BYTES - 1, ref['bytes'] - 1)
            for attempt in range(3):
                written = 0
                try:
                    response = get_range(action, offset, end)
                    requests_count += 1
                    code = response.status_code
                    statuses[str(code)] = statuses.get(str(code), 0) + 1
                    if code in {401,403}:
                        response.close()
                        action = action_for(ref, auth)
                        storage_hosts.add(allowed_storage(action['href']))
                        raise CheckError('DOWNLOAD_ACTION_REFRESHED')
                    if code == 206:
                        match = re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)', response.headers.get('Content-Range',''))
                        if not match or tuple(map(int,match.groups())) != (offset,end,ref['bytes']):
                            response.close(); raise CheckError('CONTENT_RANGE_MISMATCH')
                        expected = end - offset + 1
                    elif code == 200 and offset == 0:
                        expected = ref['bytes']
                    else:
                        response.close(); raise CheckError('DOWNLOAD_HTTP_' + str(code))
                    if response.headers.get('Content-Encoding','identity').lower() not in {'','identity'}:
                        response.close(); raise CheckError('UNEXPECTED_CONTENT_ENCODING')
                    length = response.headers.get('Content-Length')
                    if length is not None and int(length) != expected:
                        response.close(); raise CheckError('CONTENT_LENGTH_MISMATCH')
                    with response:
                        for block in response.iter_content(chunk_size=1 << 20):
                            if not block: continue
                            with LOCK: WIRE_BYTES += len(block)
                            written += len(block)
                            if written > expected: raise CheckError('DOWNLOAD_OVERFLOW')
                            target.write(block)
                    if written != expected: raise CheckError('DOWNLOAD_SHORT_READ')
                    target.flush()
                    offset += written
                    with LOCK: SAVED_BYTES += written
                    break
                except (requests.RequestException, ValueError, CheckError) as exc:
                    code = str(exc) if isinstance(exc,CheckError) else type(exc).__name__
                    target.seek(offset); target.truncate(offset)
                    retries += 1
                    if attempt == 2: raise CheckError(code)
                    time.sleep(1 + attempt)
    h = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1 << 20), b''): h.update(block)
    digest = h.hexdigest()
    if path.stat().st_size != ref['bytes'] or digest != ref['sha256']:
        raise CheckError('DOWNLOADED_ENTITY_HASH_OR_SIZE_MISMATCH')
    return {'entity':ref['entity'],'expected_bytes':ref['bytes'],'downloaded_file_bytes':path.stat().st_size,
            'sha256':digest,'expected_sha256':ref['sha256'],'status':'PASS_COLD_DOWNLOADED_FULL_ENTITY_SHA_AND_SIZE',
            'started_utc':started,'finished_utc':utc(),'local_file':str(path),
            'http_requests':requests_count,'http_status_counts':statuses,
            'retry_count':retries,'content_range_checked_for_all206':True,
            'storage_hosts_without_signed_urls':sorted(storage_hosts)}

def main():
    start = utc()
    started_perf = time.monotonic()
    spec = json.loads(SPEC.read_text(encoding='utf-8-sig'))
    refs = spec['packages']
    auth = credential()
    run_dir = OUT / 'remote_entities55' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid.uuid4().hex[:8])
    run_dir.mkdir(parents=True, exist_ok=False)
    report = {'schema':'wrd55-seven-real-lfs-cold-download-verification',
              'status':'RUNNING','started_utc':start,'finished_utc':None,
              'data_spec_sha256':hashlib.sha256(SPEC.read_bytes()).hexdigest(),
              'required_objects':len(refs),'required_distinct_bytes':sum(x['bytes'] for x in refs),
              'objects':[],'pending':[], 'errors':[], 'TLS_verification_enabled':True,
              'credential_source':'git credential fill; only in process memory; sent to official github.com LFS batch',
              'credentials_headers_and_signed_URLs_not_recorded':True,
              'model_weights_loaded':False,'training_started':False,
              'downloaded_data_executed':False,'git_refs_changed':False,
              'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    def persist():
        with LOCK:
            report['actual_network_payload_bytes_received'] = WIRE_BYTES
            report['saved_valid_range_bytes'] = SAVED_BYTES
        report['elapsed_seconds'] = round(time.monotonic()-started_perf,3)
        save(OUT / 'REMOTE_ENTITIES55.json',report)
    def round_download(selected):
        pending = []
        with ThreadPoolExecutor(max_workers=WORKERS) as executor:
            futures = {executor.submit(download,ref,auth,run_dir):ref for ref in selected}
            last_print = 0.0
            while futures:
                done,_ = wait(futures, timeout=15, return_when=FIRST_COMPLETED)
                for future in done:
                    ref = futures.pop(future)
                    try:
                        item = future.result()
                        report['objects'].append(item)
                        print(json.dumps({'event':'ENTITY_VERIFIED','entity':ref['entity'],'bytes':item['downloaded_file_bytes'],
                                          'verified_objects':len(report['objects'])}), flush=True)
                    except Exception as exc:
                        code = str(exc) if isinstance(exc,CheckError) else type(exc).__name__
                        if code == 'LFS_OBJECT_ERROR_404':
                            pending.append(ref)
                            print(json.dumps({'event':'LFS_OBJECT_NOT_YET_AVAILABLE','entity':ref['entity'],'code':code}),flush=True)
                        else:
                            report['errors'].append({'entity':ref['entity'],'error_code':code})
                            print(json.dumps({'event':'ENTITY_FAILED','entity':ref['entity'],'error_code':code}),flush=True)
                    persist()
                if time.monotonic()-last_print >= 30:
                    with LOCK: progress = {'wire_bytes':WIRE_BYTES,'saved_valid_bytes':SAVED_BYTES}
                    print(json.dumps({'event':'PROGRESS','verified_objects':len(report['objects']),
                                      'active_objects':len(futures),**progress}),flush=True)
                    persist();last_print=time.monotonic()
        return pending
    pending = round_download(refs)
    # An in-flight Git LFS upload may make a missing object available before the others finish.
    for retry in range(3):
        if not pending: break
        print(json.dumps({'event':'RECHECK_PREVIOUSLY_MISSING_OBJECTS','objects':len(pending),'round':retry+1}),flush=True)
        time.sleep(15)
        pending = round_download(pending)
    report['pending'] = [{'entity':r['entity'],'sha256':r['sha256'],'bytes':r['bytes'],'reason':'LFS_OBJECT_ERROR_404'} for r in pending]
    report['verified_distinct_bytes'] = sum(x['downloaded_file_bytes'] for x in report['objects'])
    report['finished_utc'] = utc()
    report['status'] = ('PASS_ALL_SEVEN_REAL_REMOTE_ENTITIES_COLD_DOWNLOADED_AND_FULL_SHA_VERIFIED'
                        if len(report['objects']) == len(refs) and not report['errors'] and not pending
                        else 'INCOMPLETE_REMOTE_ENTITIES_VERIFICATION')
    persist()
    print(json.dumps({'event':'FINAL','status':report['status'],'verified_objects':len(report['objects']),
                      'verified_distinct_bytes':report['verified_distinct_bytes'],
                      'pending_objects':len(pending),'errors':report['errors']}),flush=True)

if __name__ == '__main__':
    try: main()
    except Exception as exc:
        # Never render request exception text, which can embed a signed storage URL.
        print(json.dumps({'event':'FATAL','error_code':str(exc) if isinstance(exc,CheckError) else type(exc).__name__}),flush=True)
        raise SystemExit(1)
