package io.chainsignal.backend;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.Mockito.*;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import io.chainsignal.backend.event.application.*;
import io.chainsignal.backend.event.domain.*;
import io.chainsignal.backend.supplyasset.application.*;
import io.chainsignal.backend.supplyasset.domain.*;

import tools.jackson.databind.json.JsonMapper;

class EventServiceTests {
    private final EventRepository repository = mock(EventRepository.class);
    private final SupplyAssetService assets = mock(SupplyAssetService.class);
    private final EventQueryProperties properties = new EventQueryProperties(100, 500, 100, 1000);
    private final EventService service = new EventService(repository, assets, properties);

    @Test
    void getAndListDelegateTypedFiltersWithoutChangingCountry() {
        var event = new Event(1, "GDACS", "EQ:1", EventType.EARTHQUAKE, Instant.EPOCH, 0, 0, Severity.HIGH, null, JsonMapper.builder().build().readTree("{\"null\":null}"), "v1");
        when(repository.findById(1)).thenReturn(Optional.of(event));
        when(repository.findLatest(100, EventType.FLOOD, Severity.HIGH, " Türkiye ")).thenReturn(List.of(event));
        assertThat(service.getById(1)).isSameAs(event);
        assertThat(service.list(null, EventType.FLOOD, Severity.HIGH, " Türkiye ")).containsExactly(event);
        assertThat(event.country()).isNull();
        assertThat(event.metadata().isObject()).isTrue();
    }

    @Test
    void invalidAndMissingIdsAreDistinct() {
        assertThatIllegalArgumentException().isThrownBy(() -> service.getById(0));
        assertThatIllegalArgumentException().isThrownBy(() -> service.getById(-1));
        verifyNoInteractions(repository);
        assertThatThrownBy(() -> service.getById(1)).isInstanceOf(EventNotFoundException.class);
    }

    @ParameterizedTest
    @ValueSource(ints = {0, -1, 501})
    void invalidLimitsNeverReachQueries(int limit) {
        assertThatIllegalArgumentException().isThrownBy(() -> service.list(limit, null, null, null));
        assertThatIllegalArgumentException().isThrownBy(() -> service.nearby(1, 1.0, limit));
        verifyNoInteractions(repository, assets);
    }

    @ParameterizedTest
    @ValueSource(doubles = {0, -1, 1000.1, Double.NaN, Double.POSITIVE_INFINITY})
    void invalidRadiusNeverReachesQueries(double radius) {
        assertThatIllegalArgumentException().isThrownBy(() -> service.nearby(1, radius, null));
        verifyNoInteractions(repository, assets);
    }

    @Test
    void nearbyConvertsKmAndDefaultsAndAcceptsMaximum() {
        when(assets.getById(1)).thenReturn(new SupplyAsset(1, SupplyAssetType.PORT, "n", "c", "c", 0, 0, 1, true));
        service.nearby(1, null, null);
        verify(repository).findNearby(1, 100000, 100);
        service.nearby(1, 1000.0, 500);
        verify(repository).findNearby(1, 1000000, 500);
    }

    @Test
    void inactiveAndMissingAssetsAreNotFound() {
        when(assets.getById(1)).thenReturn(new SupplyAsset(1, SupplyAssetType.PORT, "n", "c", "c", 0, 0, 1, false));
        when(assets.getById(2)).thenThrow(new SupplyAssetNotFoundException(2));
        assertThatThrownBy(() -> service.nearby(1, null, null)).isInstanceOf(SupplyAssetNotFoundException.class).hasMessageContaining("Active");
        assertThatThrownBy(() -> service.nearby(2, null, null)).isInstanceOf(SupplyAssetNotFoundException.class);
        verifyNoInteractions(repository);
    }

    @Test
    void blankFilterRejectedAndConfigurationBoundsValidated() {
        assertThatIllegalArgumentException().isThrownBy(() -> service.list(null, null, null, " "));
        verifyNoInteractions(repository);
        assertThatIllegalArgumentException().isThrownBy(() -> new EventQueryProperties(0, 500, 100, 1000));
        assertThatIllegalArgumentException().isThrownBy(() -> new EventQueryProperties(100, 99, 100, 1000));
        assertThatIllegalArgumentException().isThrownBy(() -> new EventQueryProperties(100, 500, 0, 1000));
        assertThatIllegalArgumentException().isThrownBy(() -> new EventQueryProperties(100, 500, 100, 99));
        assertThatIllegalArgumentException().isThrownBy(() -> new EventQueryProperties(100, 500, 100, Double.NaN));
    }
}
