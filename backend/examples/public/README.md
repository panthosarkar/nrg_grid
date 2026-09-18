# Public sample requests

Extracted from the supplied GridWise Public LLM-Assisted Sample Case Pack v2.0.

Use `SAMPLE-01.json` through `SAMPLE-10.json`: these original case inputs use the
supported `operator_notes` array of strings. The old `*-indexed.json` files are
legacy requests for earlier deployments; the updated schema rejects them.

From the repository root, after deploying the string-note update:

```bash
curl --max-time 120 --fail-with-body -sS \
  https://nrg-grid.onrender.com/optimize-energy \
  -H 'Content-Type: application/json' \
  --data-binary @backend/examples/public/SAMPLE-01.json
```

These requests invoke Gemini in default mode, consuming provider quota. Input
acceptance alone does not prove correctness. The prompt now uses end-exclusive
windows, handles irrelevant notes as no_op, and receives battery capacity. Verify
live Gemini interpretations and optimal cost against each reference.
See ../../README.md for reference costs and compatibility details.
