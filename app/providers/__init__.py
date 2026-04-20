from app.providers.base import TrackingProvider
from app.providers.jtexpress.client import JTExpressProvider
from app.providers.shopeeexpress.client import ShopeeExpressProvider
from app.providers.ghn.client import GHNProvider


def build_provider_registry() -> dict[str, TrackingProvider]:
    providers: list[TrackingProvider] = [
        JTExpressProvider(),
        ShopeeExpressProvider(),
        GHNProvider(),
    ]
    return {p.carrier_code: p for p in providers}


__all__ = ["JTExpressProvider", "ShopeeExpressProvider", "GHNProvider", "TrackingProvider", "build_provider_registry"]
