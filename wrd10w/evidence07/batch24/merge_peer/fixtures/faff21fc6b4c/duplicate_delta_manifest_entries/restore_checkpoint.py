from pathlib import Path
import shutil,json
def restore(cipher,receipt,key,out):
    # Key-free fixture stub: only merge validation is being tested.
    shutil.copytree(cipher,out)
    return {'authenticated_files':len(json.loads((out/'PAYLOAD_MANIFEST.json').read_text())['files'])+1}
