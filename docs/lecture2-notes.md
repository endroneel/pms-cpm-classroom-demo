# Lecture 2: Project costing and crashing

Open `lecture2.html`, or select **Lecture 2 · Costing & crashing** on the existing site's header. GitHub Pages continues to publish `main /docs`; no settings changes are required.

Source: *PGE PM Lecture 2 Indranil BISWAS.pptx*, provided by the instructor. The slides themselves are not published with the module.

## Coverage

- Slides 6–17: Projects A–D; CV, SV, CPI, SPI, forecast total cost, forecast months and percentage changes.
- Slides 19–26: the A–G crash network, four complete paths, manual plans, slide plans, exhaustive whole-week optimization and deadline penalties.
- Hide/reveal answers, editable numerical inputs, JSON save/open, reset and an instructor guide.

The crash topology is fixed to the lecture example. Numerical data are editable; all crash choices use whole weeks. The solver enumerates all feasible combinations (324 for the original data), with a 200,000-plan limit for modified inputs. It shows one optimal allocation for each attainable duration and counts tied allocations. Original project cost is unspecified; the objective compares incremental crash and penalty costs.

## Full-precision earned-value results

| Project | CV | SV | CPI | SPI | Forecast total cost | Forecast months |
|---|---:|---:|---:|---:|---:|---:|
| A | 10 | 20 | 80/70 | 80/60 | 262.50 | 6 |
| B | -10 | -30 | 40/50 | 40/70 | 500 | 21 |
| C | -10 | 10 | 80/90 | 80/70 | 247.50 | 7.875 |
| D | 10 | -30 | 60/50 | 60/90 | 83.333333… | 15 |

The deck rounds indices before deriving some forecasts. The module preserves full precision. Zero-denominator indices and forecasts that divide by a zero or undefined performance index are marked undefined. PV and EV cannot exceed the original budget under the exercise's fixed-scope assumption. SPI is a value-based indicator; dividing planned months by SPI is the lecture's approximation, not a critical-path forecast.

## Crash-plan comparison

The four complete paths are A–D–G, B–G, C–E–G and A–F. A and G are shared: costs cannot be assigned independently to paths. Both terminal activities F and G must finish.

| Completion weeks | Least extra cost | One optimal crash allocation | Slide extra cost |
|---|---:|---|---:|
| 12 | $0 | None | — |
| 11 | $4,000 | D: 1 | — |
| 10 | $8,000 | D: 2 | — |
| 9 | $16,000 | A: 1, D: 1, G: 1 | $19,000 |
| 8 | $26,000 | A: 1, D: 1, F: 1, G: 2 | $29,000 |
| 7 | $39,000 | A: 1, B: 1, D: 2, F: 2, G: 2 | $39,000 |

These optima were cross-checked with an independent linear program using all four path-duration constraints. The source plans are retained and explicitly labelled as feasible lecture plans rather than least-cost plans.

For deadline week 8 and penalty $10,000 per late week, 8 and 9 weeks tie at $26,000 under optimized plans. The original slide plans tie at $29,000. The $2,750 threshold in slide 26 compares *average extra cost per week saved*, not total incremental cost. The app distinguishes the objectives and compares every attainable duration when selecting a cost-minimizing plan.

## Files

`lecture2.html`, `lecture2.css`, `lecture2-engine.js`, and `lecture2-ui.js` must stay together. They use no external dependencies and work offline. Inputs stay in memory until you save a JSON file; no information is sent to a server.
