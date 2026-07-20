from __future__ import annotations

from dataclasses import dataclass, field

from .models import JobItemResult


@dataclass(frozen=True)
class DownloadOutcome:
    paths: list[str]
    item_results: list[JobItemResult] = field(default_factory=list)
