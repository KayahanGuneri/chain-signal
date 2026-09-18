package io.chainsignal.backend.event.application;

import java.util.List;
import java.util.Optional;

import io.chainsignal.backend.event.domain.Event;
import io.chainsignal.backend.event.domain.EventType;
import io.chainsignal.backend.event.domain.NearbyEvent;
import io.chainsignal.backend.event.domain.Severity;

public interface EventRepository {
    Optional<Event> findById(long id);
    List<Event> findLatest(int limit, EventType eventType, Severity severity, String country);
    List<NearbyEvent> findNearby(long assetId, double radiusMeters, int limit);
}
