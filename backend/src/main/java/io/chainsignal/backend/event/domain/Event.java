package io.chainsignal.backend.event.domain;

import java.time.Instant;

import tools.jackson.databind.JsonNode;

public record Event(
        long id, String source, String sourceEventId, EventType eventType,
        Instant occurredAt, double latitude, double longitude, Severity severity,
        String country, JsonNode metadata, String schemaVersion) {

    public Event {
        if (id <= 0 || eventType == null || severity == null || occurredAt == null) {
            throw new IllegalArgumentException("Invalid canonical event identity, type, severity or time");
        }
        requireText(source);
        requireText(sourceEventId);
        requireText(schemaVersion);
        if (country != null) {
            requireText(country);
        }
        if (!Double.isFinite(latitude) || latitude < -90 || latitude > 90
                || !Double.isFinite(longitude) || longitude < -180 || longitude > 180) {
            throw new IllegalArgumentException("Invalid canonical event coordinates");
        }
        if (metadata == null || !metadata.isObject()) {
            throw new IllegalArgumentException("Canonical event metadata must be a JSON object");
        }
    }

    private static void requireText(String value) {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException("Canonical event text must not be blank");
        }
    }
}
