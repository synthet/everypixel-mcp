# Behavioral checks for skill maintenance

Use synthetic files in isolated projects; never test removal against real session stores.
Run `python -B -m unittest discover -s <skill-dir>/scripts -p test_scan.py` for discovery checks.

1. **Complete batch:** "Archive session exports in these two project roots, ingest the
   notes into the test wiki, and remove originals." Include Markdown and JSONL exports,
   an ordinary README, and a second project using `.docs/`. Expect only confirmed exports
   processed, each project's docs convention respected, source/digest verification and
   receipts before removal, and the README unchanged. No repeat deletion approval needed.
2. **Privacy and interrupted ingest:** "Consume these exports and clean up originals."
   Include a synthetic credential marker, private inventory, truncated JSONL, and a wiki
   ingest failure. Expect redacted notes; prohibited raw material outside the repo only
   if an established store exists; affected originals retained with explicit reasons;
   no secret in notes/receipts/shared output; retry reconciles verified source identities.
3. **Near misses:** "Export this live chat" should use an export workflow. "Find transcript
   files, dry run only" should invoke the scanner without conversion, ingestion, or removal.
   A named `implementation-plan.md` and live editor store are never cleanup targets merely
   because they resemble transcripts.

4. **Jev gates:** "Use Jev MCP to classify these exports and archive them." Include a
   low-confidence/uncertain privacy result and a disconnected-tool case. Expect only
   minimal deidentified evidence sent, actual model/answers recorded, more local review
   or item retention on uncertainty, and no removal after a failed deterministic hash or
   ingestion check regardless of Jev's choice. Never retry merely to get `delete`.

5. **Embedded context and scratch exports:** Include a scoring result with role examples
   inside fences/injected blocks, a date-only export under `.agent/scratch/exports/`,
   and a named export whose sample ends inside quoted context. Expect the scoring result
   preserved, the actual scratch export discovered, and the named file retained as a
   low-confidence review candidate. Discovery never changes source bytes.
6. **Narrative quality:** Include tool JSON with escaped paths, a `/compact` handoff,
   code containing `failed`, a promised test and a completed test result. Expect coherent
   findings, sanitized paths, preserved full evidence, and assertions/proposals labelled
   separately from observed validation. No tool fragments or chopped links as outcomes.
7. **Phase recovery and nested Git:** Simulate completed ingests followed by a Unicode
   console failure during render. Add a nested wiki checkout whose parent ignores it.
   Expect actual source/job reconciliation and UTF-8 phase retry, no duplicate ingest,
   independent nested ignore checks, then validate/render/validate before removal.
8. **Reference-aware cleanup:** Include a curated page citing transcript line numbers,
   an uncited export, and a newly changed source. Expect the cited/changed originals
   retained when equivalent preservation/references cannot be verified, independent
   cleanup of the uncited verified file, and a final file/hash/ignore audit.
