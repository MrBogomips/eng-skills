#!/usr/bin/env bash
set -euo pipefail
mkdir -p notes docs
cat > notes/cli-notes.md <<'MD'
# snapkeep CLI notes

Content-addressed storage: files are split into chunks (FastCDC, 512 KiB-8 MiB), each chunk stored once by SHA-256, so the second snapshot of an unchanged folder adds almost nothing. Snapshots are immutable trees of chunk references. Retention policies (`snapkeep forget --keep-daily 7`) remove snapshots; `snapkeep prune` reclaims unreferenced chunks.

Install: `brew install snapkeep` or the release binary.

First run:
- `snapkeep init --repo ~/backups/main` creates a repository, asks for a password; prints `created repository 3f9a1c at ~/backups/main`.
- `snapkeep backup ~/Documents --repo ~/backups/main` prints `snapshot 8d21e0 saved (1,204 files, 312 MiB added)`.
- `snapkeep snapshots --repo ~/backups/main` lists snapshots with id, time, host, paths.
- `snapkeep restore 8d21e0 --target ~/restore --repo ~/backups/main` prints `restored 1,204 files`.
- Set `SNAPKEEP_REPO=~/backups/main` to omit --repo.

Other backends: S3 (`s3:bucket/path`), SFTP. Encryption: AES-256-GCM, key derived with scrypt.
MD
