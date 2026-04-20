from __future__ import annotations

from abc import ABC, abstractmethod
from hashlib import sha256

from app.constants.enums import TrackingEventDTO, TrackingStatus


class InvalidTrackingCodeError(Exception):
    """Raised when provider confirms tracking code is invalid."""


class TrackingProvider(ABC):
    carrier_code: str

    @abstractmethod
    def fetch_latest_event(
        self,
        tracking_code: str,
        current_status: TrackingStatus | None,
    ) -> TrackingEventDTO:
        raise NotImplementedError

    def fetch_event_history(self, tracking_code: str) -> list[TrackingEventDTO]:
        return [self.fetch_latest_event(tracking_code=tracking_code, current_status=None)]


def compute_event_hash(
    tracking_code: str,
    status: TrackingStatus,
    description: str,
    location: str,
    event_time: str | None = None,
) -> str:
    raw = f"{tracking_code}|{status.value}|{description}|{location}|{event_time or ''}"
    return sha256(raw.encode("utf-8")).hexdigest()
