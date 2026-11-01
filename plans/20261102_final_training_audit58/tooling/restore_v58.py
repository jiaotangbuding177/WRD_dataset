"""Strict V58 restore, using the byte-pinned existing authenticated57 envelope."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys

sys.dont_write_bytecode = True
PINS = {'restore57.py': '2cbfb22e78bb5b28554eac49f7ae366835eb072e9b54b515fc59e031b42711c7', 'existing_AES_API.py': 'c6a48d114269e2b7c550e4d9b4db3c22b506d4faafc35831d799480427dbaafe'}
CIPHER_SHA = '1cbe86bdeeeeb7e27fcb4455da1d27311ed66eedd7a237237e475f42b5cbaf73'
CIPHER_BYTES = 10303636
MANIFEST_SHA = '3d64da349543f5b232b390e5c8094c6f4ae5119e1366e150c2ab981e3cd44601'


def require(value, message):
    if not value:
        raise ValueError(message)


def main():
    require(not sys.flags.optimize, "OPTIMIZED_PYTHON_REJECTED_USE_NORMAL_PYTHON")
    parser = argparse.ArgumentParser()
    parser.add_argument("--cipher", type=Path, required=True)
    parser.add_argument("--key-file", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    require(args.cipher.is_file() and args.cipher.stat().st_size == CIPHER_BYTES, "THIS_RELEASE_CIPHERTEXT_SIZE_REQUIRED")
    require(not args.out.exists() and not args.out.is_symlink(), "NEW_RESTORE_ROOT_REQUIRED")
    require(args.key_file.is_file() and args.key_file.stat().st_size == 32, "EXISTING_LOCAL_32_BYTE_KEY_FILE_REQUIRED")
    repo = Path(__file__).resolve().parents[3]
    folder = repo / "dataset/20261102_v58_protocol_mask/tooling"
    files = {}
    for name, expected in PINS.items():
        path = folder / name
        require(path.is_file() and not path.is_symlink(), "TRUSTED_TOOL_MISSING_OR_LINK")
        require(not (getattr(path.lstat(), "st_file_attributes", 0) & 0x400), "TRUSTED_TOOL_REPARSE_POINT_REJECTED")
        require(hashlib.sha256(path.read_bytes()).hexdigest() == expected, "TRUSTED_TOOL_SOURCE_SHA_MISMATCH")
        files[name] = path
    spec = importlib.util.spec_from_file_location("approved_existing_envelope_restore58", files["restore57.py"])
    implementation = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(implementation)
    receipt = implementation.restore(args.cipher, CIPHER_SHA, MANIFEST_SHA, args.key_file,
                                     files["existing_AES_API.py"], args.out)
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == "__main__":
    main()
