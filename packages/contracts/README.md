# PlotWeaver Contracts (Phase 1)

This package is the single source of truth for structured JSON contracts:

- `outline.json`
- `review.json`
- `characters.json`
- `chapter_meta.json`
- `memory_gate.json`

## Versioning

- Global contract version: `1.0.0` (`packages/contracts/constants.py`)
- Every structured JSON payload must include `contract_version`.

## Files

- `models.py`: Pydantic models for runtime validation.
- `adapters.py`: legacy compatibility adapters (`read old`, `write new`).
- `io.py`: normalized read/write helpers.
- `schemas/*.schema.json`: JSON Schema artifacts generated from Pydantic.

## Regenerate JSON Schema

```bash
python -m packages.contracts.generate_schemas
```

