package io.chainsignal.backend.event.web;

import java.util.List;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import io.chainsignal.backend.event.application.EventService;
import io.chainsignal.backend.event.domain.Event;
import io.chainsignal.backend.event.domain.EventType;
import io.chainsignal.backend.event.domain.NearbyEvent;
import io.chainsignal.backend.event.domain.Severity;

@RestController
public class EventController {
    private final EventService service;

    public EventController(EventService service) {
        this.service = service;
    }

    @GetMapping("/api/events")
    public List<Event> list(@RequestParam(required = false) Integer limit,
            @RequestParam(required = false) EventType eventType,
            @RequestParam(required = false) Severity severity,
            @RequestParam(required = false) String country) {
        return service.list(limit, eventType, severity, country);
    }

    @GetMapping("/api/events/{id}")
    public Event getById(@PathVariable long id) {
        return service.getById(id);
    }

    @GetMapping("/api/supply-assets/{id}/nearby-events")
    public List<NearbyEvent> nearby(@PathVariable long id,
            @RequestParam(required = false) Double radiusKm,
            @RequestParam(required = false) Integer limit) {
        return service.nearby(id, radiusKm, limit);
    }
}
