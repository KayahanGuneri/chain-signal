CREATE TABLE event (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    source TEXT NOT NULL,
    source_event_id TEXT NOT NULL,

    event_type TEXT NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,

    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,

    location geography(Point, 4326)
        GENERATED ALWAYS AS (
            ST_SetSRID(
                ST_MakePoint(longitude, latitude),
                4326
            )::geography
        ) STORED,

    severity TEXT NOT NULL,
    country TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    schema_version TEXT NOT NULL,

    CONSTRAINT uq_event_business_key
        UNIQUE (source, source_event_id),

    CONSTRAINT ck_event_source_not_blank
        CHECK (btrim(source) <> ''),

    CONSTRAINT ck_event_source_event_id_not_blank
        CHECK (btrim(source_event_id) <> ''),

    CONSTRAINT ck_event_event_type
        CHECK (
            event_type IN (
                'EARTHQUAKE',
                'FLOOD',
                'CONFLICT',
                'PROTEST',
                'STRIKE'
            )
        ),

    CONSTRAINT ck_event_latitude
        CHECK (latitude BETWEEN -90.0 AND 90.0),

    CONSTRAINT ck_event_longitude
        CHECK (longitude BETWEEN -180.0 AND 180.0),

    CONSTRAINT ck_event_severity
        CHECK (
            severity IN (
                'LOW',
                'MEDIUM',
                'HIGH',
                'CRITICAL'
            )
        ),

    CONSTRAINT ck_event_country
        CHECK (
            country IS NULL
            OR btrim(country) <> ''
        ),

    CONSTRAINT ck_event_metadata_object
        CHECK (jsonb_typeof(metadata) = 'object'),

    CONSTRAINT ck_event_schema_version_not_blank
        CHECK (btrim(schema_version) <> '')
);

CREATE INDEX idx_event_occurred_at_id
    ON event (occurred_at DESC, id DESC);

CREATE INDEX idx_event_location_gist
    ON event
    USING GIST (location);

COMMENT ON TABLE event IS
    'Pipeline-owned canonical event current projection. Python writes canonical event data; Spring Boot consumes it read-only.';

COMMENT ON COLUMN event.location IS
    'Generated WGS84 geography point derived from canonical longitude and latitude.';
