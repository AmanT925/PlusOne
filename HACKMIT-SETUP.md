# HackMIT setup — what to get, in order

Do these **on your laptop at the venue**. Do not paste keys into Slack/Discord/git. Put them in the repo-root `.env` only.

Plus One should submit to **Meta** (main), **SpaceXAI**, **The Token Company**, and optionally **Long Lake**. Linq is our iMessage channel, not a prize in this sponsor list. Skip Maximor / Voloridge / Visa / etc. unless you have leftover time.

Grok **Bot ≠** Grok **Voice/Imagine API**. SpaceXAI requires Cursor (you have it) **and** Imagine **or** Voice API. Bot is bonus only.

---

## 0. Confirm this repo

```powershell
cd C:\Projects\PlusOne
git checkout dev
```

`.env` already has `LINQ=...`. Add new keys on new lines. Never commit `.env`.

---

## 1. Meta Muse (do this first — $50 HackMIT credits)

**Why:** whispers (Muse Spark) and later earbud STT (Muse Voice Transcribe). Required for a strong Meta submission.

1. Open HackMIT Discord / Meta booth / the “redemption instructions” link in the sponsor doc (the word **here** next to $50 credits). Use **the same email** as your HackMIT registration if they say so.
2. Create a developer account: [https://dev.meta.ai](https://dev.meta.ai)
3. Redeem the HackMIT $50 code if you have one. If the form isn’t live yet, signup still usually grants a smaller preview credit — use it.
4. In the dashboard: **API keys → Create**. Copy once.
5. In `.env`:

```text
MUSE_API_KEY=...
# Meta Model API is OpenAI-compatible:
# base URL https://api.meta.ai/v1
# model muse-spark-1.1
```

6. If Transcribe is a separate product in the console, create that key too (`MUSE_TRANSCRIBE_KEY`) or note the same key works.

**Booth backup:** walk to Meta, say you’re submitting “Bringing People Closer Together,” ask them to watch you redeem.

---

## 2. SpaceXAI Grok API (required for that prize)

**Why:** Voice **or** Imagine must appear **in the project**, not only in Cursor chat.

### 2a. API key (required)

1. Go to [https://console.x.ai](https://console.x.ai) → Sign in (X / Google / same account they tell you at the booth).
2. Add credits if the console is empty. Ask the **SpaceXAI booth** if HackMIT has a credit code.
3. **API Keys → Create**. Copy.
4. In `.env`:

```text
XAI_API_KEY=...
```

5. Quick check (PowerShell):

```powershell
curl https://api.x.ai/v1/models -H "Authorization: Bearer $env:XAI_API_KEY"
```

You should see a JSON model list, not 401.

### 2b. Voice API (best fit for Plus One)

Docs: [Voice](https://docs.x.ai/developers/model-capabilities/audio/voice)

- TTS: `POST https://api.x.ai/v1/tts` (whisper playback in the earbud)
- Optional realtime: `wss://api.x.ai/v1/realtime?model=grok-voice-latest`

Same `XAI_API_KEY`. No second key.

### 2c. Imagine API (fallback if Voice is blocked)

If Voice isn’t enabled on the student account, generate **one** image or clip in the demo (e.g. a still of the trip the group picked) via [Imagine](https://docs.x.ai/developers/model-capabilities/imagine) so you still qualify. Same key.

### 2d. Grok Bot (bonus only — not a substitute)

1. Eligible Cursor plan (Pro / Ultra / Teams as listed).
2. Download **Grok Bot** from the Cursor dashboard “Download Grok Bot” row, or [getting started](https://cursor.com/docs/grok-bot/get-started).
3. Sign in with the **same Cursor account**.
4. **Create a Bot**: name `Plus One`, job “plan hackathon work, keep the privacy boundary, don’t leak private constraints.”
5. First task: “Read PLAN.md and list tonight’s build order.” Screenshot that chat for the SpaceXAI demo.

Bot does **not** replace `XAI_API_KEY`.

---

## 3. Linq iMessage (product channel, not a listed prize)

**One command:** [LINQ-SETUP.md](LINQ-SETUP.md) — `python -m server.dev`

You already have: API key in `.env` as `LINQ=`, number **+1 (949) 278-3794**.

Add:

```text
LINQ_FROM=+19492783794
```

### 3a. ngrok (HTTPS so Linq can reach your PC)

1. Sign up: [https://dashboard.ngrok.com/signup](https://dashboard.ngrok.com/signup)
2. Install: [https://ngrok.com/download](https://ngrok.com/download) or `winget install ngrok.ngrok`
3. Auth:

```powershell
ngrok config add-authtoken YOUR_NGROK_TOKEN
```

(Token is on the ngrok dashboard after signup.)

4. With uvicorn already on 8000:

```powershell
ngrok http 8000
```

5. Copy the `https://….ngrok-free.app` URL. It **changes** every time you restart ngrok unless you pay for a domain.

### 3b. Webhook subscription (= how you get the secret)

Keep ngrok **and** `uvicorn` running. Then:

```powershell
cd C:\Projects\PlusOne
# Use the same token as LINQ= in .env
$ngrok = "https://YOUR_SUBDOMAIN.ngrok-free.app"
$key = (Get-Content .env | Where-Object { $_ -like 'LINQ=*' }) -replace '^LINQ=',''

curl https://api.linqapp.com/api/partner/v3/webhook-subscriptions `
  -H "Authorization: Bearer $key" `
  -H "Content-Type: application/json" `
  -d "{`"target_url`":`"$ngrok/linq/webhook?version=2026-02-03`",`"subscribed_events`":[`"message.received`"]}"
```

Or in Linq **sandbox UI**: Webhooks → New → URL `https://…/linq/webhook?version=2026-02-03` → event `message.received`.

6. Response includes `signing_secret`: `whsec_...` **once**. Add to `.env`:

```text
LINQ_WEBHOOK_SECRET=whsec_...
```

7. Restart uvicorn so it loads the secret.
8. Text **+19492783794** from your phone: “I can’t do more than $150”. Watch uvicorn logs / `GET http://localhost:8000/rooms/demo/events`.

If ngrok URL changes, create a **new** subscription (or update the old one) with the new URL.

---

## 4. Volunteer phones (“names”)

Optional until you mix Expo + iMessage.

For each person who will text Plus One, collect:

| Display name (app) | Their cell, E.164 |
|---|---|
| sam | +1XXXXXXXXXX |
| priya | +1XXXXXXXXXX |

Then in `.env`:

```text
PLUSONE_HANDLES=sam:+1XXXXXXXXXX,priya:+1YYYYYYYYYY
```

Your Linq line is **not** listed here. Only human phones.

If you skip this, iMessage users show up as `+1…` in the log. That’s fine for a two-phone iMessage demo.

---

## 5. The Token Company (do after Muse/Grok work)

1. Friday unlock: [https://thetokencompany.com](https://thetokencompany.com) — sign in when they enable it.
2. Grab a compression API key if they issue one → `TOKEN_COMPANY_KEY=`
3. We log tokens with vs without compression in the product (not just while coding).

---

## 6. Optional voice backups (only if Grok Voice or Muse Transcribe fail)

- **Deepgram:** [https://console.deepgram.com/signup](https://console.deepgram.com/signup) — $200 HackMIT credit. Qualifies for Deepgram prize if we call their API.
- **ElevenLabs:** booth / elevenlabs.io API key — agentic voice prize; overlaps earbuds.

Don’t sign up until Meta + Grok Voice are blocked.

---

## 7. Optional: Devin / OpenAI / Codex (prize checkboxes)

- **Devin (Cognition):** give Devin the leak-test harness or the laptop leak-counter screen. Screenshot the Devin session for the demo.
- **OpenAI:** only if you want that prize; needs their API + “Codex as teammate.” Conflicts with “keep Brain on Muse/Grok.” Skip unless you have spare time.

---

## 8. Meta submission artifacts (start a folder, fill later)

You will need:

- Working prototype (this repo)
- 2–3 minute demo video
- Public GitHub
- Short write-up: who it’s for, how it strengthens connection, why AI is essential

SpaceXAI: mention Cursor + Grok Voice (or Imagine) + Bot screenshot.

---

## What “done getting keys” looks like

`.env` has at least:

```text
LINQ=...
LINQ_FROM=+19492783794
LINQ_WEBHOOK_SECRET=whsec_...
XAI_API_KEY=...
MUSE_API_KEY=...
```

Then tell me the ngrok HTTPS URL (not the keys) and I can wire subscribe + LLM whispers on `dev`.

---

## Tonight’s order if time is short

1. Muse key  
2. `XAI_API_KEY` + one Voice **or** Imagine call in the app  
3. Grok Bot screenshot  
4. ngrok + Linq webhook secret  
5. Two phones text `+19492783794`  
