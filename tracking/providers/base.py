from __future__ import annotations

from abc import ABC, abstractmethod
from hashlib import sha256

from tracking.types import TrackingEventDTO, TrackingStatus


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
        latest = self.fetch_latest_event(tracking_code=tracking_code, current_status=None)
        return [latest]


def compute_event_hash(
    tracking_code: str,
    status: TrackingStatus,
    description: str,
    location: str,
    event_time: str | None = None,
) -> str:
    raw = f"{tracking_code}|{status.value}|{description}|{location}|{event_time or ''}"
    return sha256(raw.encode("utf-8")).hexdigest()


def next_status(current_status: TrackingStatus | None) -> TrackingStatus:
    flow = [
        TrackingStatus.CREATED,
        TrackingStatus.PICKED_UP,
        TrackingStatus.IN_TRANSIT,
        TrackingStatus.OUT_FOR_DELIVERY,
        TrackingStatus.DELIVERED,
    ]

    if current_status is None:
        return TrackingStatus.CREATED

    if current_status == TrackingStatus.FAILED:
        return TrackingStatus.FAILED

    current_index = flow.index(current_status) if current_status in flow else 0
    return flow[min(current_index + 1, len(flow) - 1)]
