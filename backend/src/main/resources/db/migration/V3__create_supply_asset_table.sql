CREATE TABLE supply_asset (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    type TEXT NOT NULL,
    name TEXT NOT NULL,
    country TEXT NOT NULL,
    city TEXT NOT NULL,

    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,

    location geography(Point, 4326)
        GENERATED ALWAYS AS (
            ST_SetSRID(
                ST_MakePoint(longitude, latitude),
                4326
            )::geography
        ) STORED,

    criticality SMALLINT NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,

    CONSTRAINT ck_supply_asset_type
        CHECK (
            type IN (
                'SUPPLIER',
                'PORT'
            )
        ),

    CONSTRAINT ck_supply_asset_name_not_blank
        CHECK (btrim(name) <> ''),

    CONSTRAINT ck_supply_asset_country_not_blank
        CHECK (btrim(country) <> ''),

    CONSTRAINT ck_supply_asset_city_not_blank
        CHECK (btrim(city) <> ''),

    CONSTRAINT ck_supply_asset_latitude
        CHECK (latitude BETWEEN -90.0 AND 90.0),

    CONSTRAINT ck_supply_asset_longitude
        CHECK (longitude BETWEEN -180.0 AND 180.0),

    CONSTRAINT ck_supply_asset_criticality
        CHECK (criticality BETWEEN 1 AND 5)
);

CREATE INDEX idx_supply_asset_active_type
    ON supply_asset (type)
    WHERE active = TRUE;

CREATE INDEX idx_supply_asset_location_gist
    ON supply_asset
    USING GIST (location);

COMMENT ON TABLE supply_asset IS
    'Backend-owned tracked supplier and port assets used for geospatial risk evaluation.';

COMMENT ON COLUMN supply_asset.criticality IS
    'Ordinal operational criticality from 1 (very low) to 5 (critical).';

COMMENT ON COLUMN supply_asset.location IS
    'Generated WGS84 geography point derived from longitude and latitude.';
