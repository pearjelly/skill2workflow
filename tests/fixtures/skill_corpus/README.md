# Public Skill corpus

24 original project-authored Skills under the repository Apache-2.0 license.
No third-party source or business data is included. Reserved example HTTP
endpoints describe configuration; the benchmark never executes connectors.

`expectations.json` is the human-authored classification oracle. It includes
false-positive English terms, Chinese controls, plain commands and explicit
HTTP actions/assertions. Add the intended node types before changing inference.

Run `python3 scripts/skill_corpus_benchmark.py`; CI requires perfect inference,
zero false human gates, and at least 25% configured/enforced process nodes.
This small curated corpus is a regression signal, not a claim about all Skills.
