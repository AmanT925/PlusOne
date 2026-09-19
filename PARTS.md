# Branches

Integrated product lives on **`dev`**. The old `part-1-core` / `part-2-brain` / `part-3-client` streams were checklist-only and are **deleted** — their work is already on `dev`.

Remaining hackathon work (see [NEXT.md](NEXT.md)):

| Part | Branch | Plan | Owns |
|---|---|---|---|
| A | `feat/intelligence` | [PART-A.md](PART-A.md) | LLM whispers, group suggestion, tokens, leak API |
| B | `feat/voice-sponsors` | [PART-B.md](PART-B.md) | Grok Voice or Imagine in the product |
| C | `feat/client-ux` | [PART-C.md](PART-C.md) | Expo UI/UX revamp |

Merge back into `dev` for the demo. `/contracts` stays frozen.

**If asked to work on a part:** `git checkout feat/…` from the table (created from `dev`). Don’t edit `/contracts`.
