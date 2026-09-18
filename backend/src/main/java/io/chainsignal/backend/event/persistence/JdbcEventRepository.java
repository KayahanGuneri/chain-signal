package io.chainsignal.backend.event.persistence;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.OffsetDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Optional;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

import io.chainsignal.backend.event.application.EventRepository;
import io.chainsignal.backend.event.domain.Event;
import io.chainsignal.backend.event.domain.EventType;
import io.chainsignal.backend.event.domain.NearbyEvent;
import io.chainsignal.backend.event.domain.Severity;

import tools.jackson.databind.ObjectMapper;

@Repository
public class JdbcEventRepository implements EventRepository {
    private static final String COLUMNS = """
            e.id, e.source, e.source_event_id, e.event_type, e.occurred_at,
            e.latitude, e.longitude, e.severity, e.country, e.metadata, e.schema_version
            """;

    public static final String NEARBY_SQL = "SELECT " + COLUMNS + """
            , ST_Distance(e.location, a.location) AS distance_meters
            FROM supply_asset a
            JOIN event e ON ST_DWithin(e.location, a.location, :radiusMeters)
            WHERE a.id = :assetId AND a.active = TRUE
            ORDER BY distance_meters ASC, e.occurred_at DESC, e.id DESC
            LIMIT :limit
            """;

    private final JdbcClient jdbc;
    private final ObjectMapper mapper;

    public JdbcEventRepository(JdbcClient jdbc, ObjectMapper mapper) {
        this.jdbc = jdbc;
        this.mapper = mapper;
    }

    @Override
    public Optional<Event> findById(long id) {
        return jdbc.sql("SELECT " + COLUMNS + " FROM event e WHERE e.id = :id")
                .param("id", id).query(this::mapRow).optional();
    }

    @Override
    public List<Event> findLatest(int limit, EventType eventType, Severity severity, String country) {
        var sql = new StringBuilder("SELECT " + COLUMNS + " FROM event e WHERE TRUE");
        var parameters = new HashMap<String, Object>();
        parameters.put("limit", limit);
        if (eventType != null) {
            sql.append(" AND e.event_type = :eventType");
            parameters.put("eventType", eventType.name());
        }
        if (severity != null) {
            sql.append(" AND e.severity = :severity");
            parameters.put("severity", severity.name());
        }
        if (country != null) {
            sql.append(" AND e.country = :country");
            parameters.put("country", country);
        }
        sql.append(" ORDER BY e.occurred_at DESC, e.id DESC LIMIT :limit");
        return jdbc.sql(sql.toString()).params(parameters).query(this::mapRow).list();
    }

    @Override
    public List<NearbyEvent> findNearby(long assetId, double radiusMeters, int limit) {
        return jdbc.sql(NEARBY_SQL).param("assetId", assetId)
                .param("radiusMeters", radiusMeters).param("limit", limit)
                .query((row, number) -> new NearbyEvent(mapRow(row, number), row.getDouble("distance_meters")))
                .list();
    }

    private Event mapRow(ResultSet row, int number) throws SQLException {
        return new Event(row.getLong("id"), row.getString("source"), row.getString("source_event_id"),
                EventType.valueOf(row.getString("event_type")),
                row.getObject("occurred_at", OffsetDateTime.class).toInstant(),
                row.getDouble("latitude"), row.getDouble("longitude"),
                Severity.valueOf(row.getString("severity")), row.getString("country"),
                mapper.readTree(row.getString("metadata")), row.getString("schema_version"));
    }
}
