# Part A — Intelligence (`feat/intelligence`)

Fork from `dev`. Owns **Brain + Core routing** so whispers and group suggestions feel like a product.

**Do not** edit `/contracts`. **Do not** rebuild Expo UI (that is `feat/client-ux`). **Do not** add Grok Voice/Imagine playback (that is `feat/voice-sponsors`).

## You own

1. **LLM `write_whisper`** — Muse Spark (`MUSE_API_KEY`) first, Grok chat (`XAI_API_KEY`) fallback, template last. Input is **only** `ViewerContext` from `context_for`. 1–2 sentences. No other people’s names or private quotes.
2. **Public suggestion** — on conflicting public talk, `pick_plan` → `maybe_public_suggestion` to the **group** Linq thread + `{type: public, speaker: plus-one}`. Never “Sam’s budget.”
3. **Token log** — every LLM call (`brain/tokens.py`): prompt/completion tokens, route `muse|grok|regex`. One script: fixture with vs without LLM (Token Company).
4. **Leak proof** — extend `brain/leak_test.py`; `GET /rooms/{id}/leaks` with `{attempts, leaks}` for the laptop judge screen.

## Done when

Texting `$150` returns a natural nudge, not “The table is on hello.” A `$400` group message can produce one cheaper public suggestion. Leak harness still 0 leaks.

## Files

`/brain/*`, `/server/rooms.py`, `/server/brain_adapter.py`, `/server/main.py` (leaks route only), `/fixtures`, `/server/tests`, `/brain/tests`.
