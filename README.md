# Seed Randomness Experiment

> [한국어](README.kr.md) · **English**

Does putting a random seed at the very front of a prompt actually make LLM responses more random? This controlled experiment compares four treatment conditions.

## Main Finding

The mechanisms that increase diversity form a clear ladder.

```
plain  <  seed prefix  <  natural-language instruction ("randomly")  <  delusionist-mini pollution
```

Putting a random seed at the front of the prompt does not make responses meaningfully more random. It adds a bit of surface-level variation in wording, but the model still settles into the same stance and the same core argumentative structure. If you want a real shift in the output distribution, you need either explicit natural-language instruction or semantic-level noise injection.

![Diversity ladder](report/figures/fig1_diversity_ladder.png)

For the full write-up, start with [Eng_md.ver.md](report/Eng_md.ver.md) (long-form report) or [Eng_pap.ver.md](report/Eng_pap.ver.md) (paper-style version). Korean versions are also available: [Korean long-form report](report/한국어_md.ver.md) and [Korean paper-style report](report/한국어_논문.ver.md).

## Reports

| Language | Long-form | Paper style |
|---|---|---|
| Korean | [Korean long-form report](report/한국어_md.ver.md) | [Korean paper-style report](report/한국어_논문.ver.md) |
| English | [Eng_md.ver.md](report/Eng_md.ver.md) | [Eng_pap.ver.md](report/Eng_pap.ver.md) |

## Project Structure

```
seed-randomness-experiment/
├── README.md                       # English README (this file)
├── README.kr.md                    # Korean README
├── report/
│   ├── 한국어_md.ver.md             # Korean long-form report
│   ├── 한국어_논문.ver.md            # Korean paper-style report
│   ├── Eng_md.ver.md                # English long-form report
│   ├── Eng_pap.ver.md               # English paper-style report
│   └── figures/                    # 7 figures (PNG)
├── output/generation/              # Raw experiment outputs, 30 calls (Exp 1·2 × A/B/C × 5 calls)
├── eval_payload.txt                # Data package sent to the three evaluators
├── eval_gemini_3_1_pro.txt         # gemini-3.1-pro-preview evaluation response
├── eval_codex.txt                  # codex (gpt-5.4) evaluation response
├── queue.json                      # Experiment prompt queue (input to run_batches.py)
├── fill_queue.py                   # 6-layer prompt builder
├── run_batches.py                  # Parallel Gemini CLI batch runner
├── analyze.py                      # Quantitative analysis for Exp 1·2
├── analyze_d.py                    # Analysis for Group D (delusionist)
├── generate_figures.py             # Generates all 7 figures
└── build_eval_payload.py           # Evaluator data package builder
```

## Reproducing the Experiment

Requirements:
- Python 3.12+ (`matplotlib` 3.8+)
- Gemini CLI (with access to `gemini-3-flash-preview` and `gemini-3.1-pro-preview`)
- Codex CLI (optional; used as one of the three evaluators)

```bash
# 1. Generate queue.json (30 tasks = 5 calls × 3 groups × 2 experiments)
python3 fill_queue.py

# 2. Run the batch job — results are saved to output/generation/
python3 run_batches.py

# 3. Run quantitative analysis
python3 analyze.py

# 4. Build the evaluator package, then request evaluation from gemini-3.1-pro-preview / codex
python3 build_eval_payload.py

# 5. Regenerate all 7 figures
python3 generate_figures.py
```

Group D (`delusionist-mini`) runs through a separate pipeline:
- `/Users/jakesmacair/프로젝트 파일/delusionist_factory_personal/mini/`
- Create `request.json` → `python3 run_mini.py`
- Results are saved to `mini/output/`

## Method Summary

| Item | Details |
|---|---|
| Model | `gemini-3-flash-preview` |
| Task 1 | Output five Korean fruits |
| Task 2 | Pro/con essay on "a total smartphone ban in elementary schools" (position + three supporting reasons) |
| Treatment | A: seed prefix / B: plain / C: natural-language instruction / D: delusionist-mini pollution |
| Calls | 5 calls per group × 2 tasks = 10 (Group D uses a separate pipeline) |
| Evaluators | `gemini-3.1-pro-preview`, codex (`gpt-5.4`), claude opus 4.7 — four metrics on a 1-5 scale |

## License

Free to use for research and educational purposes. Attribution is appreciated if you cite it.
