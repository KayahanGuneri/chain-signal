"""Verify the Phase 2 chain against a disposable Flyway-initialized database."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import psycopg
from chainsignal_pipeline.__main__ import main, run_gdacs_ingestion
from chainsignal_pipeline.config import DatabaseSettings, Settings
from chainsignal_pipeline.database.event_writer import EventPersistenceWriter
from chainsignal_pipeline.models.event import CanonicalEvent, EventType, Severity


def run(backend: str, frontend: str, output: Path, skip_live_source: bool) -> None:
    settings = DatabaseSettings()
    writer = EventPersistenceWriter(settings)
    with (
        psycopg.connect(
            host=settings.host,
            port=settings.port,
            dbname=settings.name,
            user=settings.user,
            password=settings.password.get_secret_value(),
            autocommit=True,
        ) as db,
        httpx.Client(base_url=backend, timeout=20) as client,
    ):
        assert client.get("/actuator/health").json()["status"] == "UP"
        assert db.execute(
            "SELECT version FROM flyway_schema_history WHERE success ORDER BY installed_rank"
        ).fetchall() == [("1",), ("2",), ("3",)]
        assert db.execute(
            "SELECT extname FROM pg_extension WHERE extname='postgis'"
        ).fetchone() == ("postgis",)
        if not skip_live_source:
            pipeline_settings = Settings(
                bronze_path=output / "bronze", normalized_path=output / "normalized"
            )
            end = datetime.now(UTC)
            run_gdacs_ingestion(settings=pipeline_settings, start=end - timedelta(days=7), end=end)
            batches = list((output / "bronze").rglob("*.parquet"))
            assert batches, "Live ingestion did not produce a Bronze batch"
            # Invoke the same CLI normalization/persistence path used in development.
            import os

            previous = os.environ.get("CHAIN_SIGNAL_NORMALIZED_PATH")
            os.environ["CHAIN_SIGNAL_NORMALIZED_PATH"] = str(output / "normalized")
            try:
                main(
                    [
                        "normalize-gdacs",
                        "--bronze-file",
                        str(max(batches, key=lambda path: path.stat().st_mtime)),
                    ]
                )
            finally:
                if previous is None:
                    os.environ.pop("CHAIN_SIGNAL_NORMALIZED_PATH", None)
                else:
                    os.environ["CHAIN_SIGNAL_NORMALIZED_PATH"] = previous
            count = db.execute("SELECT count(*) FROM event WHERE source='GDACS'").fetchone()
            assert count and count[0] > 0, "No live GDACS canonical events persisted"
            assert client.get("/api/events?limit=500").json()
            print(f"Live GDACS persisted: {count[0]} events")

        now = datetime.now(UTC)
        fixtures = [
            CanonicalEvent(
                "PHASE2_SMOKE",
                str(index),
                EventType.EARTHQUAKE,
                now,
                latitude,
                29.0,
                Severity.HIGH,
                None,
                {"nested": {"unicode": "Türkiye", "value": None}},
            )
            for index, latitude in enumerate([41.0, 41.01, 45.0])
        ]
        assert writer.write(fixtures).changed_count == 3
        assert writer.write(fixtures).changed_count == 0
        body = {
            "type": "PORT",
            "name": "İstanbul smoke port",
            "country": "Türkiye",
            "city": "İstanbul",
            "latitude": 41.0,
            "longitude": 29.0,
            "criticality": 5,
        }
        created = client.post(
            "/api/supply-assets",
            content=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        assert created.status_code == 201, created.text
        asset = created.json()
        asset_id = asset["id"]
        assert client.get(f"/api/supply-assets/{asset_id}").json() == asset
        nearby = client.get(
            f"/api/supply-assets/{asset_id}/nearby-events?radiusKm=2&limit=100"
        ).json()
        assert [
            item["event"]["sourceEventId"]
            for item in nearby
            if item["event"]["source"] == "PHASE2_SMOKE"
        ] == ["0", "1"]
        assert nearby[0]["distanceMeters"] == 0
        assert 1000 < nearby[1]["distanceMeters"] < 1200
        assert isinstance(nearby[0]["event"]["metadata"], dict)
        event_id = nearby[0]["event"]["id"]
        assert client.get(f"/api/events/{event_id}").json()["country"] is None
        for query in [
            "radiusKm=0",
            "radiusKm=1001",
            "radiusKm=NaN",
            "limit=0",
            "limit=501",
        ]:
            assert (
                client.get(f"/api/supply-assets/{asset_id}/nearby-events?{query}").status_code
                == 400
            )
        body["latitude"] = 42.0
        assert client.put(f"/api/supply-assets/{asset_id}", json=body).status_code == 200
        assert db.execute(
            "SELECT ST_Y(location::geometry), ST_SRID(location::geometry) "
            "FROM supply_asset WHERE id=%s",
            (asset_id,),
        ).fetchone() == (42.0, 4326)
        body["latitude"] = 41.0
        assert client.put(f"/api/supply-assets/{asset_id}", json=body).status_code == 200
        assert db.execute(
            "SELECT count(*) FROM event "
            "WHERE location IS NULL OR ST_SRID(location::geometry) <> 4326"
        ).fetchone() == (0,)
        assert db.execute(
            "SELECT count(*) FROM (SELECT source, source_event_id FROM event "
            "GROUP BY source, source_event_id HAVING count(*) > 1) duplicates"
        ).fetchone() == (0,)
        with httpx.Client(base_url=frontend, timeout=20) as ui:
            page = ui.get("/")
            assert page.status_code == 200
            assert 'property="og:image"' in page.text
            assert 'name="twitter:card" content="summary_large_image"' in page.text
            assert "/og/chainsignal-phase2-og.png" in page.text
            for asset_path in ["/brand/chainsignal-hero.png", "/og/chainsignal-phase2-og.png"]:
                image = ui.get(asset_path)
                assert image.status_code == 200
                assert image.headers["content-type"].startswith("image/png")
                assert image.content.startswith(b"\x89PNG\r\n\x1a\n")
            assert ui.get("/api/events?limit=10").status_code == 200
            assert ui.get("/api/supply-assets").json()[0]["name"] == body["name"]
            assert (
                ui.get(f"/api/supply-assets/{asset_id}/nearby-events?radiusKm=2").json() == nearby
            )

        # Python owns disposable event fixture writes; Spring remains read-only.
        generated = [
            CanonicalEvent(
                "PHASE2_PLAN",
                str(index),
                EventType.FLOOD,
                now,
                -80 + (index % 1600) / 10,
                -179 + ((index * 37) % 3580) / 10,
                Severity.LOW,
                None,
            )
            for index in range(50000)
        ]
        writer.write(generated)
        db.execute("ANALYZE event")
        db.execute("ANALYZE supply_asset")
        repository_path = (
            Path(__file__).resolve().parents[1]
            / "backend/src/main/java/io/chainsignal/backend/event/persistence"
            / "JdbcEventRepository.java"
        )
        source = repository_path.read_text(encoding="utf-8")
        columns = source.split('private static final String COLUMNS = """', 1)[1].split('""";', 1)[
            0
        ]
        tail = source.split('public static final String NEARBY_SQL = "SELECT " + COLUMNS + """', 1)[
            1
        ].split('""";', 1)[0]
        query = (
            ("SELECT " + columns + tail)
            .replace(":assetId", "%(assetId)s")
            .replace(":radiusMeters", "%(radiusMeters)s")
            .replace(":limit", "%(limit)s")
        )
        plan = "\n".join(
            row[0]
            for row in db.execute(
                "EXPLAIN (ANALYZE, BUFFERS) " + query,
                {"assetId": asset_id, "radiusMeters": 2000.0, "limit": 100},
            ).fetchall()
        )
        (output / "nearby-explain.txt").write_text(plan + "\n", encoding="utf-8", newline="\n")
        assert "idx_event_location_gist" in plan and "Index Cond:" in plan, plan
        print(plan)
        db.execute("DELETE FROM event WHERE source='PHASE2_PLAN'")
        assert client.delete(f"/api/supply-assets/{asset_id}").status_code == 204
        assert client.get(f"/api/supply-assets/{asset_id}").json()["active"] is False
        assert client.get(f"/api/supply-assets/{asset_id}/nearby-events").status_code == 404
        print(
            "PASS: Flyway, "
            + ("offline fixtures" if skip_live_source else "live pipeline")
            + ", persistence, APIs, PostGIS, frontend proxy/static branding/social metadata "
            "and natural GiST plan"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", required=True)
    parser.add_argument("--frontend", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--skip-live-source", action="store_true")
    arguments = parser.parse_args()
    run(
        arguments.backend,
        arguments.frontend,
        arguments.output,
        arguments.skip_live_source,
    )
