from src.core.site_adapters.base_adapter import BaseSiteAdapter
from src.core.site_adapters.nyaa import NyaaAdapter
from src.core.site_adapters.dmhy import DMHYAdapter
from src.core.site_adapters.acgrip import ACGripAdapter
from src.core.site_adapters.bangumi import BangumiAdapter

SITE_ADAPTERS = {
    "nyaa": NyaaAdapter,
    "dmhy": DMHYAdapter,
    "acgrip": ACGripAdapter,
    "bangumi": BangumiAdapter,
}


def get_adapter_for_site(site_name: str) -> BaseSiteAdapter:
    return SITE_ADAPTERS.get(site_name.lower())()


def get_supported_sites():
    return list(SITE_ADAPTERS.keys())


def get_site_format_info(site_name: str):
    adapter_cls = SITE_ADAPTERS.get(site_name.lower())
    if not adapter_cls:
        return None
    adapter = adapter_cls()
    return {
        "site_name": adapter.site_name,
        "supported_format": adapter.supported_format,
        "description": adapter.format_description,
    }
