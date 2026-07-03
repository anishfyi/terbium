# Confidence and escalation

Confidence is the feature. terbium refuses to pretend a shaky parse is solid, and
that honesty is what lets it decide when AI is worth the cost.

## How a table is scored

Every reconstructed table starts at ~0.98 and loses points for real problems:

| Signal | Penalty |
|---|---|
| No finish/column headers detected | -0.14 |
| No product title above the table | -0.10 |
| Sparse matrix (cells missing) | up to -0.35, scaled by how empty |
| Rows that do not line up with the columns | up to -0.20 |

A single-column list is exempt from the column penalties, because "one finish, no
header" is normal, not a failure. The final score is clamped to `[0.05, 1.0]` and
attached to the table and to every record it produces, along with `reasons`.

## The threshold

`parse(threshold=0.72)` sets the line between confident and ambiguous. It affects
only labelling and escalation; every record keeps its raw score, so you can apply
your own cut:

```python
solid = [r for r in doc.records if r.confidence >= 0.9]
```

## Escalation

When one or more tables fall below the threshold:

- **With an AI key** - only those tables are sent to the routed model, rebuilt,
  and their records marked `origin="ai"`.
- **Without a key** - terbium attaches a message to `doc.escalation` and, if
  `announce=True`, prints it to stderr:

```
terbium: 712/725 records parsed confidently.
3 table(s) on page(s) 15, 26, 30 are ambiguous (...).
-> set ANTHROPIC_API_KEY or pass ai=terbium.AI(...)   recommended tier: Sonnet
```

It never fails silently, and it never bills you for the easy pages.
