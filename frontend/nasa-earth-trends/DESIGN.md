# TerraLens design system

The single reference for how the TerraLens frontend looks. Tokens live in
`src/index.css`; components live in `src/App.css` and read only those tokens.
If a value is not in this file, it does not belong in the stylesheet.

## Direction

TerraLens is an evidence tool, not a marketing site. Judges and curious readers
come to check a claim: what changed, by how much, how sure, and from which NASA
record. The interface should feel like a careful agency report that happens to
be interactive.

- **Identity:** agency-style, evidence-first. White working surfaces, deep navy
  structure, one blue for action and selection.
- **Personality:** calm, exact, unhurried. The numbers and the caveats are the
  loudest things on the page.
- **Typeface:** Public Sans for all text, the typeface of the US Web Design
  System, which suits a tool built on NASA records. IBM Plex Mono for numbers,
  IDs, years and units, with tabular figures, so columns of values line up.
- **Theme:** light by default, with a working dark mode toggle. Light suits a
  reading-first tool; dark is offered for presenting in a dim room. Dark mode
  is neutral graphite with no hue in surfaces, text or sidebar. Blue stays only
  as the accent, so in the dark it points at actions and selections alone.

### Dials

| Dial | Value | Meaning here |
| --- | --- | --- |
| ENERGY | 2 | Restrained. Colour is used for state and data, not for mood. |
| RHYTHM | 2 | A dashboard grid. Panels vary in width by content weight, not for variety's sake. |
| MOTION | 2 | Motion explains change: where you went, what is loading, where the map moved, how the series runs. Nothing animates for decoration, and nothing moves on hover. |

## Colour

Five colour roles. Every colour in the stylesheet is one of these tokens.

| Role | Token(s) | Use |
| --- | --- | --- |
| Neutrals | `--canvas`, `--surface`, `--surface-sunken`, `--surface-hover`, `--line`, `--line-strong`, `--ink`, `--ink-2`, `--muted` | Page, panels, inset tiles, borders, text. |
| Structure | `--sidebar-*` | The sidebar. Navy in light mode, near-black graphite in dark mode. |
| Accent (blue) | `--accent`, `--accent-hover`, `--accent-ink`, `--accent-soft`, `--accent-text`, `--focus` | Primary actions, the current selection, links, focus rings, the significant verdict. Nowhere else. |
| Status | `--ok-*`, `--warn-*`, `--danger-*`, `--dot-*` | Real states only: data freshness, warnings, errors, dataset status. Always paired with text. |
| Data | `--chart-*` | Charts and sparklines. Measured series is blue; the supplied trend line is amber and dashed, so it reads without colour. |

Contrast: body text and muted text meet WCAG AA 4.5:1 on `--surface`,
`--surface-sunken` and `--canvas` in both themes. Check new pairs before use.

### What colour never does

- No gradients, glows, radial orbs or background grids.
- No coloured left or top stripes for decoration. A left rule is allowed only
  where it marks a state: the active nav item, a warning, an error, a caveat.
- No translucent or blurred surfaces. Every surface is solid.

## Type scale

| Token | Size | Use |
| --- | --- | --- |
| `--text-2xs` | 11px | Mono metadata only: dataset IDs, slope units in dense tables. |
| `--text-xs` | 12px | Captions, table headers, badges, footnotes. |
| `--text-sm` | 13px | Secondary UI text, nav meta, dense table cells. |
| `--text-md` | 14px | Controls, buttons, panel titles, table cells. |
| `--text-body` | 15px | Running text inside panels. |
| `--text-lg` | 17px | `h3`, card titles. |
| `--text-xl` | 22px | Section headings inside a panel (`h2`). |
| `--text-2xl` | 28px | Page title (`h1`). |

Weights: 400 body, 600 labels and controls, 700 headings. Labels are sentence
case. Uppercase is not used for decoration; tracking stays at 0 except
`-0.01em` on headings.

## Space, shape, elevation

- **Spacing scale:** `--space-1` 4px, `--space-2` 8px, `--space-3` 12px,
  `--space-4` 16px, `--space-5` 20px, `--space-6` 24px, `--space-8` 32px,
  `--space-12` 48px.
- **Radius:** `--radius-sm` 4px for badges and inner items, `--radius` 6px for
  controls, buttons and inset tiles, `--radius-lg` 8px for panels. Fully round is
  for the theme switch and status dots only.
- **Elevation:** panels sit flat on the canvas with a 1px border. Only things
  that float above content get `--shadow-pop`: dropdown menus, the window
  popover, and the map overlays.

## Components

| Component | Rule |
| --- | --- |
| Panel | `--surface`, 1px `--line`, `--radius-lg`. Header shares the body colour and is split by a 1px line. Title is 14px semibold, sentence case. |
| Inset tile | Evidence cells, glossary items, compare cards, region cards: `--surface-sunken`, 1px `--line`, `--radius`. |
| Stat tile (KPI) | A panel with a label, a mono value and a note. No coloured edge. Four across on wide screens, two on tablets, one on phones. |
| Button | Primary: solid `--accent`. Secondary: `--surface` with a `--line-strong` border and `--accent-text`. 36px minimum height. No shadows, no lift on hover. |
| Control | Dropdown triggers, the window chip and segmented controls share one shape: `--surface`, `--line-strong` border, `--radius`. |
| Selected state | Segmented option, window year, active case tab: `--accent` fill or an `--accent` border with `--accent-soft` fill. |
| Verdict badge | Significant: solid accent. Weak evidence: warn tint. No clear trend: neutral outline. Not enough data: dashed outline. Text always names the verdict. |
| Callout | Notes use `--surface-sunken`. Caveats and cautions add a 3px `--warn-line` left rule because they mark a limitation. |
| States | Empty: dashed border, says why it is empty. Loading: spinner plus what is loading. Error: `--danger` tint and rule, with the message. |
| Map | Study boxes in slate, the selected box in accent blue. Overlays are solid surfaces with `--shadow-pop`. |

## Motion

Every animation answers a question the reader has at that moment.

| Moment | Motion | Token | Why |
| --- | --- | --- | --- |
| Hover, focus | Colour, border and background ease | `--duration`, `--ease` | Confirms the element responds. Nothing moves position. |
| Page change | The new page fades in and rises 8px, once | `--duration-enter`, `--ease-out` | Marks that the view changed without hiding the content. |
| Data request in flight | A thin accent bar runs under the top bar, after 150ms | `--ease-in-out` | Says the app is working, without flashing on cached pages. |
| Panel loading | A small trend line draws itself beside the loading label | `--duration-draw` | Names what is loading, in the product's own shape. |
| Lineup loading | Skeleton rows in the exact layout of the real rows, pulsing | n/a | Holds the space the results will fill, so nothing jumps. |
| Region change | The map flies from the old region to the new one | MapLibre `flyTo` | Shows where the new region sits relative to the last one. |
| Chart appears | The measured series draws left to right, then the trend line | `--duration-draw` | Reads like time passing, the way the record is read. |

Loops run only while their loading state is on screen.
`prefers-reduced-motion` turns every animation into its end state: the map
jumps, the chart appears drawn, and the loaders show a static form.

## Accessibility

- Every interactive element shows a 2px `--focus` outline on keyboard focus;
  the sidebar uses its own lighter focus colour.
- Status is never colour alone: dots sit next to a text label, verdicts are
  words.
- Both themes are checked for contrast and for every component before merging.
