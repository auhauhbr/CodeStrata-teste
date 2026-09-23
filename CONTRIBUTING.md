# Contributing to CodeStrata

Thanks for helping improve the excavation kit.

## Development setup

```bash
git clone https://github.com/JeffersonSantosKn/CodeStrata.git
cd CodeStrata
PYTHONPATH=src python -m unittest discover -s tests -v
```

The runtime intentionally relies on the Python standard library. Keep new mandatory dependencies rare and justified.

## Adding a detector

1. Add a detector module under `src/codestrata/detectors/`.
2. Emit `Evidence` objects rather than final confidence values.
3. Prefer deterministic, inspectable signals.
4. Register the detector in `detectors/registry.py`.
5. Add tests covering strong and weak evidence.

### Evidence guidance

- Manifest dependency: usually 75–90.
- Dedicated framework/config file: usually 50–80.
- Lockfile/package-manager marker: usually 80–95.
- Source import/API signature: usually 15–30.
- Generic CSS class or ambiguous string: keep below the default confidence threshold unless corroborated.

A single ambiguous pattern should not become a confident detection.

## Pull requests

Keep changes focused, explain the evidence rule being introduced, and include tests for false positives when a pattern is ambiguous.

Run before opening a PR:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m compileall -q src
```
