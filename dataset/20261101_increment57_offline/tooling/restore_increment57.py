"""Strict entrypoint for the pinned57 authenticated offline archive.

Refuses optimized Python and unreviewed restore/AES source replacements before
import. The key is read only by the fixed AES implementation and never copied.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import re
import sys

sys.dont_write_bytecode = True
PINS = {
    "restore57.py": "2cbfb22e78bb5b28554eac49f7ae366835eb072e9b54b515fc59e031b42711c7",
    "existing_AES_API.py": "c6a48d114269e2b7c550e4d9b4db3c22b506d4faafc35831d799480427dbaafe",
}
CIPHER_SHA = "01b8b5ec9e1ca7ce0b131a7da556e19d0115ca645f51b212c864d585dd1cde1b"
MANIFEST_SHA = "e117f39c2c902c363b2b9311f60d6973ed866bf9f6bbca68048e81b3d7747801"


def require(value, message):
    if not value:
        raise ValueError(message)


def verified_tools(folder):
    require(not sys.flags.optimize, "OPTIMIZED_PYTHON_REJECTED_USE_NORMAL_PYTHON")
    files = {}
    for name, expected in PINS.items():
        path = folder / name
        require(path.is_file() and not path.is_symlink(), "TRUSTED_TOOL_MISSING_OR_LINK")
        require(not (getattr(path.lstat(), "st_file_attributes", 0) & 0x400), "TRUSTED_TOOL_REPARSE_POINT_REJECTED")
        require(hashlib.sha256(path.read_bytes()).hexdigest() == expected, "TRUSTED_TOOL_SOURCE_SHA_MISMATCH")
        files[name] = path
    return files


def main():
    require(not sys.flags.optimize, "OPTIMIZED_PYTHON_REJECTED_USE_NORMAL_PYTHON")
    parser = argparse.ArgumentParser()
    parser.add_argument("--cipher", type=Path, required=True)
    parser.add_argument("--cipher-sha256", required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--key-file", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    require(re.fullmatch("[0-9a-f]{64}", args.cipher_sha256) and args.cipher_sha256 == CIPHER_SHA,
            "THIS_RELEASE_CIPHERTEXT_SHA_REQUIRED")
    require(re.fullmatch("[0-9a-f]{64}", args.manifest_sha256) and args.manifest_sha256 == MANIFEST_SHA,
            "THIS_RELEASE_MANIFEST_SHA_REQUIRED")
    require(not args.out.exists(), "NEW_RESTORE_ROOT_REQUIRED")
    require(args.key_file.is_file() and args.key_file.stat().st_size == 32, "EXISTING_LOCAL_32_BYTE_KEY_FILE_REQUIRED")
    files = verified_tools(Path(__file__).resolve().parent)
    spec = importlib.util.spec_from_file_location("approved_pin_verified_restore57", files["restore57.py"])
    implementation = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(implementation)
    receipt = implementation.restore(args.cipher, args.cipher_sha256, args.manifest_sha256,
                                     args.key_file, files["existing_AES_API.py"], args.out)
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == "__main__":
    main()
