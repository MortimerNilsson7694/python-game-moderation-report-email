from pathlib import Path

from report_service import LiveEvent, ModerationQueue, PlayerAsset, render_pdf


def test_report_contains_queue_decision(tmp_path: Path) -> None:
    queue = ModerationQueue(
        "p1", "player@example.com", (PlayerAsset("a1", "Sky ship", "approved"),), (LiveEvent("arena", 7),)
    )
    path = render_pdf(queue, tmp_path / "report.pdf")
    content = path.read_bytes().decode("utf-8")
    assert "a1: Sky ship [approved]" in content
    assert "arena: score 7" in content
