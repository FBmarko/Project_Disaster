import functools
import json
import os
from pathlib import Path
from typing import Any

TURKEY_PROVINCES: tuple[str, ...] = (
    "Adana",
    "Adıyaman",
    "Afyonkarahisar",
    "Ağrı",
    "Amasya",
    "Ankara",
    "Antalya",
    "Artvin",
    "Aydın",
    "Balıkesir",
    "Bilecik",
    "Bingöl",
    "Bitlis",
    "Bolu",
    "Burdur",
    "Bursa",
    "Çanakkale",
    "Çankırı",
    "Çorum",
    "Denizli",
    "Diyarbakır",
    "Edirne",
    "Elazığ",
    "Erzincan",
    "Erzurum",
    "Eskişehir",
    "Gaziantep",
    "Giresun",
    "Gümüşhane",
    "Hakkâri",
    "Hatay",
    "Isparta",
    "Mersin",
    "İstanbul",
    "İzmir",
    "Kars",
    "Kastamonu",
    "Kayseri",
    "Kırklareli",
    "Kırşehir",
    "Kocaeli",
    "Konya",
    "Kütahya",
    "Malatya",
    "Manisa",
    "Kahramanmaraş",
    "Mardin",
    "Muğla",
    "Muş",
    "Nevşehir",
    "Niğde",
    "Ordu",
    "Rize",
    "Sakarya",
    "Samsun",
    "Siirt",
    "Sinop",
    "Sivas",
    "Tekirdağ",
    "Tokat",
    "Trabzon",
    "Tunceli",
    "Şanlıurfa",
    "Uşak",
    "Van",
    "Yozgat",
    "Zonguldak",
    "Aksaray",
    "Bayburt",
    "Karaman",
    "Kırıkkale",
    "Batman",
    "Şırnak",
    "Bartın",
    "Ardahan",
    "Iğdır",
    "Yalova",
    "Karabük",
    "Kilis",
    "Osmaniye",
    "Düzce",
)

assert len(TURKEY_PROVINCES) == 81, (
    f"Expected 81 provinces, got {len(TURKEY_PROVINCES)}"
)


def find_provinces_geojson_path() -> Path:
    """Resolve the filesystem location of turkey_provinces.geojson."""
    env_path = os.getenv("AFET360_PROVINCES_GEOJSON")
    if env_path and Path(env_path).is_file():
        return Path(env_path)

    base_dir = Path(__file__).resolve().parents[2]  # backend root
    candidates = [
        base_dir / "data" / "turkey_provinces.geojson",
        Path("/app/data/turkey_provinces.geojson"),
        Path("data/turkey_provinces.geojson"),
        Path("backend/data/turkey_provinces.geojson"),
    ]
    for p in candidates:
        if p.is_file():
            return p

    raise FileNotFoundError(
        "Could not locate turkey_provinces.geojson. Checked: "
        + ", ".join(str(c) for c in candidates)
    )


@functools.cache
def get_turkey_province_features() -> list[dict[str, Any]]:
    """Load and validate the 81 Turkish province boundary features.

    Returns a list of 81 dicts sorted by plate_code ascending (1..81).
    """
    geojson_path = find_provinces_geojson_path()
    with open(geojson_path, encoding="utf-8") as f:
        data = json.load(f)

    features = data.get("features", [])
    if len(features) != 81:
        msg = (
            f"Expected exactly 81 province features in {geojson_path}, "
            f"found {len(features)}"
        )
        raise ValueError(msg)

    parsed_provinces: list[dict[str, Any]] = []
    seen_plates: set[int] = set()

    for feat in features:
        props = feat.get("properties", {})
        plate = props.get("number")
        if not isinstance(plate, int) or not (1 <= plate <= 81):
            raise ValueError(f"Invalid plate number {plate} in feature {props}")

        if plate in seen_plates:
            raise ValueError(f"Duplicate plate number {plate} encountered in GeoJSON")
        seen_plates.add(plate)

        canonical_name = TURKEY_PROVINCES[plate - 1]
        geom_str = json.dumps(feat.get("geometry"))

        parsed_provinces.append(
            {
                "plate_code": plate,
                "province_id": f"{plate:02d}",
                "province_name": canonical_name,
                "raw_name": str(props.get("name", "")),
                "geojson": geom_str,
            }
        )

    parsed_provinces.sort(key=lambda p: p["plate_code"])
    return parsed_provinces
