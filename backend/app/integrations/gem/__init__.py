from app.integrations.gem.mapping import (
    GEM_SOURCE_IDENTIFIER,
    TURKEY_CONTEXT_BBOX,
)
from app.integrations.gem.parser import parse_gem_feature, parse_gem_feature_collection

# Backwards compatibility alias
TURKEY_BBOX = TURKEY_CONTEXT_BBOX

__all__ = [
    "GEM_SOURCE_IDENTIFIER",
    "TURKEY_BBOX",
    "TURKEY_CONTEXT_BBOX",
    "parse_gem_feature",
    "parse_gem_feature_collection",
]
