# The AI lane and routing

The AI lane is opt-in, additive, and only ever sees the pages the algorithmic
engine could not resolve. terbium runs fully without it.

## Enabling it

```python
import terbium

ai = terbium.AI(anthropic_key="sk-...", gemini_key="...")   # or read from env
doc = terbium.parse("catalogue.pdf", ai=ai)
```

Keys fall back to `ANTHROPIC_API_KEY` and `GEMINI_API_KEY`, so `terbium.AI()` with
no arguments picks them up. If neither is present, the AI lane is simply off and
terbium escalates with a message instead.

## Routing

Only hard tables reach the router, and the tier scales with difficulty:

| Difficulty | Tier | Model id |
|---|---|---|
| trivial | Haiku | `claude-haiku-4-5` |
| moderate | Sonnet | `claude-sonnet-5` |
| hard / very low confidence | Opus | `claude-opus-4-8` |

Difficulty combines the table's confidence, its size, and its column count. Pin a
tier when you want to:

```python
terbium.AI(force_tier="opus")
```

If only a Gemini key is present, terbium uses `gemini-2.5-flash` / `gemini-2.5-pro`
for the same tiers.

## Arrange

Each hard table is sent to the routed model with the page's raw text and, for
PDFs, a rendered image of the page. The model returns the corrected matrix as
JSON; terbium rebuilds the table from it and marks those records `origin="ai"`.

## Vision

Some metadata lives only in the pixels: material and care icons (FSC, oiled,
varnished) and finish swatches. Read them explicitly:

```python
info = terbium.read_images("catalogue.pdf", page=59, ai=ai)
# {"icons": ["FSC", "varnished"], "finishes": ["off white", "ginger", ...]}
```

**A note on Nano Banana.** Gemini 2.5 Flash Image ("Nano Banana") is an image
generation and editing model, not an extraction one. terbium uses a Gemini or
Claude *vision* model to read imagery. Nano Banana is reserved for optional image
normalization (cleaning a swatch, generating a thumbnail) and is not wired into
the parse path.
