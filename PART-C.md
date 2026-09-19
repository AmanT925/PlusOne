# Part C — Client UI/UX (`feat/client-ux`)

Fork from `dev`. Owns a **revamp of the Expo app** so the in-person fallback looks like the product, not a debug form.

**Do not** edit `/contracts` message shapes (`utterance` / `whisper` / `public` / `counter`). **Do not** change Brain or Linq webhook logic.

## You own

1. **Visual system** — type, color, spacing; room feels like a table, not a terminal. Whisper bubbles vs table messages should be obvious in one glance.
2. **Setup** — name, room, host, fake-server toggle should be secondary (sheet or first-launch), not the whole screen.
3. **Counter** — `shared/total` as the hero (Meta demo). Optional leak `attempts/leaks` if Part A exposed `GET /rooms/{id}/leaks`.
4. **Actions** — Whisper vs Table as two clear intents (hold-to-whisper if it stays reliable).
5. **Empty/error** — connecting, live, error, fake-server labeled in plain language.
6. **Two-phone** — same room, different names, public vs private still obvious.

## Done when

A teammate can join from Expo Go (or web), send Table + Whisper, and understand the privacy story without a walkthrough.

## Files

`/client` only (`App.tsx`, `src/*`, styles). Expo 57: https://docs.expo.dev/versions/v57.0.0/
