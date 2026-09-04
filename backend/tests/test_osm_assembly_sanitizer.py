"""Unit tests for OpenStreetMap assembly-point tag sanitization and normalization."""

from app.integrations.osm.osm_sanitizer import sanitize_osm_tags


def test_sanitize_osm_tags_normalizes_core_fields() -> None:
    """Core fields (name, ref, operator) must be extracted and stripped."""
    tags = {
        "emergency": "assembly_point",
        "name": "  Demokrasi Parkı Toplanma Alanı  ",
        "ref": " 5902-007-07 ",
        "operator": " AFAD ",
    }
    name, ref, operator, properties = sanitize_osm_tags(tags)

    assert name == "Demokrasi Parkı Toplanma Alanı"
    assert ref == "5902-007-07"
    assert operator == "AFAD"
    # Core fields must NOT be duplicated in source_properties
    assert "name" not in properties
    assert "ref" not in properties
    assert "operator" not in properties
    # emergency tag is allowlisted in source_properties
    assert properties.get("emergency") == "assembly_point"


def test_sanitize_osm_tags_handles_missing_core_fields() -> None:
    """Missing or empty core fields should evaluate to None."""
    tags = {
        "emergency": "assembly_point",
        "name": "   ",
    }
    name, ref, operator, properties = sanitize_osm_tags(tags)
    assert name is None
    assert ref is None
    assert operator is None
    assert properties == {"emergency": "assembly_point"}


def test_sanitize_osm_tags_preserves_observed_allowlist_keys() -> None:
    """All 22 approved observed keys must be retained in source_properties."""
    tags = {
        "emergency": "assembly_point",
        "name:en": "City Park Assembly Area",
        "source": "https://opendata.example.gov.tr",
        "website": "https://example.gov.tr",
        "area": "yes",
        "indoor": "no",
        "opening_hours:emergency": "24/7",
        "leisure": "park",
        "amenity": "parking",
        "building": "no",
        "parking": "surface",
        "highway": "footway",
        "fee": "no",
        "addr:city": "Tekirdağ",
        "addr:district": "Süleymanpaşa",
        "addr:neighbourhood": "Hürriyet",
        "addr:subdistrict": "Merkez",
        "addr:province": "Tekirdağ",
        "addr:country": "TR",
        "addr:postcode": "59000",
        "addr:street": "Barış Caddesi",
        "addr:housenumber": "12",
    }
    _, _, _, properties = sanitize_osm_tags(tags)
    for k, v in tags.items():
        assert properties.get(k) == v


def test_sanitize_osm_tags_accepts_domain_relevant_disaster_keys() -> None:
    """The 4 forward-compatible disaster suitability keys must be accepted."""
    tags = {
        "emergency": "assembly_point",
        "assembly_point:earthquake": "yes",
        "assembly_point:fire": "yes",
        "assembly_point:flood": "no",
        "assembly_point:tsunami": "no",
    }
    _, _, _, properties = sanitize_osm_tags(tags)
    assert properties.get("assembly_point:earthquake") == "yes"
    assert properties.get("assembly_point:fire") == "yes"
    assert properties.get("assembly_point:flood") == "no"
    assert properties.get("assembly_point:tsunami") == "no"


def test_sanitize_osm_tags_drops_generic_assembly_point_wildcards() -> None:
    """Generic/unreviewed assembly_point:* tags must be dropped by default."""
    tags = {
        "emergency": "assembly_point",
        "assembly_point:tornado": "yes",
        "assembly_point:chemical": "no",
        "assembly_point:unknown_hazard": "maybe",
    }
    _, _, _, properties = sanitize_osm_tags(tags)
    assert "assembly_point:tornado" not in properties
    assert "assembly_point:chemical" not in properties
    assert "assembly_point:unknown_hazard" not in properties


def test_sanitize_osm_tags_drops_contact_and_pii_keys() -> None:
    """Personal contact details must be strictly dropped for privacy."""
    tags = {
        "emergency": "assembly_point",
        "phone": "+90 212 555 0101",
        "mobile": "+90 532 555 0101",
        "email": "contact@example.com",
        "fax": "+90 212 555 0102",
        "contact:phone": "+90 212 555 0103",
        "contact:email": "admin@example.com",
        "contact:person": "Ahmet Yılmaz",
        "contact:name": "Mehmet Demir",
    }
    _, _, _, properties = sanitize_osm_tags(tags)
    assert properties == {"emergency": "assembly_point"}


def test_sanitize_osm_tags_drops_free_text_and_low_value_keys() -> None:
    """Free text and low-value metadata must be dropped."""
    tags = {
        "emergency": "assembly_point",
        "note": "Toplanma alanı tabelası park girişindedir.",
        "description": "Geniş çim alan ve oturma bankları mevcuttur.",
        "building:levels": "2",
        "building:units": "4",
        "height": "12",
        "opening_hours:marketplace": "We 08:00-18:00",
        "shop": "kiosk",
        "education": "primary_school",
    }
    _, _, _, properties = sanitize_osm_tags(tags)
    assert properties == {"emergency": "assembly_point"}


def test_sanitize_osm_tags_drops_unrecognized_arbitrary_keys() -> None:
    """Any unrecognized future tag must be dropped by default."""
    tags = {
        "emergency": "assembly_point",
        "random_tag": "value",
        "unreviewed_metadata": "123",
        "surface": "asphalt",
    }
    _, _, _, properties = sanitize_osm_tags(tags)
    assert properties == {"emergency": "assembly_point"}


def test_sanitize_osm_tags_empty_or_none_tags() -> None:
    """Gracefully handle None or empty tag dictionaries."""
    assert sanitize_osm_tags(None) == (None, None, None, {})
    assert sanitize_osm_tags({}) == (None, None, None, {})
