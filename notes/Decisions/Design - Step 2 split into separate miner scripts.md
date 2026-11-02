---
tags: [bpm, decision]
---

# Design - Step 2 split into separate miner scripts

[[PLAN.md]] planned one `step2_discovery.py`. Implemented instead as one script per miner ([[step2_alpha_miner.py]], [[step2_heuristic_miner.py]], [[step2_inductive_miner.py]]) sharing [[pm_common.py]], plus [[step2_compare.py]] to merge their JSON metrics into tables and a Word file.
