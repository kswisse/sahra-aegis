from pathlib import Path

from .types import ActionRecord


class AuditLog:
    """Append-only JSONL. Never rewritten; carries a reason trace per action."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: ActionRecord) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(record.model_dump_json() + "\n")

    def read_all(self) -> list[ActionRecord]:
        if not self.path.exists():
            return []
        return [
            ActionRecord.model_validate_json(line)
            for line in self.path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
