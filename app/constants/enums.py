from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class TrackingStatus(str, Enum):
    CREATED = "CREATED"
    PICKED_UP = "PICKED_UP"
    IN_TRANSIT = "IN_TRANSIT"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"


@dataclass
class TrackingEventDTO:
    status: TrackingStatus
    description: str
    location: str
    event_time: datetime
    event_hash: str


@dataclass
class NotificationDTO:
    tracking_code: str
    carrier_code: str
    status: TrackingStatus
    description: str
    location: str
    event_time: datetime
