package io.chainsignal.backend;

import static org.assertj.core.api.Assertions.*;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Instant;

import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;
import org.testcontainers.postgresql.PostgreSQLContainer;
import org.testcontainers.utility.DockerImageName;

import io.chainsignal.backend.event.application.EventRepository;
import io.chainsignal.backend.event.domain.*;

import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT,
        properties = {"chainsignal.events.default-limit=100", "chainsignal.events.max-limit=500",
                "chainsignal.events.default-radius-km=100", "chainsignal.events.max-radius-km=1000"})
class GeospatialApiIT {
    private static final PostgreSQLContainer DB = new PostgreSQLContainer(
            DockerImageName.parse("postgis/postgis:16-3.5").asCompatibleSubstituteFor("postgres"));
    private static final String BODY = """
            {"type":"PORT","name":" Port İstanbul ","country":"Türkiye","city":"İstanbul",
             "latitude":41,"longitude":29,"criticality":5}
            """;
    private final JdbcClient jdbc;
    private final ObjectMapper mapper;
    private final EventRepository events;
    private final PlatformTransactionManager transactions;
    private final int port;
    private final HttpClient http = HttpClient.newHttpClient();

    @Autowired
    GeospatialApiIT(JdbcClient jdbc, ObjectMapper mapper, EventRepository events,
            PlatformTransactionManager transactions, @Value("${local.server.port}") int port) {
        this.jdbc = jdbc;
        this.mapper = mapper;
        this.events = events;
        this.transactions = transactions;
        this.port = port;
    }

    @DynamicPropertySource
    static void database(DynamicPropertyRegistry registry) {
        DB.start();
        registry.add("spring.datasource.url", DB::getJdbcUrl);
        registry.add("spring.datasource.username", DB::getUsername);
        registry.add("spring.datasource.password", DB::getPassword);
    }

    @AfterAll
    static void cleanup() {
        DB.stop();
    }

    @BeforeEach
    void resetFixtures() {
        // Test fixture setup only; production Spring repositories never write event rows.
        jdbc.sql("TRUNCATE event, supply_asset RESTART IDENTITY").update();
    }

    private HttpResponse<String> request(String method, String path, String body) throws Exception {
        return http.send(HttpRequest.newBuilder(URI.create("http://127.0.0.1:" + port + path))
                .header("Content-Type", "application/json")
                .method(method, body == null ? HttpRequest.BodyPublishers.noBody() : HttpRequest.BodyPublishers.ofString(body))
                .build(), HttpResponse.BodyHandlers.ofString());
    }

    private JsonNode get(String path) throws Exception {
        var response = request("GET", path, null);
        assertThat(response.statusCode()).isEqualTo(200);
        return mapper.readTree(response.body());
    }

    private long asset() throws Exception {
        var response = request("POST", "/api/supply-assets", BODY);
        assertThat(response.statusCode()).isEqualTo(201);
        long id = mapper.readTree(response.body()).get("id").asLong();
        assertThat(response.headers().firstValue("Location")).contains("/api/supply-assets/" + id);
        return id;
    }

    private long event(String identity, String time, double latitude, Severity severity, String country) {
        return jdbc.sql("""
                INSERT INTO event(source, source_event_id, event_type, occurred_at, latitude, longitude,
                    severity, country, metadata, schema_version)
                VALUES ('IT', :identity, 'FLOOD', CAST(:time AS timestamptz), :latitude, 29,
                    :severity, :country, '{"nested":{"text":"Türkiye","nullable":null},"list":[1,true]}'::jsonb, 'v1')
                RETURNING id
                """).param("identity", identity).param("time", time).param("latitude", latitude)
                .param("severity", severity.name()).param("country", country, java.sql.Types.VARCHAR)
                .query(Long.class).single();
    }

    @Test
    void migrationsHealthAndPostgisInitializeRealDatabase() throws Exception {
        assertThat(get("/actuator/health").get("status").asText()).isEqualTo("UP");
        assertThat(jdbc.sql("SELECT version FROM flyway_schema_history WHERE success ORDER BY installed_rank").query(String.class).list()).containsExactly("1", "2", "3");
        assertThat(jdbc.sql("SELECT postgis_version()").query(String.class).single()).startsWith("3.5");
    }

    @Test
    void assetCrudRecomputesGeographyAndSoftDeletePreservesRow() throws Exception {
        long id = asset();
        assertThat(get("/api/supply-assets").size()).isEqualTo(1);
        assertThat(get("/api/supply-assets/" + id).get("name").asText()).isEqualTo(" Port İstanbul ");
        assertThat(jdbc.sql("SELECT ST_X(location::geometry) FROM supply_asset WHERE id=:id").param("id", id).query(Double.class).single()).isEqualTo(29);
        assertThat(request("PUT", "/api/supply-assets/" + id, BODY.replace("\"latitude\":41", "\"latitude\":42")).statusCode()).isEqualTo(200);
        assertThat(jdbc.sql("SELECT ST_Y(location::geometry) FROM supply_asset WHERE id=:id").param("id", id).query(Double.class).single()).isEqualTo(42);
        assertThat(jdbc.sql("SELECT ST_SRID(location::geometry) FROM supply_asset WHERE id=:id").param("id", id).query(Integer.class).single()).isEqualTo(4326);
        assertThat(request("DELETE", "/api/supply-assets/" + id, null).statusCode()).isEqualTo(204);
        assertThat(get("/api/supply-assets/" + id).get("active").asBoolean()).isFalse();
        assertThat(get("/api/supply-assets").size()).isEqualTo(1);
        assertThat(request("DELETE", "/api/supply-assets/" + id, null).statusCode()).isEqualTo(204);
        assertThat(request("PUT", "/api/supply-assets/" + id, BODY).statusCode()).isEqualTo(200);
        assertThat(get("/api/supply-assets/" + id).get("active").asBoolean()).isFalse();
    }

    @ParameterizedTest
    @ValueSource(strings = {"type", "latitude", "longitude", "criticality"})
    void requiredFieldsCannotBeMissingOrNull(String field) throws Exception {
        var body = mapper.readTree(BODY);
        var object = (tools.jackson.databind.node.ObjectNode) body;
        object.remove(field);
        assertError("POST", "/api/supply-assets", mapper.writeValueAsString(object), 400);
        object.putNull(field);
        assertError("PUT", "/api/supply-assets/1", mapper.writeValueAsString(object), 400);
    }

    @Test
    void invalidBodiesAndEnumsHaveConsistentErrors() throws Exception {
        assertError("POST", "/api/supply-assets", "{", 400);
        assertError("POST", "/api/supply-assets", BODY.replace("PORT", "OTHER"), 400);
        assertError("POST", "/api/supply-assets", BODY.replace("\"criticality\":5", "\"criticality\":6"), 400);
        assertError("POST", "/api/supply-assets", BODY.replace("\"criticality\":5", "\"criticality\":1.5"), 400);
        assertError("POST", "/api/supply-assets", BODY.replace("\"latitude\":41", "\"latitude\":91"), 400);
        assertError("POST", "/api/supply-assets", BODY.replace(" Port İstanbul ", " "), 400);
    }

    private void assertError(String method, String path, String body, int status) throws Exception {
        var response = request(method, path, body);
        assertThat(response.statusCode()).isEqualTo(status);
        var error = mapper.readTree(response.body());
        assertThat(error.get("status").asInt()).isEqualTo(status);
        assertThat(error.get("path").asText()).isEqualTo(path.split("\\?")[0]);
        assertThat(error.get("message").asText()).isNotBlank();
        assertThat(error.get("timestamp").asText()).isNotBlank();
    }

    @Test
    void missingAndInvalidIdsHaveConsistentErrors() throws Exception {
        for (String path : new String[]{"/api/events/9", "/api/supply-assets/9", "/api/supply-assets/9/nearby-events"}) assertError("GET", path, null, 404);
        assertError("PUT", "/api/supply-assets/9", BODY, 404);
        assertError("DELETE", "/api/supply-assets/9", null, 404);
        for (String path : new String[]{"/api/events/0", "/api/events/-1", "/api/events/no", "/api/supply-assets/0", "/api/supply-assets/0/nearby-events"}) assertError("GET", path, null, 400);
    }

    @Test
    void eventMappingOrderingFilteringAndJsonMatchCanonicalContract() throws Exception {
        long first = event("one", "2026-09-01T12:00:00+03:00", 41, Severity.LOW, null);
        long second = event("two", "2026-09-01T09:00:00Z", 41.01, Severity.HIGH, "Türkiye");
        long third = event("three", "2026-09-02T00:00:00Z", 45, Severity.HIGH, " Türkiye ");
        assertThat(events.findLatest(100, null, null, null)).extracting(Event::id).containsExactly(third, second, first);
        var mapped = events.findById(first).orElseThrow();
        assertThat(mapped.eventType()).isEqualTo(EventType.FLOOD);
        assertThat(mapped.severity()).isEqualTo(Severity.LOW);
        assertThat(mapped.occurredAt()).isEqualTo(Instant.parse("2026-09-01T09:00:00Z"));
        assertThat(mapped.country()).isNull();
        assertThat(mapped.schemaVersion()).isEqualTo("v1");
        assertThat(mapped.sourceEventId()).isEqualTo("one");
        assertThat(mapped.metadata().get("nested").get("nullable").isNull()).isTrue();
        var response = get("/api/events/" + first);
        assertThat(response.get("metadata").isObject()).isTrue();
        assertThat(response.get("metadata").get("nested").get("text").asText()).isEqualTo("Türkiye");
        assertThat(response.get("country").isNull()).isTrue();
        assertThat(response.has("location")).isFalse();
        assertThat(get("/api/events?limit=1").get(0).get("id").asLong()).isEqualTo(third);
        assertThat(get("/api/events?eventType=FLOOD&severity=HIGH&country=T%C3%BCrkiye").size()).isEqualTo(1);
        assertThat(get("/api/events?eventType=EARTHQUAKE").size()).isZero();
        assertThat(get("/api/events?country=%20T%C3%BCrkiye%20").get(0).get("id").asLong()).isEqualTo(third);
        assertThat(jdbc.sql("SELECT count(*) FROM event WHERE location IS NULL OR ST_SRID(location::geometry) <> 4326").query(Long.class).single()).isZero();
    }

    @Test
    void repositoriesWorkInDatabaseReadOnlyTransaction() throws Exception {
        long id = event("one", "2026-09-01T00:00:00Z", 41, Severity.HIGH, null);
        long assetId = asset();
        var transaction = new TransactionTemplate(transactions);
        transaction.executeWithoutResult(status -> {
            jdbc.sql("SET TRANSACTION READ ONLY").update();
            assertThat(events.findById(id)).isPresent();
            assertThat(events.findLatest(10, null, null, null)).hasSize(1);
            assertThat(events.findNearby(assetId, 1000, 10)).hasSize(1);
        });
    }

    @ParameterizedTest
    @ValueSource(strings = {"limit=0", "limit=-1", "limit=501", "limit=no", "eventType=OTHER", "severity=OTHER", "country=%20"})
    void invalidEventParametersAre400(String query) throws Exception {
        assertError("GET", "/api/events?" + query, null, 400);
    }

    @Test
    void nearbyIncludesInsideExcludesOutsideOrdersDistanceAndBreaksTies() throws Exception {
        long assetId = asset();
        long center = event("center", "2026-09-01T00:00:00Z", 41, Severity.HIGH, null);
        long nearOld = event("near-old", "2026-09-01T00:00:00Z", 41.01, Severity.LOW, null);
        long nearNew = event("near-new", "2026-09-02T00:00:00Z", 41.01, Severity.LOW, null);
        long nearTie = event("near-tie", "2026-09-02T00:00:00Z", 41.01, Severity.LOW, null);
        event("outside", "2026-09-03T00:00:00Z", 45, Severity.CRITICAL, null);
        assertThat(events.findNearby(assetId, 2000, 100)).extracting(item -> item.event().id()).containsExactly(center, nearTie, nearNew, nearOld);
        var nearby = get("/api/supply-assets/" + assetId + "/nearby-events?radiusKm=2&limit=2");
        assertThat(nearby.size()).isEqualTo(2);
        assertThat(nearby.get(0).get("distanceMeters").asDouble()).isZero();
        assertThat(nearby.get(1).get("distanceMeters").asDouble()).isBetween(1000.0, 1200.0);
        assertThat(nearby.get(1).get("event").get("id").asLong()).isEqualTo(nearTie);
        assertThat(get("/api/supply-assets/" + assetId + "/nearby-events?radiusKm=0.01").size()).isEqualTo(1);
        assertThat(get("/api/supply-assets/" + assetId + "/nearby-events?radiusKm=1000&limit=500").size()).isEqualTo(5);
        assertThat(request("DELETE", "/api/supply-assets/" + assetId, null).statusCode()).isEqualTo(204);
        assertError("GET", "/api/supply-assets/" + assetId + "/nearby-events", null, 404);
    }

    @Test
    void nearbyEmptyResultIsArray() throws Exception {
        assertThat(get("/api/supply-assets/" + asset() + "/nearby-events").size()).isZero();
    }

    @ParameterizedTest
    @ValueSource(strings = {"radiusKm=0", "radiusKm=-1", "radiusKm=1001", "radiusKm=NaN", "radiusKm=Infinity", "radiusKm=no", "limit=0", "limit=501", "limit=no"})
    void invalidNearbyParametersAre400(String query) throws Exception {
        assertError("GET", "/api/supply-assets/" + asset() + "/nearby-events?" + query, null, 400);
    }
}
