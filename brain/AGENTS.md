# Stream B: Brain

Owns: constraint extractor, plan scoring, anonymous group summary, whisper
writer, timing rules, leak-test harness, token logging.

Scope: only edit files under `/brain`. Do not edit `/contracts/*` — those are
frozen; propose changes to the other stream owners instead.

Talks to Core (`/server`) as plain functions that take and return dicts /
dataclasses defined in `contracts/schema.py` (`extract_constraints`,
`group_summary`, `write_whisper`, `should_whisper`).

Work alone by running against fixture groups in `/fixtures` via a test script,
no server needed.
