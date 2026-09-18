package io.chainsignal.backend.supplyasset.application;

import java.util.List;

import org.springframework.stereotype.Service;

import io.chainsignal.backend.supplyasset.domain.SupplyAsset;

@Service
public class SupplyAssetService {

    private final SupplyAssetRepository repository;

    public SupplyAssetService(SupplyAssetRepository repository) {
        this.repository = repository;
    }

    public SupplyAsset create(CreateSupplyAssetCommand command) {
        return repository.create(command);
    }

    public SupplyAsset getById(long id) {
        requirePositiveId(id);

        return repository.findById(id)
                .orElseThrow(() -> new SupplyAssetNotFoundException(id));
    }

    public List<SupplyAsset> list() {
        return repository.findAll();
    }

    public SupplyAsset update(long id, UpdateSupplyAssetCommand command) {
        requirePositiveId(id);

        return repository.update(id, command)
                .orElseThrow(() -> new SupplyAssetNotFoundException(id));
    }

    public SupplyAsset deactivate(long id) {
        requirePositiveId(id);

        return repository.deactivate(id)
                .orElseThrow(() -> new SupplyAssetNotFoundException(id));
    }

    private static void requirePositiveId(long id) {
        if (id <= 0) {
            throw new IllegalArgumentException(
                    "Supply asset id must be positive");
        }
    }
}
