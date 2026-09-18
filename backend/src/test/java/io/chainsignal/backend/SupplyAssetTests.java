package io.chainsignal.backend;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.Mockito.*;

import java.util.List;
import java.util.Optional;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.NullAndEmptySource;
import org.junit.jupiter.params.provider.ValueSource;

import io.chainsignal.backend.supplyasset.application.*;
import io.chainsignal.backend.supplyasset.domain.*;

class SupplyAssetTests {
    private CreateSupplyAssetCommand command() {
        return new CreateSupplyAssetCommand(SupplyAssetType.PORT, " Port ", "Türkiye", "İstanbul", 41, 29, 5);
    }

    @Test
    void commandsAndDomainPreserveTextAndAllowCoordinateBoundaries() {
        assertThat(command().name()).isEqualTo(" Port ");
        var update = new UpdateSupplyAssetCommand(SupplyAssetType.SUPPLIER, " Name ", " Country ", " City ", -90, 180, 1);
        var asset = new SupplyAsset(1, update.type(), update.name(), update.country(), update.city(), update.latitude(), update.longitude(), update.criticality(), false);
        assertThat(asset.name()).isEqualTo(" Name ");
        assertThat(asset.active()).isFalse();
        assertThat(new CreateSupplyAssetCommand(SupplyAssetType.PORT, "n", "c", "c", 90, -180, 5).latitude()).isEqualTo(90);
    }

    @Test
    void nullTypesConsistentlyUseInvalidArgument() {
        assertThatIllegalArgumentException().isThrownBy(() -> new CreateSupplyAssetCommand(null, "n", "c", "c", 0, 0, 1));
        assertThatIllegalArgumentException().isThrownBy(() -> new UpdateSupplyAssetCommand(null, "n", "c", "c", 0, 0, 1));
        assertThatIllegalArgumentException().isThrownBy(() -> new SupplyAsset(1, null, "n", "c", "c", 0, 0, 1, true));
    }

    @ParameterizedTest
    @NullAndEmptySource
    @ValueSource(strings = {" ", "\t"})
    void blankTextRejectedAcrossDomainAndCommands(String value) {
        assertThatIllegalArgumentException().isThrownBy(() -> new CreateSupplyAssetCommand(SupplyAssetType.PORT, value, "c", "c", 0, 0, 1));
        assertThatIllegalArgumentException().isThrownBy(() -> new UpdateSupplyAssetCommand(SupplyAssetType.PORT, "n", value, "c", 0, 0, 1));
        assertThatIllegalArgumentException().isThrownBy(() -> new SupplyAsset(1, SupplyAssetType.PORT, "n", "c", value, 0, 0, 1, true));
    }

    @ParameterizedTest
    @ValueSource(doubles = {-91, 91, Double.NaN, Double.POSITIVE_INFINITY})
    void invalidLatitudeRejected(double value) {
        assertThatIllegalArgumentException().isThrownBy(() -> new CreateSupplyAssetCommand(SupplyAssetType.PORT, "n", "c", "c", value, 0, 1));
        assertThatIllegalArgumentException().isThrownBy(() -> new UpdateSupplyAssetCommand(SupplyAssetType.PORT, "n", "c", "c", value, 0, 1));
        assertThatIllegalArgumentException().isThrownBy(() -> new SupplyAsset(1, SupplyAssetType.PORT, "n", "c", "c", value, 0, 1, true));
    }

    @ParameterizedTest
    @ValueSource(doubles = {-181, 181, Double.NaN, Double.NEGATIVE_INFINITY})
    void invalidLongitudeRejected(double value) {
        assertThatIllegalArgumentException().isThrownBy(() -> new CreateSupplyAssetCommand(SupplyAssetType.PORT, "n", "c", "c", 0, value, 1));
        assertThatIllegalArgumentException().isThrownBy(() -> new UpdateSupplyAssetCommand(SupplyAssetType.PORT, "n", "c", "c", 0, value, 1));
        assertThatIllegalArgumentException().isThrownBy(() -> new SupplyAsset(1, SupplyAssetType.PORT, "n", "c", "c", 0, value, 1, true));
    }

    @ParameterizedTest
    @ValueSource(ints = {0, 6})
    void invalidCriticalityRejected(int value) {
        assertThatIllegalArgumentException().isThrownBy(() -> new CreateSupplyAssetCommand(SupplyAssetType.PORT, "n", "c", "c", 0, 0, value));
        assertThatIllegalArgumentException().isThrownBy(() -> new UpdateSupplyAssetCommand(SupplyAssetType.PORT, "n", "c", "c", 0, 0, value));
        assertThatIllegalArgumentException().isThrownBy(() -> new SupplyAsset(1, SupplyAssetType.PORT, "n", "c", "c", 0, 0, value, true));
    }

    @ParameterizedTest
    @ValueSource(longs = {0, -1})
    void invalidIdsNeverReachRepository(long id) {
        var repository = mock(SupplyAssetRepository.class);
        var service = new SupplyAssetService(repository);
        assertThatIllegalArgumentException().isThrownBy(() -> service.getById(id));
        assertThatIllegalArgumentException().isThrownBy(() -> service.update(id, null));
        assertThatIllegalArgumentException().isThrownBy(() -> service.deactivate(id));
        assertThatIllegalArgumentException().isThrownBy(() -> new SupplyAsset(id, SupplyAssetType.PORT, "n", "c", "c", 0, 0, 1, true));
        verifyNoInteractions(repository);
    }

    @Test
    void serviceDelegatesLifecycleAndKeepsInactiveRetrievable() {
        var repository = mock(SupplyAssetRepository.class);
        var service = new SupplyAssetService(repository);
        var asset = new SupplyAsset(1, SupplyAssetType.PORT, "n", "c", "c", 0, 0, 1, false);
        var create = command();
        var update = new UpdateSupplyAssetCommand(create.type(), create.name(), create.country(), create.city(), create.latitude(), create.longitude(), create.criticality());
        when(repository.create(create)).thenReturn(asset);
        when(repository.findById(1)).thenReturn(Optional.of(asset));
        when(repository.findAll()).thenReturn(List.of(asset));
        when(repository.update(1, update)).thenReturn(Optional.of(asset));
        when(repository.deactivate(1)).thenReturn(Optional.of(asset));
        assertThat(service.create(create)).isSameAs(asset);
        assertThat(service.getById(1)).isSameAs(asset);
        assertThat(service.list()).containsExactly(asset);
        assertThat(service.update(1, update)).isSameAs(asset);
        assertThat(service.deactivate(1)).isSameAs(asset);
    }

    @Test
    void missingAssetIsNotFoundForEveryIdOperation() {
        var service = new SupplyAssetService(mock(SupplyAssetRepository.class));
        assertThatThrownBy(() -> service.getById(8)).isInstanceOf(SupplyAssetNotFoundException.class);
        assertThatThrownBy(() -> service.update(8, null)).isInstanceOf(SupplyAssetNotFoundException.class);
        assertThatThrownBy(() -> service.deactivate(8)).isInstanceOf(SupplyAssetNotFoundException.class);
    }
}
