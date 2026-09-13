# Runbook — supervisor points 3 and 4

> **Decided 30 August 2026.** Submission is 31 August. The path taken is step 1
> and step 2a only; **step 2b (LoRA) is skipped**. Few-shot and RAG are
> regenerated over all 98 records; LoRA keeps its stored predictions and is
> therefore scored on 73. `rescore_legacy_baselines.py` drops the 25 reworded
> records for LoRA automatically, so the asymmetry is produced by the scorer
> rather than asserted, and it is declared in the table caption. The substance of
> the supervisor's point is the RAG parent-versus-exact gap, and that is measured
> on the full benchmark.
>
> Use this `--results` list in step 2c, mixing the two regenerated files with the
> stored LoRA one:
>
> ```
> --results experiments/legacy_rerun_frozen98_v1/results_fewshot.json experiments/legacy_rerun_frozen98_v1/results_rag.json ../Documents/results_lora.json
> ```


Everything below runs **on your machine**, because the OpenAI key lives there and
has never left it. Run each block from the repository root:

```
cd "C:\Users\sefir\OneDrive - aivancity\PGE 5\PFE\aviation_rag_research"
```

Use **one** interpreter for all of it — the one that has `openai` installed.
Appendix A records that two Pythons are on `PATH` on this machine, and the July
runs and the held-out run were both made with 3.10.11 / openai 2.24.0. Check
before starting:

```
python -c "import sys, openai; print(sys.executable); print(openai.__version__)"
```

If that fails, use the interpreter that works and keep using it for every
command here. Nothing in this runbook writes to `Documents/`: the historical
artefacts stay immutable under decision D002.

---

## Step 1 — point 4: the enriched context variant, development only

The supervisor's point: the neighbour-enriched context variant is built and
never executed. This runs it on the **development partition only**. It must not
be run on the held-out partition: that partition was generated once, after
freeze, and a second post-freeze run would contradict D043 and weaken the
strongest methodological claim in the thesis. `run_generation.py` refuses the
held-out split unless an explicit flag is passed — do not pass it.

Cost: 42 answers, roughly one US cent.

```
python scripts/run_generation.py --contexts experiments/E5_context_top5_neighbors_reviewed_v1/contexts.jsonl --prompt prompts/evidence_constrained_answer_v2.md --schema schemas/answer_output_v1.schema.json --output experiments/E5_generation_neighbors_dev_v2 --cache experiments/cache/generation --model gpt-4o-mini-2024-07-18 --temperature 0 --split development --dry-run
```

Read the dry-run output, then remove `--dry-run` and run it again.

Result: `experiments/E5_generation_neighbors_dev_v2/` with answers, a generation
summary and a manifest, directly comparable with
`experiments/E5_generation_top5_dev_v2/` — same prompt, same schema, same model,
same 42 questions, only the context construction differs.

---

## Step 2 — point 3: the baselines over all 98 records

The supervisor's point: the three-system comparison covers 73 of 98 records and
the 25 excluded are not a random subset. This regenerates the historical
predictions against the **frozen question wording** so the comparison covers the
whole benchmark under one provenance.

### 2a. Few-shot and RAG (the API part)

Cost: 588 predictions plus 5 embedding batches, estimated at about USD 0.12.
Every response is cached by a digest over model, system prompt and user prompt,
so an interrupted run resumes where it stopped and a repeat run costs nothing.

```
python scripts/rerun_legacy_baselines.py --benchmark data/evaluation/reviewed_benchmark_v1/reviewed_benchmark.jsonl --qa-pairs ../Documents/qa_pairs_final.json --chunks ../Documents/regulation_chunks_clean.csv --output experiments/legacy_rerun_frozen98_v1 --cache experiments/cache/legacy_rerun --dry-run
```

The dry run prints the call count and the cost estimate and writes nothing.
Then remove `--dry-run`.

### 2b. LoRA (local, no billing)

The adapter is unchanged and decoding is greedy, so this is deterministic and
costs only GPU time. It doubles as a reproducibility check: the 73 records whose
wording did not change should reproduce the stored predictions exactly, and the
manifest reports that rate.

```
python scripts/rerun_legacy_lora.py --benchmark data/evaluation/reviewed_benchmark_v1/reviewed_benchmark.jsonl --qa-pairs ../Documents/qa_pairs_final.json --adapter ../Documents/lora_model --stored ../Documents/results_lora.json --output experiments/legacy_rerun_frozen98_v1 --check-only
```

`--check-only` loads no model. It verifies the data, reports which packages are
missing and whether CUDA is visible, and re-checks that no frozen record was in
the adapter's training split — it refuses to run if that ever stops holding.
Then remove `--check-only`.

If this step will not run (Hugging Face gating on Llama-3.2, `bitsandbytes`, or
VRAM), say so rather than forcing it: `--no-4bit` loads in bf16 instead, and if
that also fails the fallback is to keep LoRA at n = 73 and declare the asymmetry
in the table caption. Few-shot and RAG at n = 98 are the part that matters most.

### 2c. Re-score all three on the frozen labels

```
python scripts/rescore_legacy_baselines.py --benchmark data/evaluation/reviewed_benchmark_v1/reviewed_benchmark.jsonl --parents data/processed/E1_parent_child_v1/parents.jsonl --split-manifest data/evaluation/reviewed_benchmark_v1/split_manifest.csv --chunk-parent-map data/evaluation/legacy_to_e1_v1/legacy_chunk_parent_map.csv --results experiments/legacy_rerun_frozen98_v1/results_fewshot.json experiments/legacy_rerun_frozen98_v1/results_rag.json experiments/legacy_rerun_frozen98_v1/results_lora.json --output experiments/legacy_baselines_frozen98_v1
```

The scorer drops any record whose question text differs from the frozen
benchmark. Because these predictions were generated from the frozen wording,
**the excluded count should now be zero and n should be 98**. If it is not, stop
and report the number — it means something did not regenerate.

---

## Step 3 — send me the output

Paste the console output of each step. I will then:

* rewrite Chapter 5 section 5.4 (Scope and Results) for n = 98, keeping the
  n = 73 column beside it so the effect of the exclusion is visible rather than
  merely asserted;
* add the enriched-variant comparison to Chapter 5 and remove the "built and
  unrun" limitation from Chapter 6;
* update the Chapter 5 summary table, the abstract and the conclusion where the
  numbers move;
* append the decision-log entries and the generated-artifacts rows.

## What stays true whatever the numbers say

The re-run does not license revising anything about the held-out generation run.
It touches the historical baselines and one development-only context ablation.
If the full-benchmark baseline numbers are worse than the n = 73 subset, that is
the result and it is reported as such — it is the direction the Chapter 5 scope
note already predicts.
