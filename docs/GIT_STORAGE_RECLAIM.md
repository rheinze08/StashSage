# Reclaiming local `.git` storage

The dev machine's `.git` grew to several GB — loose objects, many packs, and
large historical blobs under `poe2trade/db/**` and `generated/super_models/**`
(e.g. a 199 MB `ring_scoring.json` still in history). `tools/reclaim_git_storage.py`
automates the reclaim safely. It is **dry-run by default**; nothing runs until
you pass `--execute`.

## Tier 1 — safe reclaim (no history change)

Repacks and drops already-unreachable objects. Never rewrites commit SHAs, so
it needs no force-push and no coordination.

```bash
# review the commands first
python tools/reclaim_git_storage.py
# actually reclaim
python tools/reclaim_git_storage.py --execute
```

Runs:

- `git reflog expire --expire=now --all`
- `git gc --aggressive --prune=now`

Do this first — it consolidates the packs and prunes the loose/unreachable
objects with zero risk. On the dev box this alone reclaims a few GB.

## Tier 2 — history rewrite (destructive, opt-in)

Strips large regenerable trees from **every commit** with `git filter-repo`.
This rewrites history, so afterwards you must `git push --force-with-lease` every
branch/tag and everyone must re-clone (old SHAs no longer exist). It is gated
behind **two** flags so it can never run by accident.

```bash
# print the plan (still a dry run)
python tools/reclaim_git_storage.py --rewrite-history

# perform it (needs git-filter-repo installed)
python tools/reclaim_git_storage.py --rewrite-history \
    --i-understand-history-rewrite --execute
```

Default paths dropped: `poe2trade/db/files`, `generated/super_models`. Override
with one or more `--drop-path <path>`.

### Before a rewrite

1. Announce it — every open clone/branch will need to re-clone or reset.
2. Make sure `git filter-repo` is installed (`pip install git-filter-repo`).
3. Push any in-flight work first; the rewrite changes SHAs.
4. After it completes, force-push and re-clone. Re-run the CI/release once to
   confirm nothing depended on the removed history.

Prefer Tier 1 unless the historical blobs specifically are the problem — it
gets most of the reclaim with none of the coordination cost.
