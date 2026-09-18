package io.chainsignal.backend.event.application;

import java.util.List;

import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.stereotype.Service;

import io.chainsignal.backend.event.domain.Event;
import io.chainsignal.backend.event.domain.EventType;
import io.chainsignal.backend.event.domain.NearbyEvent;
import io.chainsignal.backend.event.domain.Severity;
import io.chainsignal.backend.supplyasset.application.SupplyAssetNotFoundException;
import io.chainsignal.backend.supplyasset.application.SupplyAssetService;

@Service
@EnableConfigurationProperties(EventQueryProperties.class)
public class EventService {
    private final EventRepository repository;
    private final SupplyAssetService assets;
    private final EventQueryProperties properties;

    public EventService(EventRepository repository, SupplyAssetService assets, EventQueryProperties properties) {
        this.repository = repository;
        this.assets = assets;
        this.properties = properties;
    }

    public Event getById(long id) {
        if (id <= 0) {
            throw new IllegalArgumentException("Event id must be positive");
        }
        return repository.findById(id).orElseThrow(() -> new EventNotFoundException(id));
    }

    public List<Event> list(Integer limit, EventType eventType, Severity severity, String country) {
        if (country != null && country.isBlank()) {
            throw new IllegalArgumentException("Country filter must not be blank");
        }
        return repository.findLatest(properties.limit(limit), eventType, severity, country);
    }

    public List<NearbyEvent> nearby(long assetId, Double radiusKm, Integer limit) {
        double radiusMeters = properties.radiusMeters(radiusKm);
        int boundedLimit = properties.limit(limit);
        var asset = assets.getById(assetId);
        if (!asset.active()) {
            throw new SupplyAssetNotFoundException("Active supply asset not found: " + assetId);
        }
        return repository.findNearby(assetId, radiusMeters, boundedLimit);
    }
}
