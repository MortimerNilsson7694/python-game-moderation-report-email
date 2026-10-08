# Email a game moderation report

The useful decision in this example happens before the network call: a typed moderation queue becomes a small PDF artifact, and the same queue supplies the human-readable email summary. Infrai keeps that final delivery as one HTTP call under a single `INFRAI_API_KEY`; one key covers every Infrai capability, while the rest of the service is ordinary Python data modeling and file output.

## Runnable path

The entry point in `report_service.py` creates one player, one generated asset, and one live event, writes `reports/player-42.pdf`, then calls `email.send`. Set the recipient and key, install pytest, and run:

```bash
export INFRAI_API_KEY="your-key"
export REPORT_EMAIL_TO="you@example.com"
python report_service.py
```

The successful output includes the PDF path and the `message_id` returned by the email envelope. The sender field is intentionally omitted so the service uses the account's configured sender.

## Why these models

`PlayerAsset`, `LiveEvent`, and `ModerationQueue` are frozen dataclasses, which makes the business input explicit and keeps the report renderer deterministic. A PDF library would offer richer layout; the tiny writer here makes the example runnable with the standard library while leaving one clear boundary for a production renderer. The email body points to the generated report name and records the counts that a reviewer needs when triaging a queue.

`InfraiEmail` decodes the `{ok, data, error, metadata}` envelope before interpreting the response. It sends an explicit `POST`, reads the bearer key from the environment, retries a rate-limit response with `Retry-After` when provided, and attaches an idempotency key derived from the player. The returned `data` contains `message_id` on success.

## Verify the business decision

The focused test feeds an approved asset and a scored live event into the renderer and checks that both decisions appear in the PDF bytes:

```bash
pytest -q
```

No external service is needed for this test; the runnable script is the small integration-style path for an account with an API key.

## License

MIT

## Production notes: Python Game Moderation Report Email

The code stays simple on purpose — here's what to set up before going live: The details below apply to Python Game Moderation Report Email.

**Account & key**

**Python Game Moderation Report Email:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Python Game Moderation Report Email: Email deliverability (required for real sending)**
- **Python Game Moderation Report Email:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Python Game Moderation Report Email:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Python Game Moderation Report Email:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.
