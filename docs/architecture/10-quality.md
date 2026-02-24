# 10. Quality Requirements

## 10.1 Quality Tree

```
Quality
├── Functional Correctness
│   ├── CRS transformations accurate to ±0.01m
│   ├── Contour elevations match DEM values
│   └── Tile selection covers entire AOI
├── Determinism
│   ├── Identical inputs → identical outputs
│   ├── Canonical feature ordering
│   └── Reproducible cache keys
├── Testability
│   ├── Unit test coverage ≥ 80%
│   ├── Integration tests run offline
│   └── E2E tests via CliRunner
├── Performance
│   ├── ≤1 km² at 2m: < 1 min (warm cache)
│   ├── ≤1 km² at 0.5m: < 5 min (warm cache)
│   └── Performance regressions tracked
└── Maintainability
    ├── No circular dependencies
    ├── Each module < 300 LOC
    └── Ruff + mypy clean
```

## 10.2 Quality Scenarios

| ID | Scenario | Measure | Target |
|----|----------|---------|--------|
| QS-1 | Agent modifies contour module | Existing tests pass | 100% |
| QS-2 | Same AOI processed twice | Output files byte-identical | Always |
| QS-3 | AOI in WGS84 submitted | Correctly reprojected to LV95 | ±0.01m |
| QS-4 | Tile download interrupted | Partial file cleaned up; retry works | Always |
| QS-5 | Flat DEM processed | No crash; 0-1 contours returned | Always |
| QS-6 | CI pipeline runs | All tests pass without network | Always |
