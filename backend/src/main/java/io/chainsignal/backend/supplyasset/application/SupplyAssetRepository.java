package io.chainsignal.backend.supplyasset.application;

import java.util.List;
import java.util.Optional;

import io.chainsignal.backend.supplyasset.domain.SupplyAsset;

public interface SupplyAssetRepository {

    SupplyAsset create(CreateSupplyAssetCommand command);

    Optional<SupplyAsset> findById(long id);

    List<SupplyAsset> findAll();

    Optional<SupplyAsset> update(long id, UpdateSupplyAssetCommand command);

    Optional<SupplyAsset> deactivate(long id);
}
