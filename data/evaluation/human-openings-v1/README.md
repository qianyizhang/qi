---
description: Attributed and replay-validated human-game prefixes for the local benchmark, with retained selection limits.
scope: benchmark opening source
status: experimental
last_update: 2026-09-11
document_class: artifact
---

# Human-game benchmark openings

Source: Yu-Han Tseng and Bo-Nian Chen (2026),
[Chinese Chess Practical Dataset (CCPD)](https://github.com/Yvonne761/Chinese-Chess-Practical-Dataset),
revision `368a47a947773dd8692c026e286dd19b6277b993`, licensed
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Original source license
is retained in `LICENSE.txt`. Changes: CP950 decoding, legal-move matching from
Chinese notation to coordinates, twelve-ply prefix extraction, board deduplication
and family partitioning. The original game descriptions are source attribution,
not independently verified historical claims.

The bounded input is 256 master-game paths selected by ascending
SHA256(`qi-benchmark-book-v1:` + path), from 53,685 master-game entries visible in
the pinned recursive GitHub tree. That response was truncated: this is a sample
of the returned candidates, not of the entire dataset. All 256 downloaded blobs
matched their Git object hashes; `sources.json` retains accepted source URLs,
SHA-256 receipts, original notation prefixes and portable normalized inputs.
Detailed downloads and the source manifest remain local under
`artifacts/benchmark-book-source-v1/`.

`audit.json` records the import rejection and duplicate-start exclusions.
`development.json` and `locked-test.json` retain the frozen selected prefixes,
source-game identities, families and exact partition policy. Related starts use
the same board/turn after six plies as their family, including transpositions.
The twelve-ply starts are unique by board/turn. This finite family definition
does not assert independence of all chess concepts or opening themes.

Rebuild the same books from the portable inputs into a fresh directory:

```bash
uv run qi bench book --sources data/evaluation/human-openings-v1/sources.json \
  --id ccpd-openings-v1 --output artifacts/rebuilt-benchmark-book
```

Only the imported prefixes have been replay-validated under qi. The records'
human-game origin does not establish representative strength coverage or
absence from future models' training data. Reserved confirmation pools are
managed by the [benchmark lifecycle](../../../docs/benchmark.md); source input
inspection alone does not reveal benchmark match results.
