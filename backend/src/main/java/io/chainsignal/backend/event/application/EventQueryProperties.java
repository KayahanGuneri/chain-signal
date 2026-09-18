package io.chainsignal.backend.event.application;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties("chainsignal.events")
public record EventQueryProperties(
        int defaultLimit, int maxLimit, double defaultRadiusKm, double maxRadiusKm) {
    public EventQueryProperties {
        if (defaultLimit <= 0 || maxLimit < defaultLimit
                || !Double.isFinite(defaultRadiusKm) || !Double.isFinite(maxRadiusKm)
                || defaultRadiusKm <= 0 || maxRadiusKm < defaultRadiusKm
                || !Double.isFinite(maxRadiusKm * 1000.0)) {
            throw new IllegalArgumentException("Invalid event query configuration");
        }
    }

    public int limit(Integer requested) {
        int value = requested == null ? defaultLimit : requested;
        if (value <= 0 || value > maxLimit) {
            throw new IllegalArgumentException("Limit must be between 1 and " + maxLimit);
        }
        return value;
    }

    public double radiusMeters(Double requestedKm) {
        double value = requestedKm == null ? defaultRadiusKm : requestedKm;
        if (!Double.isFinite(value) || value <= 0 || value > maxRadiusKm) {
            throw new IllegalArgumentException("Radius in km must be greater than 0 and at most " + maxRadiusKm);
        }
        return value * 1000.0;
    }
}
