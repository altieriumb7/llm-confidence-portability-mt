# Reproducibility

Canonical reviewer documentation lives in `REPRODUCIBILITY_CHECKLIST.md`.

## Levels

- **Level A (claimed):** deterministic offline regeneration from bundled snapshot artifacts.
- **Level B (claimed):** deterministic consistency/wiring validation checks.
- **Level C (not claimed in artifact-only mode):** live provider/API reruns with external dependencies.

## One-command reviewer run (A+B)

```bash
bash scripts/reproduce_offline_artifact.sh --skip-manuscript
```

## Checksum verification

```bash
sha256sum -c CHECKSUMS.sha256
```

## Boundary statement

This bundle intentionally does not claim full live end-to-end reproducibility because provider outputs and infrastructure are external and time-varying.
