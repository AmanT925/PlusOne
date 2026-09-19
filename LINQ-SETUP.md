# Linq — one command

Ngrok authtoken is already set. From the repo root:

```powershell
cd C:\Projects\PlusOne
python -m server.dev
```

That starts ngrok on port 8000, points Linq at `…/linq/webhook?version=2026-02-03`, saves `LINQ_WEBHOOK_SECRET` to `.env` (never printed), then starts the server. Leave the window open.

**Phone test:** text **+1 (949) 278-3794** (1:1, not a group):

```text
I can't do more than $150
```

Then open [http://127.0.0.1:8000/rooms/demo/events](http://127.0.0.1:8000/rooms/demo/events) — you should see a `private:…` row. Ngrok inspector: [http://127.0.0.1:4040](http://127.0.0.1:4040).

Ctrl+C stops both processes. If you already have uvicorn or ngrok running, close those first so port 8000 / 4040 are free.
