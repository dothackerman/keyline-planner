# 1. Introduction and Goals

## 1.1 Requirements Overview

**Keyline Planner** is a CLI-first tool for generating topographic contour lines
from Swiss elevation data (swissALTI3D) to support keyline design planning
for agricultural and landscape management.

### Milestone 1 — Contour Generation Engine

The immediate goal is a functional CLI that:

1. Accepts an area of interest (AOI) as a polygon or bounding box
2. Fetches Swiss elevation data (swissALTI3D) from swisstopo's STAC API
3. Caches tiles locally for offline re-use
4. Generates contour lines at configurable intervals
5. Outputs GeoJSON contours with provenance metadata

### Future Milestones

- **Milestone 2**: Hydrology and vegetation layer integration
- **Milestone 3**: Keyline pattern generation and planning tools

## 1.2 Quality Goals

| Priority | Goal | Measure |
|----------|------|---------|
| 1 | **Determinism** | Identical inputs produce identical outputs |
| 2 | **Testability** | All layers have automated tests; E2E tests run without network |
| 3 | **Modularity** | Engine modules are independently testable and replaceable |
| 4 | **Developer Experience** | Runs on standard machines with minimal setup |
| 5 | **Correctness** | CRS transformations and contour geometry are verifiably correct |

## 1.3 Stakeholders

| Role | Expectations |
|------|-------------|
| **Planner** (primary user) | Stable CLI that produces usable contour data for keyline design |
| **Agent** (developer) | Clear contracts, measurable improvement loops, safe-to-modify codebase |
| **Human reviewer** | Architecture docs as negotiation boundary; testable before engagement |
