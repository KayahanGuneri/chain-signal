package io.chainsignal.backend.event.application;

public final class EventNotFoundException extends RuntimeException {
    public EventNotFoundException(long id) {
        super("Event not found: " + id);
    }
}
