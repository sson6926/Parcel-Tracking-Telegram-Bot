from tracking.providers.base import TrackingProvider
from tracking.providers.jtexpress import JTExpressProvider
from tracking.providers.shopeeexpress import ShopeeExpressProvider


def build_provider_registry() -> dict[str, TrackingProvider]:
    providers: list[TrackingProvider] = [JTExpressProvider(), ShopeeExpressProvider()]
    return {provider.carrier_code: provider for provider in providers}


__all__ = [
    "JTExpressProvider",
    "ShopeeExpressProvider",
    "TrackingProvider",
    "build_provider_registry",
]
