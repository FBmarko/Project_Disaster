"""Constants for OpenStreetMap emergency assembly point snapshot ingestion."""

# Source Provenance Metadata
OSM_SOURCE_NAME = "OpenStreetMap"
OSM_PROVIDER = "OpenStreetMap contributors"
OSM_SOURCE_CLASSIFICATION = "community_open_data"
OSM_LICENSE = "ODbL 1.0"
OSM_ATTRIBUTION = "© OpenStreetMap contributors"
OSM_SOURCE_REFERENCE = "https://www.openstreetmap.org/copyright"
OSM_ENDPOINT = "https://overpass-api.de/api/interpreter"

# Authoritative Snapshot Manifest (2026-09-04)
OSM_SNAPSHOT_RETRIEVED_AT = "2026-09-04T08:49:10Z"
OSM_SOURCE_DATA_TIMESTAMP = "2026-09-04T08:48:11Z"
OSM_AREAS_BASE_TIMESTAMP = "2026-09-03T10:22:36Z"
OSM_GENERATOR = "Overpass API 0.7.62.11 87bfad18"

OSM_EXPECTED_SIZE_BYTES = 179012
OSM_EXPECTED_SHA256 = "23b86cfc29f30a47ca49c4e0037c4bcf914066870d06d234d53b64be2a46c340"

# Contract Counts
OSM_EXPECTED_FEATURE_COUNT = 678
OSM_EXPECTED_NODE_COUNT = 650
OSM_EXPECTED_WAY_COUNT = 28
OSM_EXPECTED_RELATION_COUNT = 0

# Authoritative Overpass Extraction Query
OSM_EXTRACTION_QUERY = """[out:json][timeout:180];

area
  ["ISO3166-1"="TR"]
  ["admin_level"="2"]
  ->.turkey;

(
  node["emergency"="assembly_point"](area.turkey);
  way["emergency"="assembly_point"](area.turkey);
  relation["emergency"="assembly_point"](area.turkey);
);

out body geom;"""

# Normalized Core Fields (Stored in dedicated columns, omitted from source_properties)
NORMALIZED_FIELD_KEYS = frozenset({"name", "ref", "operator"})

# Currently Observed and Approved Keys (22 keys)
OBSERVED_APPROVED_KEYS = frozenset(
    {
        "emergency",
        "name:en",
        "source",
        "website",
        "area",
        "indoor",
        "opening_hours:emergency",
        "leisure",
        "amenity",
        "building",
        "parking",
        "highway",
        "fee",
        "addr:city",
        "addr:district",
        "addr:neighbourhood",
        "addr:subdistrict",
        "addr:province",
        "addr:country",
        "addr:postcode",
        "addr:street",
        "addr:housenumber",
    }
)

# Forward-Compatible Domain-Relevant Approved Keys (Currently Absent, 4 exact keys)
# Note: Generic wildcard assembly_point:* is strictly prohibited
DOMAIN_RELEVANT_APPROVED_KEYS = frozenset(
    {
        "assembly_point:earthquake",
        "assembly_point:fire",
        "assembly_point:flood",
        "assembly_point:tsunami",
    }
)

# Combined Allowed Keys in source_properties
FULL_APPROVED_SOURCE_PROPERTY_KEYS = (
    OBSERVED_APPROVED_KEYS | DOMAIN_RELEVANT_APPROVED_KEYS
)

# Explicit Denylist (Defense-in-Depth against privacy leaks and free-text noise)
EXPLICIT_DENIED_EXACT_KEYS = frozenset(
    {
        "phone",
        "mobile",
        "email",
        "fax",
        "note",
        "description",
        "building:levels",
        "building:units",
        "height",
        "opening_hours:marketplace",
        "shop",
        "education",
    }
)

# Prefix Denylist (e.g. contact:phone, contact:name, contact:email, contact:person)
DENIED_KEY_PREFIXES = ("contact:",)
