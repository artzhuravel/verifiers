# The ladder, across every authored task

Each row is one task written three ways over one `(seed, expected)` pair and one set of
judge items. Open a task's `12_ladder.md` to read the three prompts side by side, or its
`08`/`09`/`10_prompt_*.txt` to see the instruction that produced each rewrite.

`v1 → v2 → v3 chars` is a crude proxy for how much scaffolding each rewrite removed.

| task | topic | steps | judge items | refs | v1 → v2 → v3 chars | reference modes used |
| --- | --- | ---: | ---: | ---: | --- | --- |
| [t0](t0/12_ladder.md) | Backend sprint: payment integration repo verif | 6 | 1 | 2 | 1219 → 1480 → 1319 | containing_text, reply_to_text |
| [t1](t1/12_ladder.md) | Preparing repo data for next week's security a | 6 | 2 | 2 | 1280 → 1264 → 1205 | only_with_unread, by_text |
| [t2](t2/12_ladder.md) | Product launch planning and migration scheduli | 6 | 3 | 7 | 1094 → 1175 → 914 | containing_text, newest_by_handle, reply_to_text, authored_text |
| [t3](t3/12_ladder.md) | Scheduling the new S3->warehouse ingest and sc | 6 | 0 | 3 | 1013 → 1191 → 1076 | containing_text, authored_text |
| [t4](t4/12_ladder.md) | Preparing a quick repo summary for a flagged d | 7 | 2 | 3 | 1213 → 1366 → 1072 | by_name, containing_text, by_text |
| [t5](t5/12_ladder.md) | Preparing the documentation topics for an acme | 6 | 2 | 2 | 844 → 1084 → 655 | by_text, newest_by_handle |
| [t6](t6/12_ladder.md) | Collecting DeepWiki prose for the scheduler re | 6 | 2 | 4 | 1109 → 1036 → 918 | by_name, containing_text, by_text |
| [t7](t7/12_ladder.md) | Site Redesign project coordination | 6 | 4 | 4 | 1226 → 1217 → 751 | by_name, containing_text, by_text, authored_text |
| [t8](t8/12_ladder.md) | Preparing release for acme/telemetry-lib — nee | 6 | 4 | 4 | 895 → 1180 → 1193 | containing_text, by_text, authored_text |
| [t9](t9/12_ladder.md) | backend telemetry rollout and deployment notes | 7 | 4 | 3 | 1256 → 1121 → 922 | by_name, by_text, by_handle |
| [t10](t10/12_ladder.md) | Frontend sprint coordination and a quick repo  | 7 | 2 | 3 | 1628 → 1221 → 1122 | by_name, by_text |
| [t11](t11/12_ladder.md) | Migration and DeepWiki indexing for the event- | 6 | 2 | 4 | 1223 → 1323 → 1096 | containing_text, reply_to_text, authored_text |
