# 11. Risks and Technical Debt

## 11.1 Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| GDAL version drift causes output differences | Medium | High | Pin GDAL version in CI; tolerance-aware test comparisons |
| STAC API schema changes | Low | Medium | Isolate STAC interaction in `tiles.py`; mock in tests |
| Large AOI causes OOM or timeout | Medium | Medium | AOI size warnings; default 2m resolution; bounded tile count |
| CRS transformation edge cases | Low | High | Explicit CRS validation; Swiss territory bounds check |
| swisstopo licensing terms change | Very Low | Low | Attribution in all outputs; OGD terms are stable |

## 11.2 Current Technical Debt

| Item | Severity | Plan |
|------|----------|------|
| No GDAL version pinning in pyproject.toml | Medium | Add Dockerfile or conda lock file |
| Temporary files not always cleaned up | Low | Add cleanup in pipeline finally block |
| No retry logic for tile downloads | Low | Add exponential backoff in cache.py |
| No CLI progress bars for long operations | Low | Add Rich progress bars in Milestone 1.1 |
| STAC API URL hardcoded | Low | Move to configuration file |
