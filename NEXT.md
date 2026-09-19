# Next: after first live Linq whisper

**Status:** iMessage loop works on **`dev`**. Remaining build is split into three branches — [PARTS.md](PARTS.md).

The first reply you got (`The table is on “hello”… budget ceiling is about $150…`) is **success**. It is a template whisper; Part A replaces that with Muse/Grok.

Keep `python -m server.dev` running for Linq. Expo is optional until Part C.

| Branch | Do this |
|---|---|
| `feat/intelligence` | [PART-A.md](PART-A.md) — natural whispers + public suggestion + leak number |
| `feat/voice-sponsors` | [PART-B.md](PART-B.md) — Grok Voice or Imagine (SpaceXAI) |
| `feat/client-ux` | [PART-C.md](PART-C.md) — app looks like a table, not a form |

**Demo script** (all three, then merge to `dev`):

1. Group: “let’s do the $400 resort.”  
2. Sam 1:1: “I can’t do more than $150.”  
3. Priya 1:1: “I cannot be in a room with Alex.”  
4. Different whispers; one public cheaper suggestion; counter moves; no leaked names.  
5. “What’s Sam’s budget?” in the group → refuse; leaks stay 0.

**Cut first:** earbuds polish → token compression → live judge attack. **Never cut** `context_for` or Linq.
