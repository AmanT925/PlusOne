# Text-loop integration

Brain (stream B) is **at the integration point**, not past it.

The four contract functions, three fixture groups, plan scoring, whisper timing, and the fixture leak harness are ready for Core to call. The text loop itself is **not wired yet**: `/server` still uses `stub_write_whisper`, and no phones are talking to the real brain.

Linq, Expo voice, and the leak-counter UI are later integration points (SPEC.md). Skip them for this pass.

## Who does what

| Stream | Change | Don’t change |
|---|---|---|
| **A (Core)** | `context_for`, call Brain, send real `{type: "whisper"}` | `/contracts`, `/brain` |
| **B (Brain)** | Nothing | Already at the handoff |
| **C (Client)** | Later: real websocket instead of a fake server | Not required to prove Brain+Core |

The Expo app is still the default template. First proof is two websocket connections against `/server`, not the phone UI.

## Brain API (already shipped)

From repo root, same import path as `contracts`:

```python
from contracts.schema import Event, ViewerContext
from brain.brain import (
    extract_constraints,
    group_summary,
    write_whisper,
    should_whisper,
    WhisperState,
)
```

| Function | Behavior |
|---|---|
| `extract_constraints(event)` | Only reads `private:<user>` events. Public → `[]`. |
| `group_summary(constraints)` | Anonymous string only. Never includes who needed what. Example: `budget ceiling is about $150`. |
| `write_whisper(viewer_context)` | One or two sentences. Does not name other people as constraint owners. |
| `should_whisper(state)` | True only on a proposal conflict, not mid-sentence, and at least 20s since that viewer’s last whisper. |

`WhisperState` is defined in Brain (not in frozen `contracts/schema.py`). Pass a `WhisperState` or a dict with:

- `public_proposal` — latest public event text
- `viewer_constraints` — that viewer’s constraints only
- `last_whisper_ts` — `None` if never whispered
- `now` — `time.time()`
- `mid_sentence` — `False` until Core tracks “still talking”
- `speaking` — optional alias for mid-sentence

Also available, not on the frozen contract: `score_plan` / `pick_plan`, `token_report`, `python3 -m brain.leak_harness`.

Fixtures: `fixtures/weekend_trip.json`, `fixtures/dinner.json`, `fixtures/extraction_attacks.json`.

```bash
python3 -m unittest brain.test_brain -v
python3 -m brain.leak_harness
```

## What Core implements in `/server`

Keep the existing in-memory event log and websocket connections. Then:

1. **Constraint store.** On each private event, `constraints.extend(extract_constraints(event))`.

2. **`context_for(viewer)`** — this is the privacy boundary. No model may receive anything this function did not build. A whisper may only see:
   - public events
   - that viewer’s `private:<viewer>` events
   - `group_summary(all_constraints)`

   Never put anyone else’s private events into `ViewerContext`.

3. **Replace `stub_write_whisper`.** After each new event:
   - If **public**: broadcast `{type: "public", speaker, text}` as now. For each connected user, if `should_whisper(...)` then `write_whisper(context_for(user))` and send `{type: "whisper", text}` **only on that user’s socket**.
   - If **private**: extract constraints, then maybe whisper **only to that speaker** (same `should_whisper` + `write_whisper`). Do not echo private text to the room.

4. **Per-user `last_whisper_ts`.** Update it when you actually send a whisper, or the 20s rule never works.

5. **Counter** can stay as-is (`shared` / `total`).

### Order of calls

```
append Event
if private: extract_constraints → store
summary = group_summary(all stored constraints)
for each viewer who might get a nudge:
    if not should_whisper(state for that viewer): skip
    text = write_whisper(context_for(viewer))  # only their context
    send whisper to that viewer only
    record last_whisper_ts[viewer]
```

Example `should_whisper` call:

```python
WhisperState(
    public_proposal=latest_public_text,
    viewer_constraints=[c for c in constraints if c.user == viewer],
    last_whisper_ts=last_sent.get(viewer),
    now=time.time(),
    mid_sentence=False,
)
```

## How you know it worked

Run from repo root:

```bash
uvicorn server.main:app --reload
```

Open two websocket clients as `sam` and `priya` on `/ws/{user}`.

1. Sam public:

   `{"type":"utterance","visibility":"public","text":"Cabin this weekend, $300 each"}`

   Both see `{type:"public",...}`. No whisper yet if nobody has constraints.

2. Sam private:

   `{"type":"utterance","visibility":"private:sam","text":"I can't do more than 150 this month"}`

   Only Sam may get `{type:"whisper",...}` (cap / cheaper option). Priya must **not** see that private text.

3. Confirm the whisper never names Priya (or anyone else) as the reason.

That’s the text loop: two people type, tagged public/private, real whisper on screen.

## What not to do in this pass

- Don’t send Brain the full log (other people’s private events).
- Don’t broadcast whispers.
- Don’t wait on Expo, Linq, or voice.
- Don’t edit `/contracts`.
- Don’t edit `/brain` for this wiring — Core only.

## Later integration points (not this pass)

From SPEC.md:

3. **Voice:** Client plugs STT/TTS into the working text loop.
4. **Leak counter:** Brain’s harness against Core’s real server; Client shows attempts vs leaks.

## Websocket shapes (frozen)

Client → server:

```json
{"type": "utterance", "visibility": "public", "text": "..."}
{"type": "utterance", "visibility": "private:<user>", "text": "..."}
```

Server → client:

```json
{"type": "whisper", "text": "..."}
{"type": "public", "speaker": "...", "text": "..."}
{"type": "counter", "shared": 0, "total": 0}
```
