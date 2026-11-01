"""Strict post-freeze restore entry for the authenticated native57 delta.

This file is delivery metadata, outside the frozen research-plan archive. It
imports only the two byte-pinned CPU restore implementations in the dataset.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys

sys.dont_write_bytecode = True
PINS = {
    "restore57.py": "2cbfb22e78bb5b28554eac49f7ae366835eb072e9b54b515fc59e031b42711c7",
    "existing_AES_API.py": "c6a48d114269e2b7c550e4d9b4db3c22b506d4faafc35831d799480427dbaafe",
}
CIPHER_SHA = "b4fbf59c470b412d4350e03a553e65b51dcf37f23dae83b487b849a19ffdbdd3"
CIPHER_BYTES = 81166541
MANIFEST_SHA = "836fa3f686ec861fc1803852b21efdaaf95ad5c466f94a8c2d3281b6c0e45ee2"


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
    parser.add_argument("--key-file", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    require(args.cipher.is_file() and args.cipher.stat().st_size == CIPHER_BYTES, "THIS_RELEASE_CIPHERTEXT_SIZE_REQUIRED")
    require(not args.out.exists(), "NEW_RESTORE_ROOT_REQUIRED")
    require(args.key_file.is_file() and args.key_file.stat().st_size == 32, "EXISTING_LOCAL_32_BYTE_KEY_FILE_REQUIRED")
    repo = Path(__file__).resolve().parents[3]
    files = verified_tools(repo / "dataset/20261101_increment57_native/tooling")
    spec = importlib.util.spec_from_file_location("approved_byte_pinned_native57_restore", files["restore57.py"])
    implementation = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(implementation)
    receipt = implementation.restore(args.cipher, CIPHER_SHA, MANIFEST_SHA, args.key_file,
                                     files["existing_AES_API.py"], args.out)
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == "__main__":
    main()
