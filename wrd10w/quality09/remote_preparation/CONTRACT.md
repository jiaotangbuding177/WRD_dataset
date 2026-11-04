# Checkpoint09 remote verification preparation

The new tools target `dataset/20261031_v10_checkpoint09`. The original checkpoint08 tools are preserved byte for byte. No production network read, push, key/config access, model call or training was performed in preparation.

`verify_remote09.py` checks the exact supplied Git commit's ordinary blobs against reviewed local release files and checks a nonempty, canonical, unique `PUBLIC_MANIFEST.json` that exactly covers the checkpoint inventory except itself. It requires one canonical LFS pointer under `controlled/` and its actual local ciphertext identity. A new empty download directory is mandatory. It independently requests every 2 MiB range from the exact commit's GitHub media URL, checks HTTP 206, exact Content-Range, unchanged URL, identity encoding and range length, and reconstructs and hashes the complete fresh remote body. Local ciphertext is never used as the downloaded body. A supplied Git directory is an immutable-object check; the root must separately record the fresh remote-fetch provenance for those Git objects.

Relative to 08, 09 also rejects all redirects and malformed/trailing/CRLF LFS pointers, detects ordinary-file LFS pointer bodies with LF or CRLF, and records each range's HTTP status, Content-Range and response URL hash. These tighten validation; no old evidence is reused as a new download. The HTTP URL itself and redirects/errors are not printed.

```
python output/20261031_wrd_curation09_delivery/verify_remote09.py --commit <exact40SHA> --git-dir <freshFetchedBare.git> --release-root <reviewedLocalGitRelease> --download-dir <newEmptyDirectory> --output <newReceipt.json>
```

`verify_metadata_followup09.py` is for the later metadata-only commit. It requires the root-frozen first data commit, first receipt SHA, first actual network body path and whole SHA. It rechecks every saved 2 MiB part, all per-part transport fields, complete contiguous cover and complete actual body SHA. It cold-fetches both exact commits into a new bare repository, checks all ordinary blobs and exact public inventory, and requires an identical canonical LFS path/OID/size/pointer. It does **not** download that final commit's LFS body again and explicitly reports this limitation. It cannot accept an arbitrary same-SHA local ciphertext alias in place of the first receipt's actual network body.

```
python output/20261031_wrd_curation09_delivery/verify_metadata_followup09.py --metadata-commit <final40SHA> --first-data-commit <first40SHA> --first-receipt <firstReceipt.json> --first-receipt-sha256 <frozenSHA> --first-body <originalNetworkBodyPath> --first-body-sha256 <frozenWholeSHA> --cold-git-dir <newBareDirectory> --release-root <reviewedLocalGitRelease> --output <newReceipt.json>
```

Preparation checks: 27 synthetic fresh-verifier cases, 30 synthetic metadata-follow-up cases, and one actual local-only Git init/fetch/cat-file fixture passed. They cover malformed/empty/duplicate/incomplete public inventories, path aliases, wrong sizes/hashes, disabled reuse, wrong range status/header/body/URL/encoding, redirect rejection, contiguous-part gaps/duplicates, forged transport, actual missing/corrupt parts, changed first/final pointers and wrong local ordinary blobs. Synthetic receipts are clearly fixtures and prove no actual GitHub delivery. AI curation and CPU costs are unknown and nonzero.

Only the two verifier scripts and these preparation reports are candidates for an explicit publication allowlist. Fixture directories and synthetic payloads must not be included through a default glob.
