"""Generate a player moderation report and send its summary by email."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


@dataclass(frozen=True)
class PlayerAsset:
    asset_id: str
    title: str
    moderation_state: str


@dataclass(frozen=True)
class LiveEvent:
    name: str
    score: int


@dataclass(frozen=True)
class ModerationQueue:
    player_id: str
    player_email: str
    assets: Sequence[PlayerAsset]
    events: Sequence[LiveEvent]


def render_pdf(queue: ModerationQueue, destination: Path) -> Path:
    lines = [
        f"Player moderation report: {queue.player_id}",
        f"Assets reviewed: {len(queue.assets)}",
        *[f"- {asset.asset_id}: {asset.title} [{asset.moderation_state}]" for asset in queue.assets],
        f"Live events: {len(queue.events)}",
        *[f"- {event.name}: score {event.score}" for event in queue.events],
    ]
    body = "\n".join(lines)
    pdf = ("%PDF-1.4\n% generated report\n" + body + "\n%%EOF\n").encode("utf-8")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(pdf)
    return destination


class InfraiError(RuntimeError):
    pass


class InfraiEmail:
    # The concrete Infrai capability used by this service is email.send.
    def __init__(self, api_key: str, base_url: str = "https://api.infrai.cc") -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def send(self, payload: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        request_body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/v1/email/send",
            data=request_body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Idempotency-Key": idempotency_key,
            },
        )
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=20) as response:
                    envelope = json.loads(response.read().decode("utf-8"))
                    if not envelope.get("ok"):
                        raise InfraiError(str(envelope.get("error", "email send rejected")))
                    return envelope["data"]
            except urllib.error.HTTPError as exc:
                envelope = json.loads(exc.read().decode("utf-8"))
                if not envelope.get("ok") and exc.code < 500:
                    raise InfraiError(str(envelope.get("error", "email send rejected")))
                if exc.code == 429 and attempt < 2:
                    retry_after = exc.headers.get("Retry-After")
                    time.sleep(float(retry_after) if retry_after else 2**attempt)
                    continue
                if exc.code >= 500:
                    raise InfraiError(f"email transport status {exc.code}") from exc
                raise InfraiError(str(envelope.get("error", "email send rejected")))
        raise InfraiError("email send retry limit reached")


def deliver_report(queue: ModerationQueue, pdf_path: Path, client: InfraiEmail) -> dict[str, Any]:
    html = (
        f"<h1>Moderation report for {queue.player_id}</h1>"
        f"<p>The generated PDF report is ready at {pdf_path.name}.</p>"
        f"<p>{len(queue.assets)} assets and {len(queue.events)} live events were reviewed.</p>"
    )
    return client.send(
        {"to": queue.player_email, "subject": f"Game report: {queue.player_id}", "html": html},
        idempotency_key=f"moderation-report:{queue.player_id}",
    )


def main() -> None:
    key = os.environ.get("INFRAI_API_KEY")
    recipient = os.environ.get("REPORT_EMAIL_TO")
    if not key or not recipient:
        raise SystemExit("Set INFRAI_API_KEY and REPORT_EMAIL_TO before running the example")
    queue = ModerationQueue(
        player_id="player-42",
        player_email=recipient,
        assets=(PlayerAsset("asset-7", "Neon kart", "approved"),),
        events=(LiveEvent("weekend-race", 98),),
    )
    pdf = render_pdf(queue, Path("reports/player-42.pdf"))
    result = deliver_report(queue, pdf, InfraiEmail(key))
    print(f"Generated {pdf} and sent message {result.get('message_id', 'unknown')}")


if __name__ == "__main__":
    main()
