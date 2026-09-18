package io.chainsignal.backend.event.domain;

public record NearbyEvent(Event event, double distanceMeters) {
    public NearbyEvent {
        if (event == null || !Double.isFinite(distanceMeters) || distanceMeters < 0) {
            throw new IllegalArgumentException("Invalid nearby event or distance");
        }
    }
}
