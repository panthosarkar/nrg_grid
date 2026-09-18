# Public sample requests

Extracted from the user-supplied GridWise Public LLM-Assisted Sample Case Pack v2.0.

`SAMPLE-01.json` through `SAMPLE-10.json` contain the original case inputs.
`SAMPLE-01-indexed.json` through `SAMPLE-10-indexed.json` convert operator note
strings to indexed objects for the current backend schema. No reference answers
are included in these requests.

The indexed versions fix request shape only. They do not fix the interpreter's
inclusive time windows, distractor handling, or missing battery-capacity context.
See ../../README.md for the compatibility review and reference costs.

From the repository root:

```bash
curl --max-time 120 --fail-with-body -sS \
  https://nrg-grid.onrender.com/optimize-energy \
  -H 'Content-Type: application/json' \
  --data-binary @backend/examples/public/SAMPLE-01-indexed.json
```

These requests invoke Gemini when the deployment uses its default interpreter;
provider usage and quota apply. Use the original files after the API accepts the
pack's string-based notes.
