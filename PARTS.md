# Parts / branches

The work is split into 3 parts, one per stream from `SPEC.md`'s "Roles"
section. Each part is buildable alone against the frozen `/contracts` — that's
why the split is along these lines rather than some other cut.

| Part | Branch | Stream | Folder |
|---|---|---|---|
| Part 1 | `part-1-core` | A: Core | `/server` |
| Part 2 | `part-2-brain` | B: Brain | `/brain` |
| Part 3 | `part-3-client` | C: Voice and client | `/client` |

**If asked to "work on part N":** check out branch `part-N-...` from the table
above (create it from `main` if it doesn't exist yet), then follow the
checklist in that branch's `PART.md` at the repo root. Don't edit `/contracts`
from inside a part branch — those files are frozen and shared by all three
parts; changes need agreement across all three and should happen on `main`.

## Shared / not owned by one part

These aren't any single part's job — whoever's free, or handle together:

- [ ] Does Meta's Official Rules text limit submitting one project to several sponsors?
- [ ] What is the submission deadline?
- [ ] Is the "Plus One" name and a matching domain/repo name free?
- [ ] Has someone already shipped a shared, privacy-aware multi-person agent? (10 min search)
- [ ] Short write-up: who it's for, how it strengthens connection, why AI is essential
- [ ] Final integration pass across all 3 parts (see SPEC.md "Integration points")
