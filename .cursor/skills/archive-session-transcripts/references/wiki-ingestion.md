# Local ingestion and cleanup verification

Use this after conversion. Confirm the target wiki exists; never initialize or relocate
it implicitly. Inspect its current CLI help when an installed version differs.

The workstation's CLI lives at `<wiki-root>/.venv/Scripts/llmwiki.exe`.
Use the installed `llmwiki` command if available; otherwise invoke that executable with
PowerShell's call operator. From the wiki checkout, `uv run llmwiki` is another option.

```powershell
llmwiki --root <wiki-root> --mode agent ingest <absolute-note-path> --json
llmwiki --root <wiki-root> sources --id <source-id> --json
llmwiki --root <wiki-root> validate --json
llmwiki --root <wiki-root> render --json
```

Placeholders denote arguments, not literal runnable shell syntax. Use an argument array
or quoted literal paths for real invocations. `--mode agent` prevents model calls.
The read-only `llmwiki-ro-core` MCP cannot ingest. A write-enabled MCP is usable only if
its configured roots include the output; a permissions error is not ingestion success.
If filesystem permissions require elevation, use the host's approval mechanism.

## Preparation and allowed roots

Freeze a batch manifest before side effects: project/source paths, full original digest
and size, output paths and digests, private evidence destination, and known blockers.
Give newly discovered exports a separately identified addition; do not silently replace
an in-progress plan or claim the discovery count equals the conversion/deletion count.
Hash-based filenames must still compare full digests before reuse; refuse collisions.

Keep raw sensitive material in the established private store from the first temporary
write. An ignored scratch directory is suitable only for permitted manifests/sanitized
derivatives. If temporary staging becomes inaccessible, retain originals, select an
allowed accessible staging directory and regenerate/reconcile from unchanged hashes.
Do not keep retrying an unreadable temporary tree or bypass filesystem approvals.

Respect the wiki's configured allowed roots. When a project note is outside them, a
sanitized mirror under a permitted wiki notes directory can be ingested with identical
bytes. Verify privacy and ignores there, including any nested Git checkout, before copying.
Do not widen wiki configuration merely to ingest a batch or copy raw exports into its store.

On Windows, verify the Python/CLI launcher actually works; a WindowsApps alias may not.
The wiki's existing `.venv/Scripts/python.exe` was usable in this run. Set `PYTHONUTF8=1`
and `PYTHONIOENCODING=utf-8` in the child process environment when invoking its CLI, and
decode captured stdout/stderr as UTF-8. Preserve permitted diagnostic output locally,
but report only the error and safe counts, not private rendered-page names/content.

## Interpret actual results

Current CLI JSON has an `ok` flag and `result`. Default ingest waits and returns a job:
require `result.status == "completed"`; its nested `result.result` contains `source_id`,
`revision_id`, `digest`, and source `status`. Require source `status == "ready"`.
An invocation with `--source-id` instead returns the source result directly. Note that
this option is the service's stable source-key contract, not a reason to invent a UUID.
Read current help/service documentation before using it.

Verify the note's SHA-256 equals the returned `digest`. Query `sources --id` and require
that the returned immutable revision ID belongs to this source, has the same digest and
byte size, and is `ready`. For a new note it should be the current revision; for a reused
historical revision, verify that exact revision rather than silently choosing another.
If `wiki/` is a nested Git checkout, verify ignore/untracked status there as well as in
the parent project. A parent ignore rule does not protect a file from the nested remote.
Reopen the note and confirm that useful content was preserved. `validate` must report
inner `ok == true`, `error_count == 0`, and no issues, as well as a successful envelope.
Run `render` after successful canonical changes and report
any conflicts; do not overwrite manual wiki pages. Keep originals when a required check
fails. Reviewed-only claim search need not return a newly ingested source.
For the default render job, require completed status before reading its nested result;
the current result has `count`, `rendered`, and `unchanged`, rather than source revision
fields. Validate again after rendering. Follow local index/log conventions at the same
privacy tier as the notes; public logs may contain safe aggregate counts only.

Never treat an exit code alone, a queued job, a filename in a listing, an unrelated search
hit, or an OCR-required source as evidence of completion. If queued, use
`llmwiki --root <wiki> job get <job-id> --json` until terminal; stop on failed/cancelled
and retain the original. Do not endlessly resubmit a failing item.
An empty/unparseable response or console encoding error can happen after a store mutation.
Read captured stderr, inspect the receipt and actual source/job state, fix the specific
failure and resume the failed phase. Do not re-ingest successful items just to retry render.

## Receipt and deletion gates

In a project-policy-approved ignored or off-repo store, record per export:

- Original relative path, SHA-256 and size; project root (private metadata).
- Converted note/companion paths, SHA-256 and size; classification and omissions.
- Wiki root, source/revision IDs and digest for each ingested document; verification result.
- Authorization scope and final disposition (`retained`, `blocked`, `deleted`).

Private receipts are local data, not tracked agent memory. Keep hashes/receipts out of
the document body after ingestion; changing that body requires re-ingestion and verification.
The note's original-source SHA-256 is provenance and may be written before ingestion;
source/revision receipt fields belong outside it. Distinguish original and derivative
digests in filenames/index labels, and keep full digests in receipts. Persist completed
item states so an interrupted batch can reconcile them rather than invent a new identity.
Write receipt updates atomically within their approved store. Record preservation before
cleanup and persist each deletion result; on interruption, reconcile missing originals
against the verified archive and wiki revision before recording a final disposition.

Before deleting an export require: authorized batch; complete useful preservation;
permitted treatment of omitted private data; matching original and note hashes;
verified completed ingestion of all required sanitized sources; successful wiki validation
and rendering; source is a regular exported file inside its approved root and not a symlink,
hardlink shared with a live store, active transcript, or changed file. Resolve paths again.
Refresh curated-document references before removal. A shortened discovery note cannot
replace a transcript's line-level evidence citation; preserve the original when a safe
equivalent reference cannot be supplied within project policy. Retain only affected items.
Delete with `Remove-Item -LiteralPath <verified-file>` on Windows (no `-Recurse` or wildcard).
If interrupted after ingestion, reconcile the receipt and source revisions before retrying.
If interrupted after deletion, confirm the preserved docs/source and update the receipt;
do not recreate or remove arbitrary similarly named files.
Distinguish attachments absent from the original text export from evidence newly lost
during conversion. Record preexisting absence explicitly; exact private archival preserves
the exported references but cannot recover attachments that were never exported. Retain
an original when required evidence actually contained in it has no verified preserved copy.

After cleanup, audit actual file presence against each disposition, reopen and hash every
preserved original and derivative, and recheck ignore/untracked status. Report project
roots scanned, confirmed exports, converted/ingested items, and removed/retained originals
separately. Put full source/revision IDs in a permitted local index/receipt.
