# The AI lane and routing

The AI lane is opt-in, additive, and only ever sees the pages the algorithmic
engine could not resolve. terbium runs fully without it.

## Enabling it

```python
import terbium

ai = terbium.AI(
    anthropic_key="sk-...",   # Claude, preferred when multiple keys are set
    openai_key="sk-...",      # GPT
    kimi_key="...",           # Moonshot Kimi (MOONSHOT_API_KEY / KIMI_API_KEY)
    grok_key="...",           # xAI Grok (XAI_API_KEY / GROK_API_KEY)
    gemini_key="...",         # Gemini
)
doc = terbium.parse("catalogue.pdf", ai=ai)
```

Keys fall back to environment variables, so `terbium.AI()` with no arguments
picks them up. If none are present, the AI lane is simply off and terbium
escalates with a message instead.

Pin a provider when you have several keys:

```python
terbium.AI(provider="openai")   # anthropic | openai | kimi | grok | gemini
```

## Routing

Only hard tables reach the router, and the tier scales with difficulty:

| Difficulty | Tier | Claude | GPT | Kimi | Grok |
|---|---|---|---|---|---|
| trivial | Haiku | `claude-haiku-4-5` | `gpt-4o-mini` | `kimi-k2-turbo-preview` | `grok-3-mini-fast` |
| moderate | Sonnet | `claude-sonnet-5` | `gpt-4o` | `kimi-k2-0711-preview` | `grok-3-mini` |
| hard / very low confidence | Opus | `claude-opus-4-8` | `o3-mini` | `kimi-k2-0711-preview` | `grok-3` |

Difficulty combines the table's confidence, its size, and its column count. Pin a
tier when you want to:

```python
terbium.AI(force_tier="opus")
```

**Provider preference:** when multiple keys are set, terbium uses Claude first,
then GPT, Kimi, Grok, then Gemini. Override with `provider=`.

Install optional SDKs:

```bash
pip install "terbium-parse[anthropic]"   # Claude
pip install "terbium-parse[openai]"      # GPT
pip install "terbium-parse[kimi]"        # Kimi (OpenAI-compatible client)
pip install "terbium-parse[grok]"        # Grok (OpenAI-compatible client)
pip install "terbium-parse[ai]"          # all lanes
```

## Arrange

Each hard table is sent to the routed model with the page's raw text and, for
PDFs, a rendered image of the page. The model returns the corrected matrix as
JSON; terbium rebuilds the table from it and marks those records `origin="ai"`.

## Vision

Some metadata lives only in the pixels: material and care icons (FSC, oiled,
varnished) and finish swatches. Read them explicitly:

```python
info = terbium.read_vision("catalogue.pdf", page=59, ai=ai)
# {"icons": ["FSC", "varnished"], "finishes": ["off white", "ginger", ...]}
```

(For extracting the product photos themselves as files, see
[images.md](images.md) and `terbium.export_images`, which needs no AI.)

**A note on Nano Banana.** Gemini 2.5 Flash Image ("Nano Banana") is an image
generation and editing model, not an extraction one. terbium uses a Gemini or
Claude *vision* model to read imagery. Nano Banana is reserved for optional image
normalization (cleaning a swatch, generating a thumbnail) and is not wired into
the parse path.
