## What changed?

Describe the change and the user-facing behavior.

## Evidence rules

If this adds or changes a detector, explain why each signal is strong or weak enough for its assigned weight.

## Verification

- [ ] `PYTHONPATH=src python -m unittest discover -s tests -v`
- [ ] `PYTHONPATH=src python -m compileall -q src`
- [ ] I considered false positives for new source signatures.
