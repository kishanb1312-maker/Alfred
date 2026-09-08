# Running Alfred's worker so your laptop can be off

Tapping **Approve** in Telegram only does something if a machine somewhere is listening.
Before this, that machine was your laptop, and only while a run happened to be going —
which is why an Approve at midnight got you a Notion status change and silence.

The **worker** (`scripts/alfred_worker.py`) is a small process whose only job is to stay
awake and listen. Put it on anything that never sleeps, and this works with your laptop
shut:

| You tap | What happens, laptop off |
|---|---|
| ✅ Approve | The email preview card arrives in seconds |
| ✏️ Edit | You reply, the rewritten preview comes back |
| 📧 Send | **The email actually goes out**, and you get the ✅ confirmation |
| 🚫 Cancel | Recorded. Your portal application is untouched |
| `/pause` | Everything stops until `/resume` |

## What the worker cannot do (and why)

- **Portal applications.** LinkedIn Easy Apply, Workday and friends need *your* signed-in
  browser. No server has your session, and driving one from a datacenter IP is the fast
  lane to a banned LinkedIn account. Portal applications still happen on your laptop, on
  your normal Alfred run. **The worker is the email half only.**
- **Finding, researching and tailoring jobs.** Those need Claude. The worker only serves
  decisions on work your laptop already prepared.
- **Notion.** No MCP connector out here. Notion catches up on your next laptop run, from
  the decision records the worker wrote.

So the shape is: **laptop prepares, worker converses and sends.**

## What the worker needs

A copy of your Alfred home — `~/.alfred`, or wherever `$ALFRED_HOME` points:

```
~/.alfred/
  .env                 the 4 secrets (0600)
  config/search.yaml   dry_run + caps.emails_per_day — the worker obeys both
  data/                staged drafts, decisions, offset, flags
  output/              the tailored PDFs it attaches
```

Attachment paths inside `email_drafts.json` are stored **relative to the Alfred home**, so
a draft staged on your laptop resolves correctly on the worker. Copying the folder is
genuinely all it takes.

### Keeping it in sync

Your 6PM run stages new drafts and PDFs on the laptop. Push them after each run:

```bash
rsync -az --delete ~/.alfred/ alfred@your-host:~/.alfred/
```

Pull the decisions back before the next run, so Notion and the portal channel see them:

```bash
rsync -az alfred@your-host:~/.alfred/data/ ~/.alfred/data/
```

Two machines writing the same `data/` will fight, so keep it one-way at a time: push after
a run, pull before the next one. If that bookkeeping annoys you, put the Alfred home on
the worker and mount it back — or just accept the worker as the source of truth for
`data/` and only ever push `output/`.

## Where to run it

**A Raspberry Pi or an old laptop at home** — cheapest, and your Gmail app password never
leaves your house. Use the systemd unit.

**A small VPS** (~$5/mo) — most reliable. Same systemd unit.

**A container platform** (Fly.io, Railway, Render) — least setup, but the free tiers sleep
idle containers, and a sleeping worker *is the original bug*. Check yours stays awake, and
that its disk persists across deploys or your staged drafts vanish.

### systemd (Pi / VPS)

```bash
sudo cp deploy/alfred-worker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now alfred-worker
journalctl -u alfred-worker -f
```

Edit `User=` and the paths in the unit first. It restarts on crash and on reboot, and
handles SIGTERM so a restart never lands mid-send.

### Docker

```bash
docker build -t alfred-worker -f deploy/Dockerfile .
docker run -d --name alfred-worker --restart unless-stopped \
    -v "$HOME/.alfred:/data" --env-file "$HOME/.alfred/.env" alfred-worker
```

Secrets go in at run time via `--env-file`. Never `COPY` a `.env` into the image — it gets
baked into a layer and travels with every copy of it.

> The image was written and reviewed but **not built in the environment that produced it**
> (no Docker daemon available there). The systemd path and the worker itself were run and
> tested directly. If the build hiccups, it will be something small in the base image —
> the worker needs only `requests` and `PyYAML`.

## Before you let it send anything

1. **Leave `dry_run: true` in `config/search.yaml` for the first day.** The worker runs the
   entire flow and sends you the 🧪 DRY RUN card showing exactly what *would* have gone out.
   Nothing reaches a recruiter.
2. Smoke-test one cycle: `python scripts/alfred_worker.py --once`
3. Check state without touching the network: `python scripts/alfred_worker.py --status`
4. When the dry-run cards look right, set `dry_run: false`.

`--no-send` is the middle setting: cards and edits work, sending never happens.

## The guardrails that hold out here

Every one of these refuses **before** SMTP is opened, and each is proven in
`scripts/dry_run_worker.py` with the send function patched to explode:

- **Only on an explicit Send tap.** No decision, or Cancel, means no email. Ever.
- **Send once.** `data/email_sent.json` — a restart, a duplicate tap, or an overlapping
  laptop run cannot send the same email twice.
- **`/pause`** halts everything; **`data/email_paused.flag`** (the bounce throttle) halts
  email only.
- **`caps.emails_per_day`** is counted and enforced.
- **`dry_run`** blocks real sends — and an unreadable `search.yaml` is read as `dry_run: true`,
  so a broken config can never be the reason something got sent.
- **Gives up after 3 failed attempts** rather than retrying and re-notifying forever.

## When something looks stuck

```bash
python scripts/alfred_worker.py --status
```

- `pending_email_previews` — approved jobs whose preview card never went out.
  `python scripts/approval_poll.py --sweep` sends them.
- `cleared_unsent` — emails you tapped Send on that have not gone. The worker retries
  these each cycle; if one is stuck, `journalctl -u alfred-worker` (or `docker logs`) says
  why: cap reached, paused, throttled, or a real SMTP error.

One caveat worth knowing: **Telegram drops un-fetched taps after 24 hours.** That is only a
risk while no worker is running. Once it is up, taps are collected within seconds. If you
ever do lose one, the review card is still in your chat — just tap it again.
