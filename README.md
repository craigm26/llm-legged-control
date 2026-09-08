# An LLM at 50 Hz

A checkable answer to the challenge posed by @JitendraMalikCV on 7 September 2026:
"Can you prompt an LLM to output the high frequency control commands for a
legged robot in varying terrain?"

Live page: https://craigm26.github.io/llm-legged-control/

- `index.html` is the write-up with figures, tables, limitations and references.
- `data/` holds every episode (`results.json`), the LLM's literal 50 Hz command
  table (`commands_open_loop.csv`), the measured standing targets
  (`neutral.json`) and the run log.
- `sim/` holds the scripts. They run inside
  [craigm26/duckbench](https://github.com/craigm26/duckbench) `sim/` (which
  carries the MuJoCo plant, the ONNX policies and `node_modules`); a copy also
  lives there as `sim/malik/`.
- `build.py` regenerates `index.html` from the data.

Built by Craig Merry pairing with Claude Code. No GitHub Actions: this is
classic branch-based GitHub Pages, published on push to `main`.
