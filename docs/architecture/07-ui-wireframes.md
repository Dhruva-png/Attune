# UI Wireframes

Visual language: dark-mode glassmorphism, rounded cards, subtle gradients, micro-animations —
closer to Linear/Arc/Raycast than a typical CV demo. Built in PySide6 with a custom QSS theme
(`dashboard/theme/`) plus Plotly (via `QWebEngineView`) for charts. No OpenCV preview windows are
ever shown — the only camera surface is the styled in-app preview card.

## Shell layout

```
┌──────────────────────────────────────────────────────────────────────────┐
│  ●●●  Attune                                          ⚙  🌙  ⤓ Export    │  ← title bar
├───────────┬──────────────────────────────────────────────────────────────┤
│  ⌂ Live   │                                                              │
│  ◷ Timeline│                     (active view renders here)              │
│  ▤ Analytics│                                                             │
│  ✦ AI Coach│                                                             │
│  ⚙ Settings│                                                             │
│           │                                                              │
│  session: │                                                              │
│  ● 01:24:07│                                                             │
│  [ End ]  │                                                              │
└───────────┴──────────────────────────────────────────────────────────────┘
```

Left rail: icon+label nav, persistent session timer/status pill, primary "Start/End Session"
action always reachable.

## Live view (default screen)

```
┌───────────────────────────────┐  ┌───────────────┐  ┌───────────────┐
│  📷  Camera Preview            │  │  FOCUS SCORE  │  │  STATUS        │
│  (rounded 16px, subtle glow    │  │   ╭───────╮   │  │  🟢 Focused    │
│   ring color = focus score)    │  │   │  82   │   │  │  Looking at    │
│                                 │  │   ╰───────╯   │  │  screen 12m    │
│  landmark overlay OFF by       │  │  animated ring │  └───────────────┘
│  default (opt-in, subtle)      │  └───────────────┘
└───────────────────────────────┘  ┌───────────────┐  ┌───────────────┐
                                     │  FATIGUE       │  │  POSTURE       │
┌───────────────┐  ┌───────────────┐│  🙂 Normal     │  │  ◠  Good       │
│  PHONE ACTIVITY│  │  BREAKS       ││  conf 0.81     │  │  neck 8°       │
│  4 today       │  │  2 · 9m total ││                │  │                │
│  last: 09:41   │  │  longest 6m   │└───────────────┘  └───────────────┘
└───────────────┘  └───────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│  LIVE EVENTS                                                    ⋯    │
│  09:52  Looking at screen                                            │
│  09:48  Phone down · 45s glance                                      │
│  09:47  Phone pickup                                                 │
└──────────────────────────────────────────────────────────────────────┘
```

All cards are translucent glass panels (`rgba` background + backdrop blur), 12–16px radius,
1px hairline border at 8% white opacity, soft drop shadow. Focus ring, status dot, and card
accent colors all derive from the same semantic palette (green=good, amber=caution, red=alert).

## Timeline view

```
┌──────────────────────────────────────────────────────────────────────┐
│  Today · Jul 29                                    [Day][Week][Month]│
│                                                                        │
│  09:00 ●──Started                                                     │
│  09:18 ●──Phone Pickup                            (amber marker)      │
│  09:43 ●──Poor Posture (12m)                       (red marker)       │
│  10:04 ●──Coffee                                                      │
│  10:31 ●──Returned                                                    │
│  ...                                                                   │
│  vertical rail, color-coded dots, hover reveals confidence + metadata │
└──────────────────────────────────────────────────────────────────────┘
```

## Analytics view

```
┌───────────────────────┐ ┌───────────────────────┐
│  Focus Trend (line)    │ │  Posture Trend (line)  │
├───────────────────────┤ ├───────────────────────┤
│  Distraction Heatmap   │ │  Weekly Comparison     │
│  (hour × day grid)     │ │  (grouped bars)        │
├───────────────────────┤ ├───────────────────────┤
│  Focus Radar           │ │  Break Quality         │
│  (gaze/posture/phone/  │ │  (progress rings:      │
│   presence axes)       │ │   count/duration/avg)  │
└───────────────────────┘ └───────────────────────┘
[Daily] [Weekly] [Monthly] toggle · [Export ⤓]
```

All charts render via Plotly inside a themed `QWebEngineView`, styled to match the glass/dark
system (transparent chart background, brand accent colors, animated transitions on data change).

## AI Coach view

```
┌──────────────────────────────────────────────────────────────────────┐
│  ✦ AI Coach                                                          │
│                                                                        │
│  "You consistently lose focus within five minutes of checking        │
│   your phone."                                            conf 0.87  │
│   → based on 14 phone events over the last 7 days   [view evidence]  │
│  ──────────────────────────────────────────────────────────────────  │
│  "Your posture deteriorates after approximately ninety minutes."     │
│                                                             conf 0.79 │
│   → based on posture trend across 6 sessions        [view evidence]  │
│                                                                        │
│  [ Ask about your patterns... ]                                      │
└──────────────────────────────────────────────────────────────────────┘
```

Insight cards, not a generic chatbot — each is evidence-linked (clicking "view evidence" filters
the Timeline view to the referenced events) and shows a confidence pill, never presented as bare
certainty.

## Settings view

Tabbed: **Camera** (device, FPS, resolution) · **Privacy** (cloud AI opt-in, debug frame saving,
data retention) · **LLM Provider** (dropdown: OpenAI/Gemini/Claude/Groq/Ollama, model, API key
field with paste-and-mask) · **Notifications** · **Performance** (inference FPS target, confidence
threshold slider) · **Storage** (DB size, export/clear data) · **Theme**.

## Splash / loading

Centered wordmark, animated gradient breathing background, thin progress indicator, one-line
status text ("Loading vision models…", "Starting camera…") — no console output, no terminal
windows, no OpenCV window ever spawned.

## Design tokens (starting point, refined during dashboard milestone)

- Background: `#0B0D10` → `#14171C` gradient
- Glass card: `rgba(255,255,255,0.04)` fill, `rgba(255,255,255,0.08)` border, `blur(20px)`
- Accent (brand): electric indigo `#6C5CE7` → teal `#00D2A0` gradient
- Semantic: good `#2ECC71`, caution `#F5A623`, alert `#FF5A5F`
- Type: Inter / SF Pro fallback stack, tight tracking on numerals (tabular figures for scores)
