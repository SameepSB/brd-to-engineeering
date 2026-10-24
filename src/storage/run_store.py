from __future__ import annotations

from src.contracts.schemas import OperationalRecord


class RunStore:
    """Local ephemeral sink for structured operational metadata only."""

    def __init__(self) -> None:
        self._records: list[OperationalRecord] = []

    def append(self, record: OperationalRecord) -> None:
        self._records.append(record.model_copy(deep=True))

    def list_records(self, run_id: str | None = None) -> list[OperationalRecord]:
        records = self._records
        if run_id is not None:
            records = [record for record in records if record.run_id == run_id]
        return [record.model_copy(deep=True) for record in records]
