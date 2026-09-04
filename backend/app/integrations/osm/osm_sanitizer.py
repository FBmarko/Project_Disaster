"""Tag extraction and allowlist-first sanitization for OSM assembly points."""

import re
from typing import Any

from app.integrations.osm.osm_constants import (
    DENIED_KEY_PREFIXES,
    EXPLICIT_DENIED_EXACT_KEYS,
    FULL_APPROVED_SOURCE_PROPERTY_KEYS,
    NORMALIZED_FIELD_KEYS,
)

# Regex for defensive screening of personal contact terms in key names
CONTACT_SCREENING_REGEX = re.compile(
    r"\b(phone|mobile|email|contact|person|fax)\b", re.IGNORECASE
)


def sanitize_osm_tags(
    tags: dict[str, Any] | None,
) -> tuple[str | None, str | None, str | None, dict[str, Any]]:
    """Extract normalized fields and produce a sanitized source_properties dictionary.

    Args:
        tags: Raw dictionary of OSM tags from an element.

    Returns:
        tuple of:
          - name: Normalized name string or None.
          - ref: Normalized reference code string or None.
          - operator: Normalized operator string or None.
          - source_properties: Allowlisted, sanitized dictionary of non-sensitive tags.
    """
    if not tags:
        return None, None, None, {}

    # 1. Extract normalized fields
    name = tags.get("name")
    if name is not None:
        name = str(name).strip() or None

    ref = tags.get("ref")
    if ref is not None:
        ref = str(ref).strip() or None

    operator = tags.get("operator")
    if operator is not None:
        operator = str(operator).strip() or None

    # 2. Filter remaining tags for source_properties
    sanitized: dict[str, Any] = {}

    for k, v in tags.items():
        k_lower = k.strip().lower()

        # Omit normalized core fields from source_properties
        if k in NORMALIZED_FIELD_KEYS:
            continue

        # Defense-in-depth: Deny explicit denied keys
        if k in EXPLICIT_DENIED_EXACT_KEYS or k_lower in EXPLICIT_DENIED_EXACT_KEYS:
            continue

        # Defense-in-depth: Deny prefixes (e.g. contact:*)
        if any(k_lower.startswith(pfx) for pfx in DENIED_KEY_PREFIXES):
            continue

        # Defense-in-depth: Deny keys containing contact terms
        if CONTACT_SCREENING_REGEX.search(k_lower):
            continue

        # Enforce strict allowlist:
        # 22 observed keys + 4 exact forward-compatible disaster keys
        # Note: Any generic assembly_point:* wildcard tag is automatically dropped
        if k not in FULL_APPROVED_SOURCE_PROPERTY_KEYS:
            continue

        # Clean value
        if v is not None:
            if isinstance(v, (str, int, float, bool)):
                sanitized[k] = v
            else:
                sanitized[k] = str(v)

    return name, ref, operator, sanitized
