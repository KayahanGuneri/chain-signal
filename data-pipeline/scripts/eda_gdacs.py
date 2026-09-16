from __future__ import annotations

import json
from typing import Any

import httpx
import pandas as pd

GDACS_SEARCH_URL = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"

FROM_DATE = "2026-09-08"
TO_DATE = "2026-09-15"

EVENT_TYPES = "EQ;FL"
ALERT_LEVELS = "Green;Orange;Red"

PAGE_SIZE = 100
MAX_PAGES = 10


def fetch_gdacs_page(
    page_number: int,
) -> list[dict[str, Any]]:
    """Fetch one page from the GDACS SEARCH endpoint."""

    params: dict[str, str | int] = {
        "eventlist": EVENT_TYPES,
        "fromdate": FROM_DATE,
        "todate": TO_DATE,
        "alertlevel": ALERT_LEVELS,
        "pagesize": PAGE_SIZE,
    }

    # The first request intentionally uses the default first page.
    # Explicit page numbers are used only for subsequent pages.
    if page_number > 1:
        params["pagenumber"] = page_number

    response = httpx.get(
        GDACS_SEARCH_URL,
        params=params,
        timeout=20.0,
    )

    print()
    print(f"=== HTTP PAGE {page_number} ===")
    print(f"URL: {response.url}")
    print(f"Status: {response.status_code}")
    print(f"Content-Type: {response.headers.get('content-type')}")
    print(f"Response bytes: {len(response.content)}")

    response.raise_for_status()

    payload: dict[str, Any] = response.json()

    if payload.get("type") != "FeatureCollection":
        raise ValueError(f"Unexpected GDACS GeoJSON type: {payload.get('type')}")

    features = payload.get("features")

    if not isinstance(features, list):
        raise ValueError("GDACS payload does not contain a features list")

    print(f"Feature count: {len(features)}")

    return features


def fetch_all_gdacs_features() -> list[dict[str, Any]]:
    """Fetch all available pages for the discovery query."""

    all_features: list[dict[str, Any]] = []
    previous_page_signature: tuple[str, ...] | None = None

    for page_number in range(1, MAX_PAGES + 1):
        features = fetch_gdacs_page(page_number)

        if not features:
            print(f"Page {page_number} is empty; pagination complete.")
            break

        page_signature = tuple(
            f"{feature.get('properties', {}).get('eventtype')}:"
            f"{feature.get('properties', {}).get('eventid')}"
            for feature in features
            if isinstance(feature.get("properties"), dict)
        )

        if page_signature == previous_page_signature:
            raise RuntimeError(
                "GDACS returned the same page twice; "
                "pagination semantics need further investigation."
            )

        previous_page_signature = page_signature
        all_features.extend(features)

        if len(features) < PAGE_SIZE:
            print(
                f"Page {page_number} contains fewer than {PAGE_SIZE} features; pagination complete."
            )
            break
    else:
        raise RuntimeError(f"Reached MAX_PAGES={MAX_PAGES} before pagination completed.")

    print()
    print("=== PAGINATION SUMMARY ===")
    print(f"Combined feature count: {len(all_features)}")

    return all_features


def inspect_first_feature(
    features: list[dict[str, Any]],
) -> None:
    """Print one raw feature to inspect the provider contract."""

    if not features:
        raise ValueError("GDACS returned no features")

    print()
    print("=== FIRST FEATURE ===")
    print(
        json.dumps(
            features[0],
            indent=2,
            ensure_ascii=False,
        )
    )


def create_dataframe(
    features: list[dict[str, Any]],
) -> pd.DataFrame:
    """Flatten GDACS feature properties into a DataFrame for analysis."""

    rows: list[dict[str, Any]] = []

    for feature in features:
        properties = feature.get("properties", {})
        geometry = feature.get("geometry", {})

        if not isinstance(properties, dict):
            properties = {}

        if not isinstance(geometry, dict):
            geometry = {}

        row = dict(properties)

        row["_geometry_type"] = geometry.get("type")
        row["_coordinates"] = geometry.get("coordinates")

        rows.append(row)

    return pd.DataFrame(rows)


def normalize_nested_value(value: Any) -> Any:
    """Convert nested values to deterministic JSON strings for analysis."""

    if isinstance(value, (dict, list)):
        return json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            default=str,
        )

    return value


def inspect_dataframe(df: pd.DataFrame) -> None:
    """Print exploratory statistics about the GDACS sample."""

    print()
    print("=== DATAFRAME SHAPE ===")
    print(df.shape)

    print()
    print("=== COLUMNS ===")
    for column in df.columns:
        print(column)

    print()
    print("=== DTYPES ===")
    print(df.dtypes.to_string())

    print()
    print("=== FIRST 5 ROWS ===")
    print(df.head().to_string())

    print()
    print("=== NULL COUNTS ===")
    print(df.isna().sum().sort_values(ascending=False).to_string())

    print()
    print("=== BLANK STRING COUNTS ===")
    blank_counts = pd.Series(
        {
            column: int(
                df[column].map(lambda value: isinstance(value, str) and value.strip() == "").sum()
            )
            for column in df.columns
        }
    ).sort_values(ascending=False)

    print(blank_counts.to_string())

    print()
    print("=== EVENT TYPE COUNTS ===")
    print(df["eventtype"].value_counts(dropna=False).to_string())

    print()
    print("=== ALERT LEVEL COUNTS ===")
    print(df["alertlevel"].value_counts(dropna=False).to_string())

    print()
    print("=== SOURCE COUNTS ===")
    print(df["source"].value_counts(dropna=False).to_string())

    print()
    print("=== GEOMETRY TYPE COUNTS ===")
    print(df["_geometry_type"].value_counts(dropna=False).to_string())

    print()
    print("=== DATE RANGE ANALYSIS ===")

    for column in [
        "fromdate",
        "todate",
        "datemodified",
    ]:
        parsed = pd.to_datetime(
            df[column],
            errors="coerce",
        )

        print()
        print(f"{column}:")
        print(f"  invalid: {parsed.isna().sum()}")
        print(f"  min: {parsed.min()}")
        print(f"  max: {parsed.max()}")

    hashable_df = df.map(normalize_nested_value)

    print()
    print("=== EXACT DUPLICATE ROWS ===")
    print(hashable_df.duplicated().sum())

    print()
    print("=== DUPLICATE EVENT IDENTITIES ===")
    print(
        df.duplicated(
            subset=[
                "eventtype",
                "eventid",
            ],
        ).sum()
    )

    print()
    print("=== DUPLICATE EPISODE IDENTITIES ===")
    print(
        df.duplicated(
            subset=[
                "eventtype",
                "eventid",
                "episodeid",
            ],
        ).sum()
    )

    print()
    print("=== UNIQUE COUNTS ===")
    print(hashable_df.nunique(dropna=False).sort_values().to_string())


def main() -> None:
    features = fetch_all_gdacs_features()

    inspect_first_feature(features)

    df = create_dataframe(features)

    inspect_dataframe(df)


if __name__ == "__main__":
    main()
